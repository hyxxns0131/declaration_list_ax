"""재질 판단 순서 ① 이력 → ② 이전 수입신고서 → ③ 시험성적서 → ④ 현품사진·라벨 (RULES 11-4). 가상 값."""

from app.a3_judge.material.resolve import resolve_material
from app.core.schema.document import ParsedDocument
from app.core.schema.fields import Field
from app.core.schema.history import C_APPROVAL, C_BL, C_MATERIAL, HistoryRow
from app.core.schema.record import Record, SamplePart

ALIASES = {"PP": "폴리프로필렌"}


def past(mat="금속제", approved="DEMO-OK1"):
    cells = {C_MATERIAL: Field(ai_value=mat), C_BL: Field(ai_value="BL-DEMO-001")}
    if approved:
        cells[C_APPROVAL] = Field(ai_value=approved)
    return HistoryRow(row_id="h1", shipper_id="A", model="DEMO-M01", cells=cells)


PRODUCT = {"materials": ["금속제", "PP"], "receipt_no": "DEMO-R1", "receipt_date": "2025-01-01"}
REC = Record(
    record_no="DEMO-101",
    products=["DEMO-M01"],
    approved_on="2028-01-01",
    sample_parts=[SamplePart(material="금속제"), SamplePart(material="고무제")],
)
PHOTO = ParsedDocument(doc_id="p1", shipper_id="A", folder_id="f", doc_type="LABEL")


def test_history_first():
    r = resolve_material("DEMO-M01", past(), ALIASES)
    assert r.value == "금속제" and r.flag == "ok"
    assert r.evidence[0].source == "HISTORY" and "[승인]" in r.evidence[0].note


def test_import_decl_when_no_history_and_alias():
    r = resolve_material("DEMO-M01", None, ALIASES, product=PRODUCT)
    assert r.value == "금속제, 폴리프로필렌" and r.evidence[0].source == "IMPORT_DECL"


def test_test_report_third():
    r = resolve_material("DEMO-M01", None, ALIASES, records=[REC])
    assert r.value == "고무제, 금속제" and r.evidence[0].source == "TEST_REPORT"


def test_sources_disagree_need_check_with_candidates():
    """다른 근거가 다른 재질을 말하면 첫 근거 값 + 후보 + '확인 필요'(DESIGN 1장 7번)."""
    r = resolve_material("DEMO-M01", past(), ALIASES, product=PRODUCT)
    assert r.value == "금속제" and r.flag == "need_check"
    assert r.candidates == ["금속제", "금속제, 폴리프로필렌"]


def test_photo_alone_never_decides():
    """사진·라벨만 있으면 값을 비우고 '확인 필요' (AGENTS 7-9)."""
    r = resolve_material("DEMO-NEW", None, ALIASES, docs=[PHOTO])
    assert r.value is None and r.flag == "need_check" and r.evidence[0].source == "LABEL"


def test_nothing_need_input_text():
    r = resolve_material("DEMO-NEW", None, ALIASES)
    assert r.value == "현품사진·한글표시 자료 추가 필요 (DEMO-NEW)" and r.flag == "need_input"


def test_order_setting():
    """화주 설정 material_source_order로 순서를 바꾼다(RULES 11-11)."""
    r = resolve_material(
        "DEMO-M01", past(), ALIASES, product=PRODUCT, order=["IMPORT_DECL", "HISTORY"]
    )
    assert r.value == "금속제, 폴리프로필렌" and r.evidence[0].source == "IMPORT_DECL"


def test_unknown_official_name_need_check():
    r = resolve_material("DEMO-M01", past(mat="이상한재질"), ALIASES, known={"금속제"})
    assert r.value == "이상한재질" and r.flag == "need_check" and "코드명" in r.memo
