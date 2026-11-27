"""서류 대조 다시 하기·불일치 목록·검수 패널에서 고른 값 저장. 담당: KHS [신규] (검역 리스트 탭 2·3단계, HS 요청 11/26)

- crosscheck_all: 화주의 선적 건마다 코드 대조 + OpenAI 분석 다시(유니패스는 부르지 않음). final_value 유지.
- list_mismatches: 대조 결과(mismatches 표)를 행 정보와 함께. status = 일치 / 불일치 / 해결됨.
- resolve: 담당자가 고른 서류 값 또는 직접 입력 → final_value + 근거 MANUAL. AI 추천 값은 자동으로 넣지 않는다.
"""

from typing import Any, Literal

from pydantic import BaseModel

from app.a1_history.crosscheck.service import (
    DOC_COLS,
    STATUS_BAD,
    STATUS_DONE,
    STATUS_EMPTY,
    STATUS_OK,
    STATUS_REF,
)
from app.a1_history.rows import service as rows_service
from app.core.errors import AppError
from app.core.schema.fields import Evidence, Field
from app.core.schema.history import C_BL, C_MODEL, C_NAME_KO, HistoryRow
from app.core.storage import local_db, work_db, work_db_more

NUMERIC_HINT = ("수", "중량", "금액", "가격", "입수")


class Choice(BaseModel):
    item: str  # 대조 항목 이름(예: "카톤 수")
    source: Literal["CI", "PL", "BL", "UNIPASS", "manual"]
    value: Any = None  # manual일 때 직접 입력 값. 서류 값을 고르면 비워도 된다
    memo: str = ""


def crosscheck_all(shipper_id: str) -> dict:
    rows = work_db.list_rows(shipper_id)
    bls = sorted({r.shipment_key for r in rows if r.shipment_key})
    n = 0
    for bl in bls:
        group = [r for r in rows if r.shipment_key == bl and not r.locked]
        if not group:
            continue
        docs = rows_service._latest_by_type(work_db_more.documents_for_bl(shipper_id, bl))
        rows_service._finish(group, docs, "")
        work_db.save_rows(group)
        n += len(group)
    local_db.audit("crosscheck", shipper_id, f"rows={n}")
    open_items = sum(1 for m in list_mismatches(shipper_id) if m["status"] == STATUS_BAD)
    return {"rows": n, "bls": len(bls), "unresolved": open_items}


def list_mismatches(shipper_id: str, status: str | None = None) -> list[dict]:
    """[{row_id, bl_no, model, item, cell, CI, PL, BL, code_different, ai, status, chosen}] — 일치 항목은 status='일치'로만 줄 때."""
    out: list[dict] = []
    for r in work_db.list_rows(shipper_id):
        for it in work_db_more.get_mismatches(r.row_id):
            st = it.get("status") or (STATUS_BAD if it.get("different") else STATUS_OK)
            if status is None and st in (
                STATUS_OK,
                STATUS_EMPTY,
                STATUS_REF,
            ):  # 비어 있음·참고는 알림만(검수할 것 아님)
                continue
            if status and st != status:
                continue
            out.append(
                {
                    "row_id": r.row_id,
                    "bl_no": r.shipment_key,
                    "model": r.model,
                    "is_part": r.is_part,
                    **it,
                    "status": st,
                }
            )
    return out


def _as_value(item_name: str, v: object) -> object:
    if isinstance(v, str):
        v = v.strip()
        if any(h in item_name for h in NUMERIC_HINT):
            try:
                return float(v.replace(",", ""))
            except ValueError:
                return v
    return v


SHIPMENT_ITEMS = ("통화", "모선", "B/L 번호", "인보이스 번호", "서류 날짜")


def is_shipment_item(it: dict) -> bool:
    """선적 건 전체에 하나인 값(서류 머리 값). 시트 칸이 없는 항목 + 통화·모선·B/L 번호."""
    return not it.get("cell") or it.get("item") in SHIPMENT_ITEMS


def _spread_shipment_items(row: HistoryRow, chosen: list[dict]) -> None:
    """선적 건 단위 항목(시트 칸 없음)을 고르면 같은 B/L의 다른 행에도 같은 선택을 넣는다(HS 11/27)."""
    from app.a1_history.crosscheck.service import apply_flags

    if not chosen or not row.shipment_key:
        return
    picked = {it["item"]: it for it in chosen}
    for sib in work_db.list_rows(row.shipper_id):
        if sib.row_id == row.row_id or sib.shipment_key != row.shipment_key or sib.locked:
            continue
        items = work_db_more.get_mismatches(sib.row_id)
        hit = False
        for it in items:
            p = picked.get(it["item"])
            if p and is_shipment_item(it):
                it["status"], it["chosen"] = STATUS_DONE, p.get("chosen")
                hit = True
                col = it.get("cell") or ""
                src = row.cells.get(col) if col else None
                if col and src is not None:  # 칸 있는 항목은 고른 값까지 같이
                    sib.cells[col] = src.model_copy(deep=True)
        if hit:
            work_db_more.save_mismatches(sib.row_id, items)
            apply_flags(sib, items)
            sib.refresh_status()
            work_db.save_rows([sib])


def resolve(row_id: str, choices: list[Choice]) -> HistoryRow:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    if row.locked:
        raise AppError("locked", "승인 완료된 행은 고칠 수 없습니다.", 409)
    row.shipment_bl = row.shipment_key
    items = work_db_more.get_mismatches(row_id)
    by_name = {it["item"]: it for it in items}
    for ch in choices:
        it = by_name.get(ch.item)
        if not it:
            raise AppError("not_found", f"대조 항목이 없습니다: {ch.item}", 404)
        if ch.source == "manual":
            value = _as_value(ch.item, ch.value)
            note = "MANUAL: 직접 입력"
        else:
            value = it.get(ch.source)
            note = f"MANUAL: {ch.source} 값 선택"
        if value in (None, ""):
            raise AppError("invalid_input", f"{ch.item}: 고른 값이 비었습니다.")
        if ch.memo:
            note += f" — {ch.memo}"
        col = it.get("cell") or ""
        if col == C_MODEL:
            row.model = str(value)
        if col:
            cell = row.cells.setdefault(col, Field())
            cell.final_value = value
            cell.flag = "edited"  # 화면: 주황 '사람이 고름'
            cell.memo = ch.memo
            cell.evidence = [e for e in cell.evidence if e.source != "MANUAL"] + [
                Evidence(source="MANUAL", ref=ch.source, note=note)
            ]
        it["status"] = STATUS_DONE
        it["chosen"] = {"source": ch.source, "value": value, "memo": ch.memo, "note": note}
    row.refresh_status()
    work_db.save_rows([row])
    work_db_more.save_mismatches(row_id, items)
    _spread_shipment_items(
        row, [by_name[c.item] for c in choices if is_shipment_item(by_name[c.item])]
    )
    local_db.audit("resolve", row_id, ",".join(c.item for c in choices))
    rows_service.rejudge(
        row.shipper_id, [row_id]
    )  # 고른 값으로 아래 단계(판단·신고건) 다시, final_value 유지
    got = work_db.get_row(row_id)
    assert got is not None
    return got


__all__ = ["DOC_COLS", "Choice", "crosscheck_all", "list_mismatches", "resolve"]


# ── 화면 ② 왼쪽 목록 (HS 요청 11/27: '해결됨' 필터가 비는 문제, 숫자와 목록을 같은 함수로) ──────────
FRIENDLY_ITEM = {
    "CI 금액 TOTAL (시트 칸 = 줄 합)": "인보이스 합계 ↔ 품목 금액 합",
}


def friendly_item(it: dict) -> str:
    """항목 이름을 초보자가 알아듣는 말로. CI 합계는 값까지 붙인다."""
    name = it.get("item", "")
    if name in FRIENDLY_ITEM:
        total, lines = it.get("CI"), it.get("sheet")
        if total is not None and lines is not None:
            return f"인보이스 합계 {_num(total)} / 품목 금액 합 {_num(lines)}"
        return FRIENDLY_ITEM[name]
    return name


def _num(v: object) -> str:
    """1,234,567.5 처럼 쉼표 표기(지수 표기 쓰지 않음)."""
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(v)
    return f"{f:,.2f}".rstrip("0").rstrip(".")


def _row_label(r: HistoryRow) -> str:
    """행 이름: 모델 → (모델이 서류마다 다르면) 서류별 모델 → 한글 제품명 → '모델을 읽지 못함'."""
    if r.model:
        # '모델 · 한글 제품명' (부분품이면 합친 부품 수까지) — 초보자가 무슨 품목인지 알아보게(HS 11/27)
        import re as _re

        name = _re.sub(r"\([^)]*\)\s*$", "", r.text(C_NAME_KO)).strip()
        if "자료 추가 필요" in name:
            name = ""
        label = r.model + (" 부분품" if r.is_part and not name else "")
        if name:
            label += f" · {name}"
        if r.part_lines:
            label += f" (부품 {len(r.part_lines)}종)"
        return label
    if r.source_models:
        return "모델이 서류마다 다름: " + " / ".join(f"{k} {v}" for k, v in r.source_models.items())
    name = r.text(C_NAME_KO) if hasattr(r, "text") else ""
    if "자료 추가 필요" in name:  # 품목 칸에 '서류 필요' 표시만 있는 행
        return "품목을 읽지 못함 — 인보이스·패킹리스트 확인"
    return name or "모델을 읽지 못함"


def _reasons(r: HistoryRow) -> list[str]:
    """대조 항목 밖에서 사람이 볼 것(입력 필요·확인 필요 칸). 칸 이름은 짧게."""
    need_in = [
        c.split(" (")[0]
        for c, f in r.cells.items()
        if f.flag == "need_input" and f.final_value is None
    ]
    need_chk = [
        c.split(" (")[0]
        for c, f in r.cells.items()
        if f.flag == "need_check" and f.final_value is None
    ]
    out = []
    if need_in:
        out.append("입력 필요: " + ", ".join(need_in[:4]) + (" 외" if len(need_in) > 4 else ""))
    if need_chk:
        out.append("확인 필요: " + ", ".join(need_chk[:4]) + (" 외" if len(need_chk) > 4 else ""))
    return out


def _short(col: str) -> str:
    return col.split(" (")[0].split("(")[0].strip()


def _todo(r: HistoryRow, n_open: int, n_done: int) -> str:
    """카드에 쓰는 할 일 한 줄(HS 11/27 '칸 이름 칩은 읽기 어렵다'). 자세한 칸은 오른쪽 패널에서.
    예: '서류끼리 다른 값 1개 고르기 · 빈 칸 2개(선적일·재질) — ③에서 입력'"""
    skip = {C_BL} if not r.shipment_key else set()  # B/L 없음은 둘째 줄에 한 번만
    empty = [
        _short(c)
        for c, f in r.cells.items()
        if f.flag == "need_input" and f.final_value is None and c not in skip
    ]
    check = [
        _short(c)
        for c, f in r.cells.items()
        if f.flag == "need_check" and f.final_value is None and c not in skip
    ]

    def names(xs: list[str]) -> str:
        return "·".join(xs[:3]) + (" 외" if len(xs) > 3 else "")

    parts = []
    if n_open:
        parts.append(f"서류끼리 다른 값 {n_open}개 고르기")
    if empty:
        parts.append(f"빈 칸 {len(empty)}개({names(empty)}) — ③에서 입력")
    if check:
        parts.append(f"확인할 칸 {len(check)}개({names(check)})")
    if not parts:
        return f"고른 값 {n_done}개 — 할 일 없음" if n_done else "할 일 없음"
    return " · ".join(parts)


def _card(r: HistoryRow) -> dict:
    """카드 제목 정보(HS 11/27): 제품명(한글, 없으면 영문) · 모델, B/L 줄, B/L 없으면 구분용 파일 이름."""
    import re as _re

    ko = _re.sub(r"\([^)]*\)\s*$", "", r.text(C_NAME_KO)).strip()
    if "자료 추가 필요" in ko:
        ko = ""
    name = ko or r.text("영문 제품명").strip()
    model = r.model or (" / ".join(r.source_models.values()) if r.source_models else "")
    if r.is_part and name and "부분품" not in name:
        name += " 부분품"
    hint = ""
    if not r.shipment_key:
        for did in r.source_doc_ids:
            got = work_db.get_document(did)
            if got and got[0].doc_type in ("CI", "PL"):
                hint = got[1]
                break
    return {
        "name": name or ("품목을 읽지 못함" if not model else ""),
        "model": model,
        "bl_text": f"B/L {r.shipment_key}" if r.shipment_key else "B/L 번호 없음 → ①에서 입력",
        "parts": len(r.part_lines),
        "hint": hint,
    }


def review_rows(shipper_id: str) -> dict:
    """{rows: [{row_id, bl, label, open[], done[], reasons[], open_row, done_row}], counts: {open, done, all},
    by_bl: {bl: {open_items, done_items}}}. 필터와 숫자는 이 결과 하나로 센다.
    - 미해결 행: 풀리지 않은 대조 항목이 있거나, 입력·확인할 칸이 있는 행(승인 행 제외)
    - 해결됨 행: 사람이 고른 대조 항목이 하나라도 있는 행(미해결 항목이 같이 있어도 보인다)"""
    rows_by_id = {r.row_id: r for r in work_db.list_rows(shipper_id)}
    acc: dict[str, dict] = {}
    by_bl: dict[str, dict] = {}
    lead: dict[str, str] = {}  # B/L → 그 건의 첫 행(선적 건 단위 항목은 여기서만 보인다)
    for r in rows_by_id.values():
        if r.shipment_key:
            lead.setdefault(r.shipment_key, r.row_id)
    for it in list_mismatches(shipper_id):
        r = rows_by_id.get(it["row_id"])
        if r is None:
            continue
        if is_shipment_item(it) and r.shipment_key and lead.get(r.shipment_key) != r.row_id:
            continue  # 같은 서류 차이가 행마다 되풀이되지 않게(HS 11/27)
        bl = it.get("bl_no") or "(B/L 없음)"
        cur = acc.setdefault(
            r.row_id,
            {
                "row_id": r.row_id,
                "bl": it.get("bl_no", ""),
                "label": _row_label(r),
                **_card(r),
                "open": [],
                "done": [],
            },
        )
        key = "done" if it["status"] == STATUS_DONE else "open"
        cur[key].append(friendly_item(it))
        b = by_bl.setdefault(bl, {"open_items": 0, "done_items": 0})
        b[f"{key}_items"] += 1
    for r in rows_by_id.values():
        if r.locked or r.status == "승인":
            continue
        reasons = _reasons(r)
        if not reasons and r.row_id not in acc:
            continue
        cur = acc.setdefault(
            r.row_id,
            {
                "row_id": r.row_id,
                "bl": r.text(C_BL),
                "label": _row_label(r),
                **_card(r),
                "open": [],
                "done": [],
            },
        )
        cur["reasons"] = reasons
    out = []
    for cur in acc.values():
        cur.setdefault("reasons", [])
        r = rows_by_id[cur["row_id"]]
        cur["todo"] = _todo(r, len(cur["open"]), len(cur["done"]))
        cur["open_row"] = bool(cur["open"] or cur["reasons"])
        cur["done_row"] = bool(cur["done"])
        out.append(cur)
    out.sort(key=lambda x: (not x["open_row"], x["bl"], x["label"]))
    return {
        "rows": out,
        "counts": {
            "open": sum(1 for x in out if x["open_row"]),
            "done": sum(1 for x in out if x["done_row"]),
            "all": len(out),
        },
        "by_bl": by_bl,
    }
