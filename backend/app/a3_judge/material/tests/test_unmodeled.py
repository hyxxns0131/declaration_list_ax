"""모델 코드 없는 행 → 영문명이 같은 이력. 보수적으로(글자 같아야, 재질 엇갈리면 안 고름). 가상 행."""

from app.a3_judge.material.unmodeled import find_by_name, name_key
from app.core.schema.history import C_BL, C_MATERIAL, C_NAME_EN, HistoryRow


def hist(rid, name, mat, is_part=True, bl="BLTEST001"):
    r = HistoryRow(row_id=rid, shipper_id="A", model="", is_part=is_part)
    r.set_ai(C_NAME_EN, name)
    r.set_ai(C_MATERIAL, mat)
    r.set_ai(C_BL, bl)
    return r


def test_name_key_ignores_spaces_and_punct():
    assert name_key("Inner-Pot") == name_key("INNER POT") == "INNERPOT"
    assert name_key("INNER POT 2L") != name_key("INNER POT")


def test_finds_same_name_part():
    past, note = find_by_name([hist("h1", "INNER POT", "금속제(불소수지도장)")], "inner pot", True)
    assert past and past.row_id == "h1" and "확인 필요" in note


def test_part_vs_finished_must_match():
    past, note = find_by_name([hist("h1", "INNER POT", "금속제", is_part=False)], "INNER POT", True)
    assert past is None and "같은 이력 없음" in note


def test_conflicting_materials_not_chosen():
    h = [hist("h1", "STEAM PLATE", "폴리프로필렌"), hist("h2", "STEAM PLATE", "스테인레스")]
    past, note = find_by_name(h, "STEAM PLATE", True)
    assert past is None and "서로 달라" in note


def test_no_name():
    assert find_by_name([], "", True) == (None, "")
