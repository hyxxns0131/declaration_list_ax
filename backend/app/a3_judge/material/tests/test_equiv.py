"""라벨 표기 ↔ 재질 코드명 같은 재질인지. 애매하면 unknown(확인 필요). 가상 값(약어표도 시험용)."""

from app.a3_judge.material.equiv import compare, compare_sets, split_code_name

ALIASES = {"PP": "폴리프로필렌", "실리콘": "실리콘고무"}  # 시험용 약어표
KNOWN = {"금속제(불소수지도장)", "스테인레스", "폴리프로필렌", "유리제", "도자기제", "실리콘고무"}


def test_split_code_name():
    assert split_code_name("금속제(불소수지도장)") == ("금속제", "불소수지도장")
    assert split_code_name("유리제") == ("유리제", "")


def test_coating_label_matches_detail():
    assert compare("불소수지", "금속제(불소수지도장)") == "same"
    assert compare("불소수지 코팅", "금속제(불소수지도장)") == "same"


def test_spelling_and_aliases():
    assert compare("스테인리스", "스테인레스") == "same"
    assert compare("Stainless Steel", "스테인레스") == "same"
    assert compare("PP", "폴리프로필렌", ALIASES) == "same"
    assert compare("유리", "유리제") == "same"


def test_base_only_with_detail_is_unknown():
    """'금속'만 적힌 라벨로는 코팅 여부를 모름."""
    assert compare("금속", "금속제(불소수지도장)") == "unknown"


def test_different_known_material():
    assert compare("PP", "스테인레스", ALIASES, KNOWN) == "different"
    assert compare("도자기제", "유리제", None, KNOWN) == "different"
    assert compare("이상한재질", "유리제", None, KNOWN) == "unknown"


def test_compare_sets():
    got = compare_sets(
        ["불소수지 코팅", "PP", "알수없음"],
        ["금속제(불소수지도장)", "폴리프로필렌"],
        ALIASES,
        KNOWN,
    )
    assert got == {"불소수지 코팅": "same", "PP": "same", "알수없음": "unknown"}
