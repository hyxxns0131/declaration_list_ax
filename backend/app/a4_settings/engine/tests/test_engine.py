from app.a4_settings.engine.service import get_rules, merge_rules, rule


def test_shipper_overrides_default():
    s = merge_rules(
        {"merge_spare_parts": False, "color_check": True}, {"merge_spare_parts": True}, "A"
    )
    assert s.merge_spare_parts is True and s.color_check is True and s.shipper_id == "A"


def test_group_by_maker_cannot_be_turned_off():
    s = merge_rules({}, {"group_by_maker": False}, "X")
    assert rule(s, "group_by_maker") is True


def test_unknown_shipper_uses_default():
    s = get_rules("NO_SUCH_SHIPPER")
    assert s.required_docs == ["CI", "PL", "BL", "CO"]
    assert s.merge_spare_parts is False


def test_sample_shippers_differ():
    a, b = get_rules("A"), get_rules("B")
    assert a.merge_spare_parts and not b.merge_spare_parts
    assert rule(b, "group_by_color") is True and b.max_rows_per_declaration == 5
