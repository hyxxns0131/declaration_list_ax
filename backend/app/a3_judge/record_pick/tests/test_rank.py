"""실적 고르기(RULES 11-8, 기존 precise.choose_approval)."""

from datetime import date

from app.a3_judge.record_pick.rank import choose_record
from app.core.schema.record import Record, SamplePart

ON = date(2026, 11, 25)


def rec(no, mats, approved, code="CN1", names=("전기밥솥",), colors=()):
    return Record(
        record_no=no,
        factory_code=code,
        materials=list(mats),
        approved_on=approved,
        product_names=list(names),
        sample_parts=[SamplePart(material=mats[0], color=c) for c in colors],
    )


def test_most_inclusive_valid_record():
    rs = [
        rec("1", ["A"], "2025-01-01"),
        rec("2", ["A", "B", "C"], "2024-01-01"),
        rec("3", ["A", "B"], "2025-06-01"),
    ]
    got = choose_record(rs, ["A", "B"], "CN1", "", "전기밥솥(M1)", ON)
    assert got.record_no == "2"


def test_expired_skipped_and_reported():
    rs = [rec("9", ["A"], "2020-01-01")]
    got = choose_record(rs, ["A"], "CN1", "", "전기밥솥(M1)", ON)
    assert got.value is None and got.precise_needed and "실적 만료" in got.note


def test_other_factory_is_precise_target():
    got = choose_record(
        [rec("1", ["A"], "2025-01-01", code="CN2")], ["A"], "CN1", "", "전기밥솥", ON
    )
    assert got.precise_needed and "정밀검사 대상" in got.note


def test_spare_uses_main_record_but_not_reverse():
    main = rec("1", ["A"], "2025-01-01", names=("전기밥솥",))
    assert choose_record([main], ["A"], "CN1", "", "전기밥솥(M1) 부분품", ON).record_no == "1"
    part = rec("2", ["A"], "2025-01-01", names=("전기밥솥부분품",))
    assert choose_record([part], ["A"], "CN1", "", "전기밥솥(M1)", ON).value is None


def test_color_mismatch_needs_precise():
    r = rec("1", ["A"], "2025-01-01", colors=("검정",))
    got = choose_record([r], ["A"], "CN1", "", "전기밥솥", ON, color="흰색", color_check=True)
    assert got.precise_needed and "색상" in got.note
