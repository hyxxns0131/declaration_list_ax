"""해외제조업소 코드 고르기(RULES 11-7)."""

from app.a3_judge.factory.address import addr_score
from app.a3_judge.factory.choose import MANUAL, choose_factory

F = [
    {"code": "CN1", "address": "NO. 1 TEST ROAD, SAMPLE DISTRICT, VIRTUAL CITY", "status": "정상"},
    {"code": "CN2", "address": "NO. 77 OTHER ROAD, ELSEWHERE TOWN, VIRTUAL CITY", "status": "정상"},
]


def test_spacing_only_difference_is_same_address():
    assert addr_score("12 DONG CHENG ROAD, X", "12 DONGCHENG ROAD, X") >= 0.45


def test_address_match_picks_factory():
    got = choose_factory("V", "NO.1 TEST ROAD SAMPLE DISTRICT VIRTUAL CITY", F, set())
    assert got.code == "CN1" and not got.need_check


def test_past_code_preferred_when_rule_on():
    got = choose_factory(
        "V", "NO.1 TEST ROAD SAMPLE DISTRICT VIRTUAL CITY", F, {"CN2"}, prefer_past=True
    )
    assert got.code == "CN2" and got.need_check


def test_manual_when_nothing_fits():
    got = choose_factory("V", "SOMEWHERE ELSE 999", F, set())
    assert got.code == "" and MANUAL in got.notes


def test_no_registered_factory():
    assert choose_factory("V", "", [], set()).how == "none"
