"""부분품 시트가 본품 줄을 다시 적어도 줄이 두 번 들어가지 않는다 (HS 11/27). 가상 값만 쓴다. 담당: KHS"""

from app.a0_reader.extract.service import _merge_part_sheet
from app.core.schema.document import DocumentLine, ParsedDocument


def test_repeated_main_lines_not_duplicated():
    main = ParsedDocument(
        doc_id="d",
        shipper_id="A",
        folder_id="f",
        doc_type="CI",
        lines=[
            DocumentLine(model="RC-100", quantity=10, amount=100),
            DocumentLine(model="P-1", quantity=6, is_part=True),
        ],
    )
    extra = [
        DocumentLine(model="RC-100", quantity=10, amount=100, is_part=True),
        DocumentLine(model="P-1", quantity=6, amount=5, is_part=True),
        DocumentLine(model="P-2", quantity=2, amount=1, is_part=True),
    ]
    _merge_part_sheet(main, extra)
    assert [ln.model for ln in main.lines] == ["RC-100", "P-1", "P-2"]
    assert main.lines[0].is_part is False
    assert main.lines[1].amount == 5
    assert sum(ln.amount or 0 for ln in main.lines) == 106


def test_part_line_with_parent_model_matched_by_description():
    main = ParsedDocument(
        doc_id="d",
        shipper_id="A",
        folder_id="f",
        doc_type="PL",
        lines=[
            DocumentLine(
                model="P-1", description="INNER POT", quantity=6, cartons=1, net_kg=2, is_part=True
            )
        ],
    )
    _merge_part_sheet(
        main,
        [
            DocumentLine(
                model="RC-100",
                description="INNER POT",
                quantity=6,
                cartons=1,
                amount=9,
                is_part=True,
            )
        ],
    )
    assert len(main.lines) == 1 and main.lines[0].amount == 9
