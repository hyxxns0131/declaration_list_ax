"""모델 코드·제조사 칸·품명 (RULES 11-2, 11-7 표기). 가상(DEMO) 값."""

from app.a3_judge.history_lookup.model_key import (
    is_part_name,
    join_maker,
    main_product,
    model_from_name,
    norm_company,
    product_base,
    same_model,
    split_maker,
)


def test_split_and_join_maker():
    assert split_maker("DEMO MAKER CO.,LTD. (CN000000001)") == (
        "DEMO MAKER CO.,LTD.",
        "CN000000001",
    )
    assert split_maker("DEMO MAKER") == ("DEMO MAKER", "")
    assert split_maker("") == ("", "")
    assert join_maker("DEMO MAKER", "CN000000001") == "DEMO MAKER (CN000000001)"
    assert join_maker("DEMO MAKER", "") == "DEMO MAKER"


def test_same_model_exact_only():
    """괄호 안 모델 코드가 정확히 같아야 같은 모델 (RULES 11-2: CR-0655F ≠ CR-0655FR)."""
    assert same_model("DEMO-M01", " demo-m01 ")
    assert not same_model("DEMO-0655F", "DEMO-0655FR")
    assert not same_model("", "")


def test_model_from_name():
    assert model_from_name("RICE COOKER(DEMO-M01)") == "DEMO-M01"
    assert model_from_name("rice cooker (demo-m01) ") == "DEMO-M01"
    assert model_from_name("INNER POT") == ""


def test_model_from_name_with_trailing_words():
    """괄호 뒤에 SPARE PARTS·수기 표시가 붙어도 모델 코드를 찾는다 (11/26)."""
    assert model_from_name("RICE COOKER(DEMO-M01) SPARE PARTS") == "DEMO-M01"
    assert model_from_name("RICE COOKER(DEMO-M01) 정밀검사") == "DEMO-M01"
    assert model_from_name("POT(SIZE)(DEMO-P14)") == "DEMO-P14"  # 여러 개면 마지막


def test_norm_company_ignores_marks_and_case():
    assert norm_company("Demo Maker Co., Ltd.") == norm_company("DEMO MAKER CO.,LTD")


def test_product_base_and_parts():
    assert product_base("전기밥솥(DEMO-M01)") == "전기밥솥"
    assert product_base("전기밥솥 부분품") == "전기밥솥부분품"
    assert is_part_name("전기밥솥(DEMO-M01) 부분품") and is_part_name("전기밥솥 부속품")
    assert not is_part_name("전기밥솥(DEMO-M01)")
    assert main_product("전기밥솥 부분품") == "전기밥솥"
    assert main_product("전기밥솥(DEMO-M01)") == "전기밥솥"
