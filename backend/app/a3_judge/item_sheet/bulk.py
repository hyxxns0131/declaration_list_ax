"""품목사항 엑셀 한꺼번에 내려받기(전체 / 같은 품목끼리). AI 없음. 담당: LSY [신규] (HS 요청 11/26)

- 유니패스는 신고건 1개 = 품목사항 파일 1개라서, ZIP 안에 신고건마다 xlsx 1개를 넣는다.
  파일 이름: <화주>_신고건NN_<모선>_<제조업소>.xlsx. 검토용 합본 xlsx(신고건마다 시트 1개)도 같이 넣는다.
- '같은 품목끼리'는 어느 신고건을 내려받을지 고르는 것일 뿐, 서로 다른 신고건을 한 파일로 합치지 않는다
  (한 품목사항 = 한 신고건, check_one_declaration 그대로).
- 검사에 걸린 신고건(한 신고건이 아님, 실적 자료 없음, 행 없음)은 빼고 ZIP 안 '제외됨.txt'와 응답에 이유를 남긴다.
- 파일은 DATA_DIR/item_sheets/<file_id>.zip, 기록은 item_files 표(단건과 같은 표).
"""

import re
import uuid
import zipfile
from collections.abc import Callable
from datetime import date
from io import BytesIO

from openpyxl import Workbook

from app.a3_judge.history_lookup.model_key import product_base
from app.a3_judge.item_sheet.build import HEADERS, build_item_sheet
from app.a3_judge.item_sheet.validate import check_one_declaration
from app.a3_judge.item_sheet.writer import write_xlsx
from app.a4_settings.engine.service import get_rules
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schema.declaration import Declaration
from app.core.schema.history import C_BL, C_NAME_KO, C_RECORD, HistoryRow
from app.core.storage import local_db, work_db, work_db_more

GROUP_BASES: dict[str, str] = {
    "material": "재질",
    "factory": "제조업소",
    "product": "품목(한글 제품명·모델군)",
    "record": "실적번호",
}
NONE_LABEL = "(정해지지 않음)"


def _safe(text: str, limit: int = 30) -> str:
    s = re.sub(r'[\\/:*?"<>|\s]+', "_", text.strip()).strip("_")
    return (s or "미상")[:limit]


def _model_group(model: str) -> str:
    """모델군: 'RC-100' → 'RC', 'POT-14' → 'POT' (숫자 앞 글자)."""
    m = re.match(r"[A-Za-z]+", model or "")
    return m.group(0).upper() if m else ""


def _product_label(rows: list[HistoryRow]) -> str:
    name = product_base(rows[0].text(C_NAME_KO)) if rows else ""
    if name and "자료추가필요" not in name:
        return name
    return _model_group(rows[0].model) if rows else ""


GROUP_FN: dict[str, Callable[[Declaration, list[HistoryRow]], str]] = {
    "material": lambda d, rows: d.key.material,
    "factory": lambda d, rows: d.key.factory_code,
    "product": lambda d, rows: _product_label(rows),
    "record": lambda d, rows: ", ".join(d.record_nos),
}


def _declarations(shipper_id: str) -> list[tuple[int, Declaration, list[HistoryRow]]]:
    """(화면 번호 1부터, 신고건, 표 순서 행)."""
    decls = work_db_more.list_declarations(shipper_id)
    order = {r.row_id: i for i, r in enumerate(work_db.list_rows(shipper_id))}
    out = []
    for no, d in enumerate(decls, start=1):
        rows = work_db.get_rows(d.row_ids) if d.row_ids else []
        rows.sort(key=lambda r: order.get(r.row_id, 0))
        out.append((no, d, rows))
    return out


def groups(shipper_id: str, group_by: str) -> list[dict]:
    """같은 품목끼리 고르기용 묶음 [{key, label, count, declaration_ids, numbers}]."""
    fn = GROUP_FN.get(group_by)
    if not fn:
        raise AppError("invalid_input", f"묶음 기준은 {', '.join(GROUP_BASES)} 중 하나입니다.")
    out: dict[str, dict] = {}
    for no, d, rows in _declarations(shipper_id):
        key = fn(d, rows) or NONE_LABEL
        g = out.setdefault(
            key, {"key": key, "label": key, "count": 0, "declaration_ids": [], "numbers": []}
        )
        g["count"] += 1
        g["declaration_ids"].append(d.declaration_id)
        g["numbers"].append(no)
    return list(out.values())


def _problems(rows: list[HistoryRow], settings: object) -> list[str]:
    if not rows:
        return ["행이 없습니다"]
    reasons = check_one_declaration(rows, settings)  # type: ignore[arg-type]
    missing = [f"{r.text(C_BL)} {r.model}".strip() for r in rows if not r.text(C_RECORD)]
    if missing:
        reasons.append(
            f"실적 자료 없음 {len(missing)}행 ({', '.join(missing[:3])}{' 외' if len(missing) > 3 else ''})"
        )
    return reasons


def _combined(sheets: list[tuple[str, list[list[str]]]]) -> bytes:
    """검토용 합본: 신고건마다 시트 1개(시트끼리 섞지 않는다)."""
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in sheets:
        ws = wb.create_sheet(title[:31])
        ws.append([h for h, _ in HEADERS])
        for values in rows:
            ws.append(values)
    if not wb.sheetnames:
        wb.create_sheet("없음").append(["내려받을 신고건이 없습니다"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export(
    shipper_id: str,
    declaration_ids: list[str] | None = None,
    group_by: str | None = None,
    group_keys: list[str] | None = None,
) -> dict:
    """ZIP 만들기. declaration_ids가 있으면 그 신고건만, group_by+group_keys면 그 묶음의 신고건만, 둘 다 없으면 전체."""
    all_decls = _declarations(shipper_id)
    if not all_decls:
        raise AppError("not_found", "신고건이 없습니다. 검역 리스트에서 서류를 먼저 올리세요.", 404)
    wanted: set[str] | None = None
    if declaration_ids:
        wanted = set(declaration_ids)
    elif group_by:
        keys = set(group_keys or [])
        if not keys:
            raise AppError("invalid_input", "내려받을 묶음을 골라 주세요.")
        wanted = {
            i
            for g in groups(shipper_id, group_by)
            if g["key"] in keys
            for i in g["declaration_ids"]
        }
    chosen = [x for x in all_decls if wanted is None or x[1].declaration_id in wanted]
    if not chosen:
        raise AppError("not_found", "고른 신고건이 없습니다.", 404)

    settings = get_rules(shipper_id)
    included: list[dict] = []
    excluded: list[dict] = []
    sheets: list[tuple[str, list[list[str]]]] = []
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for no, d, rows in chosen:
            reasons = _problems(rows, settings)
            if reasons:
                excluded.append(
                    {"declaration_id": d.declaration_id, "number": no, "reasons": reasons}
                )
                continue
            sheet = build_item_sheet(rows)
            vessel = d.key.vessel_key.replace("모선명:", "")
            name = f"{_safe(shipper_id, 20)}_신고건{no:02d}_{_safe(vessel)}_{_safe(d.key.factory_code)}.xlsx"
            zf.writestr(name, write_xlsx(sheet))
            sheets.append((f"신고건{no:02d}", sheet.rows))
            included.append(
                {
                    "declaration_id": d.declaration_id,
                    "number": no,
                    "filename": name,
                    "rows": len(rows),
                    "warnings": sheet.warnings,
                }
            )
        zf.writestr(f"검토용_합본_{_safe(shipper_id, 20)}.xlsx", _combined(sheets))
        lines = [
            f"신고건 {x['number']} ({x['declaration_id']}): {' / '.join(x['reasons'])}"
            for x in excluded
        ]
        zf.writestr("제외됨.txt", "\n".join(lines) if lines else "제외된 신고건 없음")

    file_id = uuid.uuid4().hex[:12]
    base = get_settings().data_path
    folder = base / "item_sheets"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{file_id}.zip"
    path.write_bytes(buf.getvalue())
    label = (
        "전체"
        if wanted is None
        else (GROUP_BASES.get(group_by or "", "선택") if group_by else "선택")
    )
    filename = f"품목사항_{_safe(shipper_id, 20)}_{label}_{date.today():%Y%m%d}.zip"
    row_ids = [i for _, d, _ in chosen for i in d.row_ids]
    work_db_more.save_item_file(
        file_id, shipper_id, filename, path.relative_to(base).as_posix(), row_ids
    )
    local_db.audit(
        "item_sheet_bulk", shipper_id, f"included={len(included)} excluded={len(excluded)}"
    )
    return {"file_id": file_id, "filename": filename, "included": included, "excluded": excluded}
