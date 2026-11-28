"""같은 공장: 코드 같음 / 코드 달라도 주소 같음(갱신 추정) / 다름. 가상 주소."""

from app.a3_judge.factory.same_factory import same_factory

ADDR = "No. 8, Demo East Road, Alpha Town"


def test_same_factory():
    assert same_factory("cn1", "", "CN1", "") == "코드"
    assert same_factory("CN1", "No 8 Demo East Road Alpha Town", "CN0", ADDR) == "주소"
    assert same_factory("CN1", "NO.25 OTHER ROAD", "CN0", ADDR) is None
    assert same_factory("", "", "", "") is None
