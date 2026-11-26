"""검역이력 행 처리 공개 함수: 업로드 → 판독 → 행 → 판단 → 대조 → 가격 → 신고건. 담당: KHS A1-1~A1-7

다른 영역(A2 등록 후 재계산, A4 시험 실행)은 이 파일의 함수만 부른다.
재실행 규칙(AGENTS 3장): 앞 단계가 바뀌면 뒤 단계를 다시 계산한다. final_value와 승인 행은 건드리지 않는다.
"""

import re
import uuid
from datetime import date
from pathlib import Path

from app.a0_reader.classify.service import classify_by_name
from app.a0_reader.extract.service import extract_documents
from app.a1_history.arrival.service import apply_cargo
from app.a1_history.crosscheck.ai_check import analyze as analyze_with_ai
from app.a1_history.crosscheck.service import (
    apply_flags,
    arrival_check,
    crosscheck_row,
    mark_resolved,
    merge_ai,
)
from app.a1_history.missing.service import DOC_LABELS, missing_docs
from app.a1_history.price.service import fill_prices
from app.a1_history.rows.build import build_rows, find_bl, merge_with_existing
from app.a1_history.rows.names import apply_name_style
from app.a3_judge.grouping.service import recompute
from app.a3_judge.pipeline.service import judge_rows
from app.a4_settings.engine.service import get_rules
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.masking import all_names
from app.core.schema.document import ParsedDocument
from app.core.schema.fields import Evidence, Field
from app.core.schema.history import (
    C_APPROVAL,
    C_MAKER,
    C_MATERIAL,
    C_NAME_KO,
    C_PRICE_USD,
    C_SPEC,
    COLOR_COLUMN,
    COLUMNS,
    HistoryRow,
)
from app.core.schema.shipper import ShipperSettings
from app.core.storage import drive, local_db, work_db, work_db_more
from app.core.unipass.client import get_cargo

W_MULTI_BL = "한 폴더에 B/L이 여러 개입니다 — 폴더를 나눠 올려 주세요(확인 필요)"
COMPUTED = {C_PRICE_USD, "USD 환율", "CI 통화 환율"}  # 계산 칸: 직접 입력 금지
REJUDGE_COLS = {C_MATERIAL, C_MAKER, C_SPEC, C_NAME_KO, COLOR_COLUMN}


def _latest_by_type(docs: list[ParsedDocument]) -> list[ParsedDocument]:
    """같은 B/L 재업로드: 서류 종류마다 가장 최근 것만(사진·라벨은 모두)."""
    latest: dict[str, ParsedDocument] = {}
    extra: list[ParsedDocument] = []
    for d in docs:
        if d.doc_type in ("PHOTO", "LABEL"):
            extra.append(d)
        else:
            latest[d.doc_type] = d
    return [*latest.values(), *extra]


def _safe(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", name)


def preview(filenames: list[str], shipper_id: str) -> dict:
    """올리기 전: 파일 이름으로 서류 종류 미리 보기, 화주 필요 서류(DESIGN 3-1-1)."""
    settings = get_rules(shipper_id)
    kinds = [{"filename": f, "doc_type": classify_by_name(f)} for f in filenames]
    present = {k["doc_type"] for k in kinds if k["doc_type"]}
    return {
        "files": kinds,
        "required": [
            {"doc_type": d, "label": DOC_LABELS.get(d, d), "present": d in present}
            for d in settings.required_docs
        ],
        "missing": missing_docs(present, list(settings.required_docs)),
    }


def _bl_label(rows: list[HistoryRow], bl: str) -> str:
    models = [r.model for r in rows if r.model and not r.is_part]
    return f"{bl} {models[0]} 외" if models else bl


def process_upload(shipper_id: str, files: list[tuple[str, bytes]]) -> dict:
    """폴더 1개 = 선적서류 1건(RULES 11-1). 응답: 만든·고친 row_id, 서류별 판독 결과."""
    if not files:
        raise AppError("invalid_input", "파일을 골라 주세요.")
    settings = get_rules(shipper_id)
    folder_id = uuid.uuid4().hex[:12]
    base = get_settings().data_path
    folder = base / "uploads" / shipper_id / folder_id
    folder.mkdir(parents=True, exist_ok=True)
    mask = (
        all_names()
    )  # PC 전용 목록(DATA_DIR/mask_names.json)만. rules/*.json의 mask_names는 읽지 않는다

    docs: list[ParsedDocument] = []
    paths: dict[str, Path] = {}
    for filename, data in files:
        path = folder / _safe(filename)
        path.write_bytes(data)
        # 엑셀 한 파일에 CI·PL 시트가 같이 있으면 서류 여러 개(HS 11/26)
        for doc in extract_documents(path, filename, shipper_id, folder_id, mask):
            work_db.save_document(doc, filename, path.relative_to(base).as_posix())
            docs.append(doc)
            paths[doc.doc_id] = path

    warnings: list[str] = []
    bls = {d.bl_no for d in docs if d.bl_no}
    if len(bls) > 1:
        warnings.append(W_MULTI_BL)
    bl_no = find_bl(docs)
    if bl_no:
        work_db_more.set_folder_bl(folder_id, bl_no)
        docs = [d.model_copy(update={"bl_no": d.bl_no or bl_no}) for d in docs]
    else:
        warnings.append("B/L 번호를 찾지 못함 — [확인 필요]")

    all_docs = _latest_by_type(work_db_more.documents_for_bl(shipper_id, bl_no)) if bl_no else docs
    existing = work_db.rows_by_bl(shipper_id, bl_no) if bl_no else []
    created, updated = rebuild_bl(shipper_id, bl_no, all_docs, existing)

    drive_result = drive.status()
    if drive_result["ok"]:
        rows = work_db.get_rows(created + updated)
        label = _bl_label(rows, bl_no) if bl_no else f"[확인 필요] {folder_id}"
        for d in docs:
            drive.upload(
                paths[d.doc_id], d.doc_id + "_" + paths[d.doc_id].name, [shipper_id, label]
            )
    local_db.audit("upload", shipper_id, f"bl={bl_no} files={len(files)}")
    return {
        "folder_id": folder_id,
        "bl_no": bl_no,
        "documents": [
            {
                "doc_id": d.doc_id,
                "doc_type": d.doc_type,
                "parser": d.parser,
                "warnings": d.warnings,
                "filename": paths[d.doc_id].name,
            }
            for d in docs
        ],
        "created": created,
        "updated": updated,
        "reupload": bool(existing),
        "missing_docs": missing_docs({d.doc_type for d in all_docs}, list(settings.required_docs)),
        "warnings": warnings,
        "drive": drive_result,
    }


def rebuild_bl(
    shipper_id: str, bl_no: str, docs: list[ParsedDocument], existing: list[HistoryRow]
) -> tuple[list[str], list[str]]:
    settings = get_rules(shipper_id)
    cargo = get_cargo(bl_no) if bl_no else None
    new_rows = build_rows(shipper_id, docs, settings, cargo)
    rows, created, updated = merge_with_existing(new_rows, existing)
    for r in rows:
        if r.row_id in updated:
            old = next((o for o in existing if o.row_id == r.row_id), None)
            if old and _values(old) != _values(r):
                r.confirmed = False  # 서류 값이 바뀌면 확인함을 다시 받는다
        apply_cargo(r, cargo)
    history = work_db.list_rows(shipper_id)
    ids = {r.row_id for r in rows}
    merged_history = [h for h in history if h.row_id not in ids] + rows
    rows = judge_rows(shipper_id, rows, merged_history)
    apply_name_style(rows, settings)
    _finish(rows, docs, cargo.arrival_packages if cargo else "")
    work_db.save_rows(rows)
    recompute(shipper_id)
    return created, updated


def simulate(
    shipper_id: str, docs: list[ParsedDocument], settings: ShipperSettings
) -> list[HistoryRow]:
    """저장하지 않고 서류 → 행 → 판단(A4 시험 실행). 같은 B/L의 기존 행은 이력에서 뺀다."""
    bl_no = find_bl(docs)
    cargo = get_cargo(bl_no) if bl_no else None
    rows = build_rows(shipper_id, docs, settings, cargo)
    for r in rows:
        apply_cargo(r, cargo)
    history = [h for h in work_db.list_rows(shipper_id) if h.text("B/L Number") != bl_no]
    rows = judge_rows(shipper_id, rows, history + rows, settings=settings, extra_docs=docs)
    apply_name_style(rows, settings)
    fill_prices(rows)
    for r in rows:
        apply_flags(r, crosscheck_row(r, docs, rows))
        r.refresh_status()
    return rows


def _values(row: HistoryRow) -> dict:
    return {k: c.ai_value for k, c in row.cells.items()}


def _finish(rows: list[HistoryRow], docs: list[ParsedDocument], arrival_packages: str) -> None:
    """대조 → 가격 → 상태. 저장은 하지 않는다."""
    bl_doc = next((d for d in reversed(docs) if d.doc_type == "BL"), None)
    fill_prices(rows)
    # 코드 대조 → OpenAI 분석(선적 건 1번) → 둘 중 하나라도 다르면 불일치 → 불일치 칸 막기 (검역 리스트 탭 2단계)
    rows_items = [(r, crosscheck_row(r, docs, rows)) for r in rows]
    mask = all_names()
    ai = analyze_with_ai(rows_items, docs, mask)
    for r, items in rows_items:
        merge_ai(items, (ai or {}).get(r.row_id))
        apply_flags(r, items)
        mark_resolved(r, items, work_db_more.get_mismatches(r.row_id))
        arrival_check(r, bl_doc, arrival_packages)
        work_db_more.save_mismatches(r.row_id, items)
        r.refresh_status()


def rebuild_all(shipper_id: str) -> dict:
    """설정 변경 뒤: B/L마다 서류에서 행을 다시 만든다(확정 값 유지). 서류에 더는 없는 행은
    사람이 고친 값이 없으면 지우고, 있으면 남겨서 비고에 '확인 필요'를 단다."""
    rows = work_db.list_rows(shipper_id)
    bls = sorted({r.text("B/L Number") for r in rows if r.text("B/L Number")})
    removed, kept = 0, 0
    for bl in bls:
        existing = [r for r in rows if r.text("B/L Number") == bl]
        docs = _latest_by_type(work_db_more.documents_for_bl(shipper_id, bl))
        if not docs:
            continue
        created, updated = rebuild_bl(shipper_id, bl, docs, existing)
        live = set(created) | set(updated)
        for old in existing:
            if old.row_id in live or old.locked:
                continue
            if any(c.final_value is not None for c in old.cells.values()):
                old.set_note("설정 변경", "바뀐 설정으로는 서류에 없는 행입니다 — 확인 필요")
                old.cells["비고"].flag = "need_check"
                old.refresh_status()
                work_db.save_rows([old])
                kept += 1
            else:
                work_db_more.delete_rows([old.row_id])
                removed += 1
    recompute(shipper_id)
    return {"bls": len(bls), "removed": removed, "kept": kept}


def rejudge(shipper_id: str, row_ids: list[str] | None = None) -> int:
    """판단만 다시(A2 등록·설정 변경·칸 수정 뒤). 승인 행 제외."""
    history = work_db.list_rows(shipper_id)
    targets = [r for r in history if not r.locked and (row_ids is None or r.row_id in row_ids)]
    if not targets:
        recompute(shipper_id)
        return 0
    judged = judge_rows(shipper_id, targets, history)
    apply_name_style(judged, get_rules(shipper_id))
    for r in judged:
        r.refresh_status()
    work_db.save_rows(judged)
    recompute(shipper_id)
    return len(judged)


def scan_inbox(shipper_id: str) -> dict:
    """드라이브 접수 폴더 자동 처리(화주 설정 inbox). {화주}/새 서류/의 B/L 폴더마다 서류 올리기와 같게 처리하고
    {화주}/가져옴/으로 옮긴다. 꺼져 있으면 하지 않고, 드라이브가 연결 안 됐으면 '드라이브 미연결'로 알린다."""
    if not getattr(get_rules(shipper_id), "inbox", False):
        return {
            "ok": False,
            "enabled": False,
            "reason": "기업 설정에서 '드라이브 접수 폴더 자동 처리'가 꺼져 있습니다.",
            "imported": [],
        }
    folders, why = drive.inbox_folders(shipper_id)
    if why:
        return {"ok": False, "enabled": True, "reason": why, "imported": []}
    imported = []
    for name, files in folders:
        out = process_upload(shipper_id, files)
        drive.move_folder([shipper_id, drive.INBOX_NEW, name], [shipper_id, drive.INBOX_DONE])
        imported.append(
            {
                "folder": name,
                "bl_no": out["bl_no"],
                "rows": len(out["created"]) + len(out["updated"]),
            }
        )
    local_db.audit("inbox_scan", shipper_id, f"folders={len(imported)}")
    return {"ok": True, "enabled": True, "reason": "", "imported": imported}


def refresh(shipper_id: str) -> dict:
    """새로고침: 유니패스(캐시 없이)·대조·가격·판단·신고건을 다시. 확정 값 유지(DESIGN 3-3)."""
    rows = work_db.list_rows(shipper_id)
    bls = sorted({r.text("B/L Number") for r in rows if r.text("B/L Number")})
    n = 0
    for bl in bls:
        group = [r for r in rows if r.text("B/L Number") == bl and not r.locked]
        if not group:
            continue
        cargo = get_cargo(bl, use_cache=False)
        for r in group:
            apply_cargo(r, cargo)
        docs = _latest_by_type(work_db_more.documents_for_bl(shipper_id, bl))
        _finish(group, docs, cargo.arrival_packages if cargo else "")
        work_db.save_rows(group)
        n += len(group)
    judged = rejudge(shipper_id)
    # 접수 폴더 자동 처리가 켜진 화주는 새로고침 때 드라이브 접수 폴더도 본다(로직 점검 반영 11/25)
    inbox = scan_inbox(shipper_id) if getattr(get_rules(shipper_id), "inbox", False) else None
    return {"rows": n, "judged": judged, "bls": len(bls), "inbox": inbox}


def patch_cell(
    row_id: str, column: str, value: object | None, memo: str | None, clear: bool = False
) -> HistoryRow:
    """담당자 수정 → final_value. 재질·제조사 등을 고치면 실적·신고건을 다시 계산(DESIGN 3-4)."""
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    if row.locked:
        raise AppError("locked", "승인 완료된 행은 고칠 수 없습니다.", 409)
    if column not in COLUMNS and column != COLOR_COLUMN:
        raise AppError("invalid_input", f"모르는 열: {column}")
    if column in COMPUTED and (value is not None or clear):
        raise AppError("computed", "가격(USD)은 계산 칸입니다. 가격(수출국)·환율을 고치세요.", 400)
    cell = row.cells.setdefault(column, Field())
    if clear:
        cell.final_value = None
        cell.flag = "ok"
    elif value is not None:
        text = value.strip() if isinstance(value, str) else value
        cell.final_value = text if text != "" else None
        same = str(cell.ai_value) == str(cell.final_value)
        # 사람이 입력한 값(프로그램 값과 다르거나 빈 칸을 채움)은 주황 '사람이 고름·입력' + 근거 MANUAL
        cell.flag = "ok" if same or cell.final_value is None else "edited"
        if cell.final_value is not None and not same:
            cell.evidence = [e for e in cell.evidence if e.source != "MANUAL"] + [
                Evidence(
                    source="MANUAL",
                    ref="edit",
                    note="MANUAL: 직접 입력" + (f" — {memo}" if memo else ""),
                )
            ]
    if memo is not None:
        if memo == "" and cell.flag in ("need_check", "mismatch"):
            cell.flag = "ok"  # 메모를 지우면 확인함(RULES 11-9)
        cell.memo = memo
    if column == C_APPROVAL and cell.value:
        row.status = "승인"
    row.refresh_status()
    work_db.save_rows([row])
    local_db.audit("edit", row_id, column)
    if column in REJUDGE_COLS or column == C_APPROVAL:
        rejudge(row.shipper_id, [row_id] if column != C_MATERIAL else None)
    else:
        recompute(row.shipper_id)
    got = work_db.get_row(row_id)
    assert got is not None
    return got


def confirm(row_id: str, on: bool) -> HistoryRow:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    row.confirmed = on
    row.refresh_status()
    work_db.save_rows([row])
    recompute(row.shipper_id)
    local_db.audit("confirm" if on else "unconfirm", row_id)
    got = work_db.get_row(row_id)
    assert got is not None
    return got


def review(row_id: str) -> dict:
    """검수 패널(DESIGN 4장): 서류별 값, 불일치·사람 수정 수, 원본 서류 목록."""
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    items = work_db_more.get_mismatches(row_id)
    docs = work_db.documents_by_ids(row.source_doc_ids)
    edited = [
        {"column": col, "sheet": c.final_value, "program": c.ai_value, "memo": c.memo}
        for col, c in row.cells.items()
        if c.flag == "edited"
    ]
    warnings = [
        {"column": col, "flag": c.flag, "memo": c.memo, "value": c.value}
        for col, c in row.cells.items()
        if c.flag in ("need_check", "need_input", "mismatch")
    ]
    files = []
    for d in docs:
        got = work_db.get_document(d.doc_id)
        files.append(
            {
                "doc_id": d.doc_id,
                "doc_type": d.doc_type,
                "filename": got[1] if got else d.doc_id,
                "warnings": d.warnings,
            }
        )
    return {
        "row": row.model_dump(),
        "items": items,
        "mismatch_count": sum(1 for it in items if it.get("different")),
        "edited_count": len(edited),
        "edited": edited,
        "warnings": warnings,
        "documents": files,
        "confirmed": row.confirmed,
    }


def badges(shipper_id: str) -> dict:
    rows = work_db.list_rows(shipper_id)
    decls = work_db_more.list_declarations(shipper_id)
    return {
        "need_check": sum(1 for r in rows if r.needs_attention()),
        "in_progress": len(decls),
        "ready": sum(1 for r in rows if r.status == "신청 전"),
        "mismatch": sum(
            1
            for r in rows
            if not r.confirmed and any(c.flag == "mismatch" for c in r.cells.values())
        ),
        "edited": sum(1 for r in rows if any(c.flag == "edited" for c in r.cells.values())),
        "approved": sum(1 for r in rows if r.locked),
        "total": len(rows),
        # 검역 리스트 탭 헤더 배지 (0단계, HS 요청 11/26)
        "need_input": sum(1 for r in rows if not r.locked and "need_input" in r.attention_flags()),
        "review_waiting": sum(1 for r in rows if r.needs_attention()),
        "manual": sum(1 for r in rows if any(c.final_value is not None for c in r.cells.values())),
    }


def list_history(
    shipper_id: str, status: str | None = None, attention: bool = False
) -> list[HistoryRow]:
    rows = work_db.list_rows(shipper_id)
    if status:
        rows = [r for r in rows if r.status == status]
    if attention:
        rows = [r for r in rows if r.needs_attention()]
    return rows


def delete_row(row_id: str) -> None:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    if row.locked:
        raise AppError("locked", "승인 완료된 행은 지울 수 없습니다.", 409)
    work_db_more.delete_rows([row_id])
    recompute(row.shipper_id)
    local_db.audit("delete_row", row_id)


def move_row(row_id: str, before_row_id: str | None) -> None:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    work_db_more.move_row(row_id, before_row_id)
    recompute(row.shipper_id)


def archive_ready(shipper_id: str) -> dict:
    """처리완료 이동(A1-5): '자료 추가 필요' 칸이 하나도 없는 B/L. 드라이브 연동이 꺼져 있으면 목록만."""
    rows = work_db.list_rows(shipper_id)
    by_bl: dict[str, list[HistoryRow]] = {}
    for r in rows:
        if r.text("B/L Number"):
            by_bl.setdefault(r.text("B/L Number"), []).append(r)
    ready = [
        bl
        for bl, rs in by_bl.items()
        if not any(c.flag == "need_input" for r in rs for c in r.cells.values())
    ]
    st = drive.status()
    moved = []
    if st["ok"]:
        for bl in ready:
            label = _bl_label(by_bl[bl], bl)
            res = drive.move_folder([shipper_id, label], ["처리완료", shipper_id])
            if res.get("ok"):
                moved.append(bl)
    return {"ready": ready, "moved": moved, "drive": st, "today": date.today().isoformat()}
