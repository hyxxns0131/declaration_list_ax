"""재질 구분 칸 읽기·정리 (RULES 11-5 적는 법). 가상 값."""

from app.a3_judge.spec_class.parse import canonical, missing_inputs, parse_spec, same_spec


def test_parse_examples_from_rules():
    s = parse_spec("깊이 3cm, 용량 1.2L")
    assert (s.depth_cm, s.volume_ml, s.flat, s.heat) == (3.0, 1200.0, None, None)
    assert parse_spec("평판(액체 못 채움)").flat is True
    s = parse_spec("용량 800mL, 가열조리용")
    assert (s.volume_ml, s.heat) == (800.0, True)


def test_units_order_and_spaces():
    """순서·단위가 달라도 같은 값: 30mm = 3cm, 1200ml = 1.2L."""
    assert canonical("용량 1200ml 깊이 30mm") == "깊이 3cm, 용량 1.2L"
    assert same_spec("깊이 3cm, 용량 1.2L", "용량1.2ℓ,깊이 3 cm")
    assert not same_spec("깊이 3cm, 용량 1.2L", "깊이 2cm, 용량 1.2L")


def test_heat_words():
    assert (
        parse_spec("전자레인지용, 용량 500mL").heat is True
    )  # 직화·오븐·전자레인지·열탕 = 가열조리용
    assert parse_spec("가열조리용 이외").heat is False


def test_missing_inputs():
    assert missing_inputs(parse_spec("깊이 3cm")) == ["용량"]
    assert missing_inputs(parse_spec("평판")) == []
    assert missing_inputs(parse_spec("가열조리용")) == ["깊이(또는 평판)", "용량"]


def test_unreadable_text_kept():
    assert canonical("  잘   모름 ") == "잘 모름"
