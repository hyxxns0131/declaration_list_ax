"""라벨 재질 ↔ 신고 재질 경고. 값은 안 바꾸고 문구만. 가상 값(약어표도 시험용)."""

from app.a3_judge.material.label_diff import label_terms_from, label_warning
from app.core.schema.document import ParsedDocument

ALIASES = {"PP": "폴리프로필렌"}
KNOWN = {"금속제(불소수지도장)", "폴리프로필렌", "스테인레스", "도자기제"}


def test_no_warning_when_same():
    assert (
        label_warning(
            ["금속제(불소수지도장)", "폴리프로필렌"], ["불소수지 코팅", "PP"], ALIASES, KNOWN
        )
        is None
    )


def test_warning_when_label_says_other_material():
    msg = label_warning(["금속제(불소수지도장)"], ["스테인레스"], ALIASES, KNOWN)
    assert msg and "스테인레스" in msg and "다름" in msg


def test_unknown_label_term_asks_check():
    msg = label_warning(["도자기제"], ["신소재X"], ALIASES, KNOWN)
    assert msg and "'신소재X'" in msg and "확인" in msg


def test_empty_inputs():
    assert label_warning([], ["PP"]) is None
    assert label_warning(["도자기제"], []) is None


def test_terms_from_docs_without_field():
    """서류 판독에 라벨 재질 칸이 아직 없으면 빈 목록 → 경고 없음."""
    d = ParsedDocument(doc_id="d1", shipper_id="T", folder_id="f", doc_type="LABEL")
    assert label_terms_from([d]) == []


def test_terms_from_docs_when_field_exists():
    """칸이 생기면(목록 또는 '·,' 구분 글자) 바로 읽는다 — 미리 맞춰 둔 시험."""
    from types import SimpleNamespace

    docs = [
        SimpleNamespace(doc_type="LABEL", label_materials=["스테인레스", "PP"]),
        SimpleNamespace(doc_type="LABEL", label_materials="PP, 실리콘"),
        SimpleNamespace(doc_type="CI", label_materials=["무시"]),
    ]
    assert label_terms_from(docs) == ["스테인레스", "PP", "실리콘"]  # type: ignore[arg-type]
