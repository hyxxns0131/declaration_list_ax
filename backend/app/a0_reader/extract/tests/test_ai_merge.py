"""AI 보충: 규칙 줄의 빈 칸만 채우기, 엑셀 격자 → 탭 글자 (HS 11/26). 가상 값만 쓴다. 담당: KHS"""

from app.a0_reader.extract.ai_read import grid_text
from app.a0_reader.extract.service import lines_incomplete, merge_lines
from app.core.schema.document import DocumentLine, ParsedDocument


def _doc(doc_type: str, lines: list[DocumentLine]) -> ParsedDocument:
    return ParsedDocument(doc_id="d", shipper_id="A", folder_id="f", doc_type=doc_type, lines=lines)


def test_merge_fills_only_empty_line_fields():
    doc = _doc("PL", [DocumentLine(model="RC-100", net_kg=80), DocumentLine(model="RC-200")])
    assert lines_incomplete(doc)
    ai = [
        DocumentLine(model="RC 200", cartons=9, qty_per_carton=1, net_kg=90),
        DocumentLine(model="RC-100", cartons=8, qty_per_carton=1, net_kg=999),
    ]
    n = merge_lines(doc, ai, "llm")
    assert n == 5
    assert doc.lines[0].net_kg == 80  # 규칙 값은 덮지 않는다
    assert doc.lines[0].cartons == 8
    assert doc.lines[1].cartons == 9 and doc.lines[1].net_kg == 90
    assert doc.sources["lines.cartons"] == "llm"
    assert not lines_incomplete(doc)


def test_merge_takes_ai_lines_when_rules_found_none():
    doc = _doc("CI", [])
    merge_lines(doc, [DocumentLine(model="RC-100", amount=1040)], "llm:image")
    assert doc.lines[0].amount == 1040 and doc.sources["lines"] == "llm:image"


def test_grid_text_tab_rows():
    assert grid_text([["MODEL", "CTNS"], [None, ""], ["RC-100", 8]]) == "MODEL\tCTNS\nRC-100\t8"


def test_merge_fills_missing_model_by_order():
    doc = _doc("PL", [DocumentLine(net_kg=80), DocumentLine(net_kg=90)])
    merge_lines(
        doc,
        [DocumentLine(model="RC-100", cartons=8), DocumentLine(model="RC-200", cartons=9)],
        "llm",
    )
    assert [ln.model for ln in doc.lines] == ["RC-100", "RC-200"]
    assert doc.lines[0].net_kg == 80 and doc.lines[1].cartons == 9


def test_merge_uses_ai_lines_when_no_models_and_counts_differ():
    doc = _doc("PL", [DocumentLine(net_kg=170)])
    merge_lines(
        doc,
        [DocumentLine(model="RC-100", net_kg=80), DocumentLine(model="RC-200", net_kg=90)],
        "llm",
    )
    assert [ln.model for ln in doc.lines] == ["RC-100", "RC-200"]
