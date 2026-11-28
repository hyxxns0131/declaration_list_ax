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


def test_color_mismatch_marked_excluded():
    """color_check면 검체 색이 다른 실적은 후보 목록에서 '제외' + 이유(색상 다름). 가상 값."""
    from datetime import date

    from app.a3_judge.record_pick.rank import choose_record
    from app.core.schema.record import Record, SamplePart

    def rec(no: str, approved: str, color: str) -> Record:
        return Record(
            record_no=no,
            factory_code="CN900000201",
            materials=["도자기제"],
            approved_on=approved,
            sample_parts=[SamplePart(material="도자기제", part="그릇 본체", color=color)],
            products=["BWL-W15"],
        )

    out = choose_record(
        [rec("R-WHITE", "2025-05-24", "WHITE"), rec("R-BLUE", "2025-07-13", "BLUE")],
        ["도자기제"],
        "CN900000201",
        "",
        "도자기 그릇(BWL-W15)",
        date(2026, 11, 27),
        color="WHITE",
        color_check=True,
    )
    by = {c["record_no"]: c for c in out.candidates}
    assert out.record_no == "R-WHITE"
    assert by["R-BLUE"]["status"] == "제외" and "색상 다름" in by["R-BLUE"]["reason"]
    assert by["R-BLUE"]["checks"]["색상"] is False and by["R-WHITE"]["checks"]["색상"] is True


def test_color_words_english_korean():
    """시험성적서 'WHITE(흰색)' ↔ 선적서류 'WHITE' 또는 '흰색'은 같은 색. 가상 값."""
    from app.a3_judge.record_pick.rank import _color_ok, color_words
    from app.core.schema.record import Record, SamplePart

    assert color_words("WHITE(흰색)") == {"WHITE", "흰색"}
    r = Record(
        record_no="R-1",
        sample_parts=[SamplePart(material="도자기제", part="접시", color="WHITE(흰색)")],
    )
    assert _color_ok(r, "WHITE") is True
    assert _color_ok(r, "white") is True
    assert _color_ok(r, "흰색") is True
    assert _color_ok(r, "BLUE") is False


def test_spec_compare_ignores_order_and_units():
    """실적 재질 구분 '깊이 3cm, 용량 1.2L' = 행 '용량 1200ml, 깊이 30mm' → 같은 구분. 가상 값."""
    from datetime import date

    from app.a3_judge.record_pick.rank import choose_record
    from app.core.schema.record import Record

    r = Record(
        record_no="R-1",
        factory_code="CN900000201",
        materials=["도자기제"],
        approved_on="2025-05-24",
        spec_class="깊이 3cm, 용량 1.2L",
        products=["BWL-W15"],
    )
    out = choose_record(
        [r],
        ["도자기제"],
        "CN900000201",
        "",
        "도자기 그릇(BWL-W15)",
        date(2026, 11, 27),
        spec="용량 1200ml, 깊이 30mm",
    )
    assert out.record_no == "R-1" and out.candidates[0]["checks"]["재질 구분"] is True
