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
from app.core.schema.history import C_MODEL, HistoryRow
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
    local_db.audit("resolve", row_id, ",".join(c.item for c in choices))
    rows_service.rejudge(
        row.shipper_id, [row_id]
    )  # 고른 값으로 아래 단계(판단·신고건) 다시, final_value 유지
    got = work_db.get_row(row_id)
    assert got is not None
    return got


__all__ = ["DOC_COLS", "Choice", "crosscheck_all", "list_mismatches", "resolve"]
