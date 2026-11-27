"""모선명: 유니패스 값을 자동으로 쓰고, 서류와 다르면 참고로만 보인다(HS 결정 11/27).
유니패스 값이 없으면 서류끼리 대조(다르면 불일치). 가상 값만. 담당: KHS"""

from app.a1_history.crosscheck.service import (
    STATUS_BAD,
    STATUS_OK,
    STATUS_REF,
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


def test_different_ship_uses_unipass_and_only_notes():
    row = _row("SKY ORION")
    it = _vessel(row, [_bl("CA MANILA/2615N")])
    assert it["status"] == STATUS_REF and not it["different"]  # 막지 않는다
    cell = row.cells[C_VESSEL]
    assert cell.ai_value == "SKY ORION" and cell.flag == "ok"  # 유니패스 값이 리스트에 들어감
    assert "모선: 유니패스 값 사용, 서류 BL CA MANILA/2615N" in row.text("비고")
    # AI가 다르다고 해도 막지 않는다
    from app.a1_history.crosscheck.service import merge_ai

    items = crosscheck_row(row, [_bl("CA MANILA/2615N")], [row])
    merge_ai(items, {"모선": {"same": False, "what": "가짜 AI"}})
    v = next(i for i in items if i["item"] == "모선")
    assert not v["different"] and v["status"] == STATUS_REF


def test_blocked_vessel_comes_back_when_unipass_arrives():
    """예전에 서류끼리 달라 막혔던 칸도 유니패스 값이 생기면 그 값으로 채운다."""
    row = _row("SKY ORION")
    row.cells[C_VESSEL].ai_value = None
    row.cells[C_VESSEL].flag = "mismatch"
    _vessel(row, [_bl("CA MANILA/2615N")])
    assert row.cells[C_VESSEL].ai_value == "SKY ORION" and row.cells[C_VESSEL].flag == "ok"


def test_without_unipass_documents_are_compared():
    row = HistoryRow(
        row_id="r", shipper_id="A", model="RC-100", cells={C_VESSEL: Field(ai_value="CA MANILA")}
    )
    ci = ParsedDocument(
        doc_id="c", shipper_id="A", folder_id="f", doc_type="CI", vessel="SKY ORION"
    )
    it = _vessel(row, [ci, _bl("CA MANILA/2615N")])
    assert it["status"] == STATUS_BAD and it["different"] and UNIPASS not in it
    assert row.cells[C_VESSEL].ai_value is None and row.cells[C_VESSEL].flag == "mismatch"
