"""실적 고르기 경계 (RULES 11-8): 같은 공장 판정, 품명, 재질 포함, 유효기간 당일, 동점, 재질 구분. 가상 값."""

from datetime import date

from app.a3_judge.record_pick.eligibility import covers_materials, covers_product, factory_match
from app.a3_judge.record_pick.rank import choose_record
from app.core.schema.record import Record

ADDR = "NO.8 DEMO EAST ROAD, ALPHA TOWN"


def rec(
    no="R",
    mats=("금속제",),
    approved="2023-05-05",
    code="CN1",
    addr="",
    names=("전기밥솥",),
    spec="",
):
    return Record(
        record_no=no,
        factory_code=code,
        factory_address=addr,
        materials=list(mats),
        approved_on=approved,
        product_names=list(names),
        spec_class=spec,
    )


# --- 같은 공장 ---
def test_factory_match_code_case_insensitive():
    assert factory_match(rec(code="cn1"), "CN1", "") == "코드"


def test_factory_match_by_address_when_code_changed():
    """코드가 달라도 주소(정규화)가 같으면 같은 공장(코드 갱신 추정, RULES 11-7)."""
    assert (
        factory_match(rec(code="CN0", addr=ADDR), "CN1", "No 8 Demo East Road Alpha Town") == "주소"
    )
    assert factory_match(rec(code="CN0", addr=ADDR), "CN1", "NO.25 OTHER ROAD") is None


def test_address_match_chosen_but_needs_check():
    r = rec(code="CN0", addr=ADDR, approved="2028-01-01")
    got = choose_record([r], ["금속제"], "CN1", ADDR, "전기밥솥", date(2030, 1, 1))
    assert got.record_no == "R" and got.need_check and "코드 갱신 추정" in got.note


# --- 품명·재질 ---
def test_product_name_rules():
    assert covers_product("전기밥솥(M1)", rec())
    assert covers_product("전기밥솥 부분품", rec())  # 부속품 → 본품 실적 (한 방향)
    assert not covers_product("전기밥솥", rec(names=("전기밥솥 부분품",)))  # 반대는 안 됨
    assert covers_product("아무거나", rec(names=()))  # 실적 품명 기록이 없으면 거르지 않음


def test_materials_must_all_be_covered():
    assert covers_materials(["금속제"], rec(mats=("고무제", "금속제")))  # 실적이 더 많아도 됨
    assert not covers_materials(["금속제", "폴리프로필렌"], rec(mats=("금속제",)))
    assert not covers_materials([], rec())


# --- 유효기간: 승인일 + 5년, 그날까지 사용 가능 ---
def test_valid_on_expiry_day_expired_next_day():
    r = rec(approved="2023-05-05")
    assert choose_record([r], ["금속제"], "CN1", "", "전기밥솥", date(2028, 5, 5)).record_no == "R"
    late = choose_record([r], ["금속제"], "CN1", "", "전기밥솥", date(2028, 5, 6))
    assert late.value is None and "실적 만료 (R, 2028.05.05)" in late.note


# --- 동점이면 최신 승인일 ---
def test_tie_on_materials_latest_approval_wins():
    rs = [rec("OLD", approved="2025-01-01"), rec("NEW", approved="2026-01-01")]
    got = choose_record(rs, ["금속제"], "CN1", "", "전기밥솥", date(2026, 11, 26))
    assert got.record_no == "NEW" and got.value == "NEW (2026.01.01)"


# --- 재질 구분 (유리제·도자기제 등) ---
def test_spec_class_mismatch_skipped_then_precise():
    r = rec(mats=("유리제",), approved="2026-01-01", spec="가열조리용")
    got = choose_record(
        [r], ["유리제"], "CN1", "", "전기밥솥", date(2026, 11, 26), spec="가열조리용 이외"
    )
    assert (
        got.value is None and got.precise_needed and "재질 구분이 달라 건너뛴 실적: R" in got.note
    )


def test_spec_unknown_on_record_needs_check():
    r = rec(mats=("유리제",), approved="2026-01-01", spec="")
    got = choose_record(
        [r], ["유리제"], "CN1", "", "전기밥솥", date(2026, 11, 26), spec="가열조리용"
    )
    assert got.record_no == "R" and got.need_check and "같은 구분인지 확인 필요" in got.note


def test_no_material_or_factory_does_not_pick():
    assert (
        "재질이 정해지지 않아"
        in choose_record([rec()], [], "CN1", "", "전기밥솥", date(2026, 1, 1)).note
    )
    assert (
        "해외제조업소가 정해지지 않아"
        in choose_record([rec()], ["금속제"], "", "", "전기밥솥", date(2026, 1, 1)).note
    )


# --- 색상 비교 켠 화주(B사): 색이 맞는 실적은 고른다 (11/26 버그 재발 방지) ---
def test_color_check_on_picks_matching_color():
    from app.core.schema.record import SamplePart

    r = rec(approved="2026-01-01")
    r.sample_parts = [SamplePart(material="금속제", color="흰색")]
    got = choose_record(
        [r], ["금속제"], "CN1", "", "전기밥솥", date(2026, 11, 26), color="흰색", color_check=True
    )
    assert got.record_no == "R" and got.value == "R (2026.01.01)"
