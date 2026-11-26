"""재질 표기 정리 (RULES 11-4: 재질 코드명, 가나다 순, 쉼표 구분, 약어 변환·추측 금지). 가상 값."""

from app.a3_judge.material.codes import material_list, normalize, split_materials

ALIASES = {"PP": "폴리프로필렌", "스테인리스": "금속제"}


def test_split_marks():
    assert split_materials("금속제, 폴리프로필렌") == ["금속제", "폴리프로필렌"]
    assert split_materials("금속제/폴리프로필렌·고무제") == ["금속제", "폴리프로필렌", "고무제"]
    assert split_materials("  ") == []


def test_commas_inside_parentheses_kept():
    """괄호 안 쉼표·가운뎃점은 나누지 않는다(재질 코드명의 일부, 11/25 결정)."""
    assert split_materials("합성수지제(PP, PE), 금속제") == ["합성수지제(PP, PE)", "금속제"]
    assert normalize("고무제(실리콘·불소), 금속제", {}) == ("고무제(실리콘·불소), 금속제", False)
    assert normalize("금속제, 합성수지제(PP, PE)", {}) == ("금속제, 합성수지제(PP, PE)", False)


def test_normalize_alias_sort_dedupe():
    """약어는 대소문자 상관없이 바꾸고, 중복 제거 후 가나다 순."""
    assert normalize("pp, 금속제, PP", ALIASES) == ("금속제, 폴리프로필렌", False)
    assert normalize("스테인리스", ALIASES) == ("금속제", False)


def test_unknown_name_kept_and_flagged():
    """공식 코드명 목록에 없으면 바꾸지 않고 그대로 두되 '확인 필요'(추측 금지, AGENTS 0-5)."""
    known = {"금속제", "폴리프로필렌"}
    assert normalize("금속제, 이상한재질", ALIASES, known) == ("금속제, 이상한재질", True)
    assert normalize("PP", ALIASES, known) == ("폴리프로필렌", False)


def test_known_none_skips_check():
    """코드명 목록을 못 읽으면(Supabase 연결 없음) 확인을 건너뛴다."""
    assert normalize("이상한재질", {}, None) == ("이상한재질", False)


def test_material_list_need_input_is_empty():
    assert material_list("현품사진·한글표시 자료 추가 필요 (DEMO-M01)") == []
    assert material_list("") == []
    assert material_list("금속제, 폴리프로필렌") == ["금속제", "폴리프로필렌"]
