"""규칙 검사 — 담당자가 고친 재질·실적이 규칙에 맞는지, 값은 바꾸지 않고 비고에만 (RULES 11-9). 가상 값."""

from datetime import date

from app.a3_judge.pipeline.context import JudgeContext
from app.a3_judge.pipeline.judge_row import judge_row
from app.a3_judge.rule_check.material_rule import check_material
from app.a3_judge.rule_check.record_rule import check_record
from app.a4_settings.engine.service import merge_rules
from app.core.schema.fields import Field
from app.core.schema.history import C_MAKER, C_MATERIAL, C_NAME_KO, C_NOTE, C_RECORD, HistoryRow
from app.core.schema.record import Record

ON = date(2026, 11, 26)
REC = Record(
    record_no="202600000101",
    factory_code="CN1",
    materials=["금속제", "폴리프로필렌"],
    approved_on="2026-01-01",
    product_names=["전기밥솥"],
)
OLD = Record(
    record_no="201900000001", factory_code="CN1", materials=["금속제"], approved_on="2019-01-01"
)


# --- 재질 ---
def test_material_ok():
    assert check_material("금속제, 폴리프로필렌", {"금속제", "폴리프로필렌"}) == []


def test_material_order_dup_unknown():
    got = check_material("폴리프로필렌, 금속제, 금속제, 이상한재질", {"금속제", "폴리프로필렌"})
    assert "같은 재질이 두 번: 금속제" in got
    assert any(x.startswith("가나다 순 아님") for x in got)
    assert "재질 코드명 아님: 이상한재질" in got


def test_material_need_input_and_no_known_skip():
    assert check_material("현품사진·한글표시 자료 추가 필요 (M1)", {"금속제"}) == []
    assert check_material("이상한재질", None) == []  # 코드명 목록을 못 읽으면 건너뜀


# --- 실적 ---
def test_record_ok():
    got = check_record(
        "202600000101 (2026.01.01)", ["금속제"], "CN1", "", "전기밥솥(M1)", [REC], ON
    )
    assert got == []


def test_record_problems():
    got = check_record(
        "202600000101 (2026.01.01)", ["고무제", "금속제"], "CN9", "", "그릇", [REC], ON
    )
    assert "다른 공장의 실적(CN1)" in got
    assert "실적에 없는 재질: 고무제" in got
    assert "다른 품명의 실적" in got


def test_record_expired_and_unknown():
    assert check_record("201900000001 (2019.01.01)", ["금속제"], "CN1", "", "", [OLD], ON) == [
        "만료된 실적(2024.01.01)"
    ]
    assert "등록된 실적이 아님" in check_record("209900000001", [], "CN1", "", "", [REC], ON)[0]
    assert check_record("", [], "", "", "", [REC], ON) == []


# --- 판단 흐름에 연결: 사람이 고친 값만 검사, 값은 그대로 ---
def _row(final_mat=None, final_rec=None):
    r = HistoryRow(row_id="n1", shipper_id="T", model="M1")
    r.cells[C_MAKER] = Field(final_value="가상공장 (CN1)")
    r.cells[C_NAME_KO] = Field(ai_value="전기밥솥(M1)")
    r.cells[C_MATERIAL] = Field(final_value=final_mat)
    r.cells[C_RECORD] = Field(final_value=final_rec)
    return r


def _ctx():
    return JudgeContext(
        settings=merge_rules({"required_docs": ["CI"]}, {}, "T"),
        history=[],
        records=[REC],
        known_materials=frozenset({"고무제", "금속제", "폴리프로필렌"}),
        today=ON,
    )


def test_pipeline_marks_human_edits_without_changing_them():
    out = judge_row(
        _row(final_mat="폴리프로필렌, 고무제, 금속제", final_rec="202600000101 (2026.01.01)"),
        _ctx(),
    )
    note = out.text(C_NOTE)
    assert "⚠️ 재질 규칙: 가나다 순 아님" in note
    assert "⚠️ 실적 규칙: 실적에 없는 재질: 고무제" in note
    assert out.text(C_MATERIAL) == "폴리프로필렌, 고무제, 금속제"  # 사람 값 그대로
    assert out.text(C_RECORD) == "202600000101 (2026.01.01)"


def test_pipeline_no_rule_note_when_fine():
    out = judge_row(_row(final_mat="금속제", final_rec="202600000101 (2026.01.01)"), _ctx())
    assert "규칙" not in out.text(C_NOTE)
