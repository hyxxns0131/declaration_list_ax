"""제조사 코드 규칙 검사 (RULES 11-7 '담당자가 코드를 바꿈'). 값은 바꾸지 않고 비고에만. 가상 값."""

from app.a3_judge.pipeline.context import JudgeContext
from app.a3_judge.pipeline.judge_row import judge_row
from app.a3_judge.rule_check.maker_rule import check_maker
from app.a4_settings.engine.service import merge_rules
from app.core.schema.document import ParsedDocument
from app.core.schema.fields import Field
from app.core.schema.history import C_MAKER, C_NOTE, HistoryRow

F1 = {"code": "CN1", "address": "NO.8 DEMO EAST ROAD, ALPHA TOWN", "status": "정상"}
F2 = {"code": "CN2", "address": "NO.25 SAMPLE WEST ROAD, BETA TOWN", "status": "정상"}
GONE = {"code": "CN9", "address": "NO.8 DEMO EAST ROAD, ALPHA TOWN", "status": "취소"}
DOC = "No.8 Demo East Road, Alpha Town"


def test_ok_when_registered_and_address_matches():
    assert check_maker("CN1", [F1, F2], DOC, set()) == []


def test_not_registered_code():
    got = check_maker("CN7", [F1, F2], DOC, set())
    assert got and got[0].startswith("제조사 코드 규칙 위배: CN7") and "CN1, CN2" in got[0]


def test_canceled_code_is_violation():
    assert check_maker("CN9", [F1, GONE], DOC, set())[0].startswith("제조사 코드 규칙 위배")


def test_address_differs_from_document():
    assert check_maker("CN2", [F1, F2], DOC, set()) == [
        "서류와 불일치 (제조사 주소): 등록 주소가 C/O 생산자 주소와 다름"
    ]


def test_prefer_past_skips_address_check():
    """A사: 같은 모델 과거 신고 코드면 주소 검사 생략(화주 요청 예외)."""
    assert check_maker("CN2", [F1, F2], DOC, {"CN2"}, prefer_past=True) == []
    assert check_maker("CN2", [F1, F2], DOC, {"CN2"}, prefer_past=False) != []


def test_no_check_when_lookup_failed_or_empty():
    assert check_maker("CN1", None, DOC, set()) == []  # 조회 실패 → 추측하지 않음
    assert check_maker("", [F1], DOC, set()) == []


# --- 판단 흐름에 연결 ---
def _ctx(lookup):
    co = ParsedDocument(
        doc_id="co1",
        shipper_id="T",
        folder_id="f",
        doc_type="CO",
        manufacturer_name="DEMO",
        manufacturer_address=DOC,
    )
    return JudgeContext(
        settings=merge_rules({"required_docs": ["CI"]}, {}, "T"),
        history=[],
        docs={"co1": co},
        factory_lookup=lookup,
    )


def _row(final_maker):
    r = HistoryRow(row_id="n1", shipper_id="T", model="M1", source_doc_ids=["co1"])
    r.cells[C_MAKER] = Field(final_value=final_maker)
    return r


def test_pipeline_marks_wrong_code_and_keeps_value():
    out = judge_row(_row("DEMO (CN7)"), _ctx(lambda name: ([F1, F2], "mock")))
    assert "⚠️ 제조사 규칙: 제조사 코드 규칙 위배: CN7" in out.text(C_NOTE)
    assert out.text(C_MAKER) == "DEMO (CN7)"


def test_pipeline_no_note_when_fine():
    out = judge_row(_row("DEMO (CN1)"), _ctx(lambda name: ([F1, F2], "mock")))
    assert "제조사 규칙" not in out.text(C_NOTE)
