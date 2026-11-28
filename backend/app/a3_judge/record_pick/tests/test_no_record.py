"""실적 없음 문구 (RULES 11-2·11-8). 비고·화면이 그대로 보여 주므로 글자를 고정한다."""

from app.a3_judge.record_pick import no_record


def test_no_valid_record():
    assert no_record.no_valid_record("CN1") == (
        "이 공장(CN1)에서 이 재질을 모두 포함하는 유효한 정밀검사 실적 없음 → 정밀검사 대상"
    )
    assert "이 공장(주소 기준)" in no_record.no_valid_record("")


def test_expired():
    assert no_record.expired("202300000101", "2028.04.25") == (
        "실적 만료 (202300000101, 2028.04.25) → 정밀검사 신청 대상"
    )


def test_spec_and_color():
    assert no_record.spec_mismatch([]) == "같은 재질 구분의 유효한 실적 없음 → 정밀검사 대상"
    assert no_record.spec_mismatch(["재질 구분이 달라 건너뛴 실적: R"]).startswith(
        "재질 구분이 달라 건너뛴 실적: R → "
    )
    assert (
        no_record.color_mismatch("R", "흰색")
        == "R실적과 현품(흰색)의 색상이 달라 추가 정밀검사 필요"
    )
