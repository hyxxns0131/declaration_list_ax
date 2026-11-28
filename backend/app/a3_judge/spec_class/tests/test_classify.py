"""재질 구분 자동 입력 (RULES 11-5): 유리제는 코드명 표시로만, 나머지 4종은 담당자 입력. 가상 값."""

from app.a3_judge.spec_class.classify import auto_spec, families_in


def test_not_one_of_four_families():
    assert auto_spec(["금속제", "폴리프로필렌"]) == (None, "")


def test_glass_heat_from_code_name():
    assert auto_spec(["유리제(가열조리용)"])[0] == "가열조리용"
    assert (
        auto_spec(["유리제(전자레인지용)"])[0] == "가열조리용"
    )  # 직화·오븐·전자레인지·열탕 = 가열조리용
    assert auto_spec(["유리제"])[0] == "가열조리용 이외"
    assert "깊이·용량은 담당자 입력" in auto_spec(["유리제"])[1]


def test_others_need_manual_input():
    value, memo = auto_spec(["도자기제", "금속제"])
    assert value is None and "도자기제" in memo and "입력 필요" in memo


def test_glass_with_other_family_manual():
    """유리제와 도자기제가 함께면 자동으로 정하지 않는다."""
    assert auto_spec(["유리제", "도자기제"])[0] is None
    assert families_in(["법랑", "옹기류", "유리제"]) == ["유리제", "법랑", "옹기류"]


def test_judge_spec_keeps_typed_value_and_lists_missing():
    """담당자가 적은 칸은 그대로 두고, 모자란 입력만 비고에."""
    from app.a3_judge.spec_class.classify import judge_spec

    j = judge_spec(["도자기제"], "깊이 3cm")
    assert j.ai_value is None and j.missing == ["용량"] and "용량 입력 필요" in j.note
    j = judge_spec(["도자기제"], "깊이 3cm, 용량 1.2L")
    assert j.note == "" and j.missing == []
    j = judge_spec(["도자기제"], "")
    assert j.ai_value is None and "입력 필요" in j.note
    assert judge_spec(["금속제"], "").families == []


def test_glass_unclear_heat_mark_needs_check():
    """'(가열조용)'처럼 글자가 빠진 표기는 자동으로 '가열조리용 이외'를 넣지 않는다. 가상 값."""
    value, memo = auto_spec(["무착색유리제(가열조용)", "스테인레스"])
    assert value is None and "확인 필요" in memo
    assert auto_spec(["무착색유리제(가열조리용)"])[0] == "가열조리용"
    assert auto_spec(["유리제(가열조리용 이외)"])[0] == "가열조리용 이외"
    assert auto_spec(["유리제(가열조리용)", "유리제"])[0] is None  # 둘이 섞이면 담당자 확인
