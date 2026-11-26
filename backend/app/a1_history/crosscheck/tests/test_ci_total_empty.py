"""CI 금액 TOTAL 대조: 값이 없으면 막지 않고 '비어 있음'만 표시 (HS 11/26). 가상 값만. 담당: KHS"""

from app.a1_history.crosscheck.service import (
    CI_TOTAL_ITEM,
    STATUS_BAD,
    STATUS_EMPTY,
    apply_flags,
    crosscheck_row,
    merge_ai,
)
from app.core.schema.document import DocumentLine, ParsedDocument
from app.core.schema.history import HistoryRow


def _ci(total: float | None, amount: float | None) -> ParsedDocument:
    return ParsedDocument(
        doc_id="ci",
        shipper_id="A",
        folder_id="f",
        doc_type="CI",
        total_amount=total,
        lines=[DocumentLine(model="RC-100", amount=amount)],
    )


def _item(row: HistoryRow, ci: ParsedDocument) -> dict:
    items = crosscheck_row(row, [ci], [row])
    merge_ai(items, {CI_TOTAL_ITEM: {"same": False, "what": "가짜 AI"}})
    apply_flags(row, items)
    return next(i for i in items if i["item"] == CI_TOTAL_ITEM)


def test_ci_total_missing_shows_empty():
    row = HistoryRow(row_id="r", shipper_id="A", model="RC-100")
    it = _item(row, _ci(None, 1040))
    assert it["status"] == STATUS_EMPTY and not it["different"] and it["ai"] is None
    assert "CI 금액 TOTAL (시트 칸 = 줄 합) 비어 있음" in row.text("비고")


def test_ci_total_still_checked_when_present():
    row = HistoryRow(row_id="r", shipper_id="A", model="RC-100")
    it = _item(row, _ci(2510, 1250))
    assert it["status"] == STATUS_BAD and it["different"]
