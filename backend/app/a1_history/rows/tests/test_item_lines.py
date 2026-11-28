"""품목이 아닌 줄(바코드 줄·제목 줄)은 행을 만들지 않는다 (HS 11/27). 가상 값만 쓴다. 담당: KHS"""

from app.a1_history.rows.build import item_lines, pair_lines
from app.core.schema.document import DocumentLine, ParsedDocument


def _doc(t: str, lines: list[DocumentLine]) -> ParsedDocument:
    return ParsedDocument(doc_id=t, shipper_id="A", folder_id="f", doc_type=t, lines=lines)


def test_barcode_and_title_lines_do_not_make_rows():
    pl = [
        DocumentLine(description="CERAMIC PLATE"),  # 제목 줄
        DocumentLine(model="RC-100", quantity=10, net_kg=8.0),
        DocumentLine(model="UPC 0000000000001", net_kg=0.5, cartons=2),  # 바코드 줄
        DocumentLine(model="RC-200", quantity=5, net_kg=4.0),
        DocumentLine(model="UPC 0000000000002"),
    ]
    got = item_lines(pl)
    assert [x.model for x in got] == ["RC-100", "RC-200"]
    assert got[0].net_kg == 8.0 and got[0].cartons == 2  # 빈 칸만 채움


def test_pair_lines_rows_equal_ci_models():
    ci = _doc(
        "CI", [DocumentLine(model="RC-100", amount=10), DocumentLine(model="RC-200", amount=5)]
    )
    pl = _doc(
        "PL",
        [
            DocumentLine(description="TITLE"),
            DocumentLine(model="RC-100", net_kg=8.0),
            DocumentLine(model="UPC 1"),
            DocumentLine(model="RC-200", net_kg=4.0),
        ],
    )
    assert len(pair_lines(ci, pl)) == 2


def test_line_without_model_but_with_numbers_is_kept():
    got = item_lines([DocumentLine(description="SPARE PART", quantity=3, amount=9)])
    assert len(got) == 1
