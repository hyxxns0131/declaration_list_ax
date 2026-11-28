"""제자리로 옮긴 규칙: 부속품 → 본품 실적(한 방향), 재질 구분 거르기. 가상 값."""

from app.a3_judge.record_pick.spare_rule import same_product
from app.a3_judge.record_pick.spec_filter import spec_ok, split_by_spec


def test_spare_to_main_one_way():
    assert same_product("전기밥솥 부분품(RC-100)", ["전기밥솥(RC-100)"])
    assert not same_product("전기밥솥(RC-100)", ["전기밥솥 부분품"])
    assert not same_product("전기밥솥 부분품", ["전기밥솥"], spare_to_main=False)
    assert same_product("아무거나", [])


def test_spec_ok_and_split():
    assert spec_ok("깊이 3cm, 용량 1.2L", "용량 1200ml 깊이 30mm")
    assert not spec_ok("깊이 2cm", "깊이 3cm")
    assert spec_ok("깊이 2cm", "깊이 3cm", enabled=False)
    assert spec_ok("", "깊이 3cm")
    kept, skipped, no_spec = split_by_spec(
        ["a", "b", "c"], "깊이 3cm", {"a": "깊이 3cm", "b": "깊이 2cm", "c": ""}.get
    )
    assert kept == ["a", "c"] and skipped == ["b"] and no_spec is True
