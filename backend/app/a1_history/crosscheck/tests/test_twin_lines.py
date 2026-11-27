"""같은 모델 여러 줄 짝짓기 + 리스트 값만 다를 때 불일치 (HS 11/27). 가상 값만 쓴다. 담당: KHS"""

from app.a1_history.crosscheck.service import _lines_for, item
from app.core.schema.document import DocumentLine, ParsedDocument
from app.core.schema.history import HistoryRow


def test_same_model_two_lines_pair_in_order():
    doc = ParsedDocument(
        doc_id="d",
        shipper_id="A",
        folder_id="f",
        doc_type="CI",
        lines=[DocumentLine(model="RC-100", cartons=900), DocumentLine(model="RC-100", cartons=1)],
    )
    a = HistoryRow(row_id="r1", shipper_id="A", model="RC-100")
    b = HistoryRow(row_id="r2", shipper_id="A", model="RC-100")
    assert _lines_for(a, doc, [a, b])[0].cartons == 900
    assert _lines_for(b, doc, [a, b])[0].cartons == 1
    assert len(_lines_for(a, doc, [a])) == 2  # 행 수가 다르면 전부 합쳐 비교
    bl = doc.model_copy(
        update={"doc_type": "BL", "lines": [DocumentLine(model="RC-100", cartons=901)]}
    )
    assert _lines_for(a, bl, [a, b]) == []  # 합계 한 줄은 행 하나와 비교하지 않는다


def test_list_value_differs_from_agreeing_docs():
    it = item("카톤 수", 900.0, 900.0, None, 1.0, "카톤 수")
    assert it["different"] and it["list_diff"] and it["status"] == "불일치"
    assert not item("카톤 수", 900.0, 900.0, None, 900.0, "카톤 수")["different"]
