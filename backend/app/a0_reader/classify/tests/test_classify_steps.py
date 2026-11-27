"""서류 종류 판별 순서: 파일 이름 → 본문 키워드 → OpenAI(가짜 응답) → 모르면 None. (검역 리스트 탭 1단계)"""

from app.a0_reader.classify import service
from app.a0_reader.classify.service import classify, classify_shipping_name, classify_with_ai


def test_name_then_content():
    assert classify("CI_BLTEST003.xlsx") == "CI"
    assert classify("문서1.pdf", "PACKING LIST Invoice No.") == "PL"
    assert classify("문서1.pdf", "") is None


def test_scanned_image_named_bl_is_shipping():
    assert classify_shipping_name("BL 스캔.jpg") == "BL"
    assert classify_shipping_name("현품사진.jpg") is None


def test_ai_fallback_and_unknown(monkeypatch):
    class _Out:
        def __init__(self, t: str) -> None:
            self.doc_type = t

    import app.core.llm as llm

    monkeypatch.setattr(llm, "call_structured", lambda *a, **k: _Out("BL"))
    assert classify_with_ai("문서1.pdf", "OCEAN VESSEL PORT OF LOADING", []) == "BL"
    monkeypatch.setattr(llm, "call_structured", lambda *a, **k: _Out("UNKNOWN"))
    assert classify_with_ai("문서1.pdf", "", []) is None
    monkeypatch.setattr(llm, "call_structured", lambda *a, **k: None)  # AI 꺼짐
    assert classify_with_ai("문서1.pdf", "", []) is None
    assert service.SHIPPING_TYPES[:3] == ("CI", "PL", "BL")


def test_import_decl_not_bl():
    """수입신고필증은 이름에 B/L 번호가 있어도 IMPORT_DECL (HS 11/26)"""
    from app.a0_reader.classify.service import classify

    assert classify("A사_BL TEST123_수입신고필증.pdf") == "IMPORT_DECL"
    assert classify("신고필증 BL-TEST-004.pdf") == "IMPORT_DECL"
    assert classify("문서.pdf", "수입신고필증 신고번호 12345") == "IMPORT_DECL"
    assert classify("BL TEST123.pdf") == "BL"


def test_fta_draft_is_certificate_of_origin():
    """FTA 원산지증명서 초안을 B/L로 잘못 보지 않는다(HS 11/27)"""
    from app.a0_reader.classify.service import classify

    assert classify("ABC123---FTA draft.pdf") == "CO"


def test_unknown_document_is_other_not_bl(tmp_path):
    """종류를 모르는 서류는 '기타'로 둔다(B/L·인보이스로 짐작하지 않음)"""
    from openpyxl import Workbook

    from app.a0_reader.extract.service import extract_file

    p = tmp_path / "memo.xlsx"
    wb = Workbook()
    wb.active.append(["메모", "아무 내용"])
    wb.save(p)
    doc = extract_file(p, "memo.xlsx", "A", "f")
    assert doc.doc_type == "OTHER" and "서류 종류 확인 필요" in doc.warnings
