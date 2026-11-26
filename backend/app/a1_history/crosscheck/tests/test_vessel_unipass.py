"""모선명: 서류 모선 ↔ 유니패스 모선 대조, 다르면 불일치로 알리고 담당자가 고른다(HS 결정 11/26). 가상 값만. 담당: KHS"""

from app.a1_history.crosscheck.service import (
    STATUS_BAD,
    STATUS_OK,
    UNIPASS,
    apply_flags,
    crosscheck_row,
    vessel_name,
)
from app.a1_history.rows.build import UNIPASS_VESSEL
from app.core.schema.document import ParsedDocument
from app.core.schema.fields import Evidence, Field
from app.core.schema.history import C_VESSEL, HistoryRow


def _row(unipass: str) -> HistoryRow:
    ev = [Evidence(source="UNIPASS", ref="BL1", note=UNIPASS_VESSEL + unipass)]
    return HistoryRow(
        row_id="r",
        shipper_id="A",
        model="RC-100",
        cells={C_VESSEL: Field(ai_value=unipass, evidence=ev)},
    )


def _bl(vessel: str) -> ParsedDocument:
    return ParsedDocument(doc_id="b", shipper_id="A", folder_id="f", doc_type="BL", vessel=vessel)


def _vessel(row: HistoryRow, docs: list[ParsedDocument]) -> dict:
    items = crosscheck_row(row, docs, [row])
    apply_flags(row, items)
    return next(i for i in items if i["item"] == "모선")


def test_vessel_name_ignores_voyage_and_spaces():
    assert vessel_name("SKY ORION / 2612N") == vessel_name("SKY ORION") == "SKYORION"
    assert vessel_name("VIRTUAL STAR 101E") == "VIRTUALSTAR"


def test_same_ship_is_ok():
    row = _row("VIRTUAL STAR")
    it = _vessel(row, [_bl("VIRTUAL STAR / 101E")])
    assert it["status"] == STATUS_OK and it[UNIPASS] == "VIRTUAL STAR"
    assert row.cells[C_VESSEL].ai_value == "VIRTUAL STAR"


def test_different_ship_is_mismatch_and_blocked():
    row = _row("SKY ORION")
    it = _vessel(row, [_bl("CA MANILA/2615N")])
    assert it["status"] == STATUS_BAD and it["different"]
    cell = row.cells[C_VESSEL]
    assert (
        cell.ai_value is None and cell.flag == "mismatch"
    )  # 담당자가 고르기 전에는 리스트에 안 들어감
    assert "유니패스 SKY ORION" in cell.memo and "BL CA MANILA/2615N" in cell.memo
    # 다시 대조해도 유니패스 값은 근거에 남아 있어 같은 결과
    assert _vessel(row, [_bl("CA MANILA/2615N")])[UNIPASS] == "SKY ORION"
