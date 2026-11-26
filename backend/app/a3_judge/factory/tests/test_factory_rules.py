"""해외제조업소 코드 고르기 경계 (RULES 11-7): 정상 등록만, 애매하면 수기, 과거 코드와 다르면 확인. 가상 값."""

from app.a3_judge.factory.address import addr_score, same_address
from app.a3_judge.factory.choose import MANUAL, choose_factory

F1 = {"code": "CN1", "address": "NO.8 DEMO EAST ROAD, ALPHA TOWN", "status": "정상"}
F2 = {"code": "CN2", "address": "NO.25 SAMPLE WEST ROAD, BETA TOWN", "status": "정상"}
F3 = {"code": "CN3", "address": "NO.8 DEMO EAST ROAD, ALPHA TOWN SECOND", "status": "정상"}
CANCELED = {"code": "CN9", "address": "NO.8 DEMO EAST ROAD, ALPHA TOWN", "status": "취소"}
DOC = "No.8 Demo East Road, Alpha Town"


def test_house_number_different_lowers_score():
    """번지 숫자가 다르면 점수를 크게 깎는다."""
    same_street = addr_score("NO.8 DEMO ROAD, ALPHA", "NO.9 DEMO ROAD, ALPHA")
    assert same_street < addr_score("NO.8 DEMO ROAD, ALPHA", "NO.8 DEMO ROAD, ALPHA")


def test_same_address_needs_both():
    assert not same_address("", F1["address"]) and same_address(DOC, F1["address"])


def test_canceled_factory_not_chosen():
    got = choose_factory("DEMO", DOC, [CANCELED, F2], set())
    assert got.code != "CN9"
    only_canceled = choose_factory("DEMO", DOC, [CANCELED], set())
    assert (
        only_canceled.code == ""
        and only_canceled.need_check
        and "정상 등록 공장 없음" in only_canceled.notes[0]
    )


def test_close_scores_go_manual_with_candidates():
    """1등과 2등 점수 차가 0.1보다 작으면 고르지 않고 후보를 보여 준다(보수적으로)."""
    got = choose_factory("DEMO", DOC, [F1, F3], set())
    assert got.code == "" and got.need_check and MANUAL in got.notes[-1]
    assert {c["code"] for c in got.candidates} == {"CN1", "CN3"}


def test_address_choice_differs_from_past_needs_check():
    got = choose_factory("DEMO", DOC, [F1, F2], {"CN2"})
    assert got.code == "CN1" and got.how == "address" and got.need_check
    assert "이전 신고 공장" in got.notes[0]


def test_past_code_used_when_no_address():
    got = choose_factory("DEMO", "", [F1, F2], {"CN2"})
    assert got.code == "CN2" and got.how == "past" and got.need_check


def test_settings_thresholds():
    """기준 점수는 설정값으로 바꿀 수 있다(코드에 박지 않음)."""
    strict = choose_factory("DEMO", DOC, [F1, F2], set(), min_score=1.01)
    assert strict.code == ""
