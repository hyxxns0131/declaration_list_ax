"""부분품 줄 기록·모델 바꾸기. 가상 값."""

from app.a3_judge.spare_parts.collect import collect_parts, format_part_line
from app.a3_judge.spare_parts.model_change import apply_model_change, chosen_model
from app.core.schema.document import DocumentLine
from app.core.schema.history import C_MODEL, C_NAME_EN, C_NAME_KO, HistoryRow


def test_collect_parts_and_format():
    lines = [
        DocumentLine(model="RC-100", description="RICE COOKER", cartons=12),
        DocumentLine(
            model="RC-100-IP",
            description="INNER POT (SPARE PART)",
            qty_per_carton=10,
            cartons=2,
            is_part=True,
        ),
        DocumentLine(model="RC-100-SP", description="STEAM PLATE", is_part=True),
    ]
    parts = collect_parts(lines)
    assert [p.part_no for p in parts] == ["RC-100-IP", "RC-100-SP"]
    assert format_part_line(parts[0]) == "RC-100-IP INNER POT (SPARE PART) — 20 PCS, 2 CTNS"
    assert format_part_line(parts[1]) == "RC-100-SP STEAM PLATE — ? PCS, ? CTNS"


def _part_row():
    r = HistoryRow(row_id="r1", shipper_id="A", model="RC-100", is_part=True)
    r.part_lines = ["RC-100-IP INNER POT — 20 PCS, 2 CTNS"]
    r.source_models = {"CI": "RC-100"}
    r.set_ai(C_NAME_EN, "SPARE PARTS FOR RC-100")
    return r


def _final(row, col, value):
    row.set_ai(col, row.text(col) or None)
    row.cells[col].final_value = value


def test_model_cell_final_wins():
    r = _part_row()
    _final(r, C_MODEL, "RC-200")
    assert chosen_model(r) == "RC-200"
    note = apply_model_change(r)
    assert r.model == "RC-200" and note and "RC-200" in note and "RC-100" in note
    assert r.cells[C_NAME_EN].ai_value == "SPARE PARTS FOR RC-200"


def test_model_from_final_korean_name():
    r = _part_row()
    _final(r, C_NAME_KO, "전기밥솥 부분품(RC-300)")
    assert chosen_model(r) == "RC-300"


def test_no_change_no_note():
    r = _part_row()
    assert apply_model_change(r) is None and r.model == "RC-100"


def test_final_english_name_kept():
    """담당자가 고친 영문명은 그대로(프로그램 값만 바뀜)."""
    r = _part_row()
    _final(r, C_NAME_EN, "MY NAME")
    _final(r, C_MODEL, "RC-200")
    apply_model_change(r)
    assert r.text(C_NAME_EN) == "MY NAME"
