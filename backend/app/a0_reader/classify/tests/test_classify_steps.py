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
