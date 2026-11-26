"""한글 제품명에 모델명 포함(product_name_with_model): 켜면 붙이고 끄면 뗀다. 담당자 값은 그대로."""

from app.a1_history.rows.names import apply_name_style, style_name
from app.a4_settings.engine.service import merge_rules
from app.core.schema.history import C_NAME_KO, HistoryRow


def test_style_name():
    assert style_name("전기밥솥", "RC-100", True) == "전기밥솥(RC-100)"
    assert style_name("전기밥솥(RC-100)", "RC-100", True) == "전기밥솥(RC-100)"
    assert style_name("전기밥솥(RC-100)", "RC-100", False) == "전기밥솥"
    assert style_name("전기밥솥(RC-100) 부분품", "RC-100", False) == "전기밥솥 부분품"


def test_switch_changes_row_but_keeps_final():
    r = HistoryRow(row_id="r1", shipper_id="T", model="RC-100")
    r.set_ai(C_NAME_KO, "전기밥솥")
    apply_name_style([r], merge_rules({}, {"product_name_with_model": True}, "T"))
    assert r.cells[C_NAME_KO].ai_value == "전기밥솥(RC-100)"
    apply_name_style([r], merge_rules({}, {"product_name_with_model": False}, "T"))
    assert r.cells[C_NAME_KO].ai_value == "전기밥솥"
    r.cells[C_NAME_KO].final_value = "담당자 이름"
    apply_name_style([r], merge_rules({}, {"product_name_with_model": True}, "T"))
    assert r.text(C_NAME_KO) == "담당자 이름"
