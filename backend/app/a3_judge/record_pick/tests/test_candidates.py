"""실적 후보 표: 검사별 ✓/✗·빠진 재질·제외 이유·기준일 (근거 패널용, 11/26 [개선]). 가상 값."""

from datetime import date

from app.a3_judge.record_pick.rank import choose_record
from app.core.schema.record import Record

ON = date(2030, 1, 10)


def rec(no, mats, approved, code="CN1", names=("전기밥솥",), spec=""):
    return Record(
        record_no=no,
        factory_code=code,
        materials=list(mats),
        approved_on=approved,
        product_names=list(names),
        spec_class=spec,
    )


def by_no(choice):
    return {c["record_no"]: c for c in choice.candidates}


def test_selected_and_excluded_with_reasons():
    rs = [
        rec("OK", ["고무제", "금속제"], "2028-01-01"),
        rec("OLD", ["고무제", "금속제"], "2020-01-01"),  # 만료(2025-01-01)
        rec("FAC", ["고무제", "금속제"], "2028-01-01", code="CN9"),
        rec("MAT", ["금속제"], "2028-01-01"),
    ]
    got = choose_record(rs, ["고무제", "금속제"], "CN1", "", "전기밥솥(M1)", ON)
    c = by_no(got)
    assert got.record_no == "OK" and got.basis_date == "2030-01-10"
    assert c["OK"]["status"] == "선택" and all(c["OK"]["checks"].values())
    assert c["OLD"]["status"] == "제외" and not c["OLD"]["checks"]["기간"]
    assert "만료" in c["OLD"]["reason"] and "기준일 2030.01.10" in c["OLD"]["reason"]
    assert c["FAC"]["status"] == "제외" and "다른 공장" in c["FAC"]["reason"]
    assert c["MAT"]["missing_materials"] == ["고무제"] and "고무제 없음" in c["MAT"]["reason"]


def test_less_inclusive_valid_record_stays_candidate():
    rs = [rec("BIG", ["고무제", "금속제"], "2028-01-01"), rec("SMALL", ["금속제"], "2029-01-01")]
    c = by_no(choose_record(rs, ["금속제"], "CN1", "", "전기밥솥", ON))
    assert c["BIG"]["status"] == "선택"
    assert c["SMALL"]["status"] == "후보" and c["SMALL"]["reason"] == ""


def test_no_record_all_excluded_with_reason():
    rs = [rec("X", ["금속제"], "2028-01-01", names=("그릇",))]
    got = choose_record(rs, ["금속제"], "CN1", "", "전기밥솥", ON)
    c = by_no(got)
    assert got.value is None and got.precise_needed
    assert c["X"]["status"] == "제외" and not c["X"]["checks"]["품명"]


def test_spec_mismatch_marked():
    rs = [rec("S", ["유리제"], "2028-01-01", spec="가열조리용")]
    c = by_no(choose_record(rs, ["유리제"], "CN1", "", "전기밥솥", ON, spec="가열조리용 이외"))
    assert c["S"]["status"] == "제외" and not c["S"]["checks"]["재질 구분"]


def test_old_keys_kept_for_screen():
    """PM 화면(JudgeEvidence)이 쓰는 칸은 그대로 있어야 한다."""
    c = choose_record([rec("A", ["금속제"], "2028-01-01")], ["금속제"], "CN1", "", "전기밥솥", ON)
    keys = {"record_no", "value", "materials", "approved_on", "expires_on", "expired", "fits"}
    assert keys <= set(c.candidates[0])
