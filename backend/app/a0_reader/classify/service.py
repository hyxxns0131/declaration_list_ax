"""서류 종류 판별: 파일 이름 → 내용 순서. 담당: KHS [재사용] A0-2 (기존 CompanyRules.invoice_name·bl_name)

못 알아보면 None(호출한 쪽이 "서류 종류 확인 필요"로 둔다).
"""

import re

from app.core.schema.document import DocType

# 파일 이름 조각(소문자·영숫자/한글만) → 서류 종류. 앞에 있는 것부터 본다.
NAME_TOKENS: list[tuple[DocType, tuple[str, ...]]] = [
    ("INTAKE_LIST", ("입고", "intake")),
    ("CO", ("co", "origin", "원산지", "certificateoforigin")),
    ("BL", ("bl", "billoflading", "선하증권")),
    ("PL", ("pl", "packing", "packinglist", "패킹", "포장명세서")),
    ("CI", ("ci", "invoice", "commercialinvoice", "인보이스")),
    ("IMPORT_DECL", ("수입신고서", "importdeclaration")),
    ("TEST_REPORT", ("시험성적서", "검사성적서", "testreport")),
    ("LABEL", ("라벨", "한글표시", "label")),
]

# 서류 본문 첫머리 제목 → 서류 종류
TITLE_WORDS: list[tuple[DocType, str]] = [
    ("CO", "certificateoforigin"),
    ("BL", "billoflading"),
    ("PL", "packinglist"),
    ("CI", "commercialinvoice"),
    ("CI", "invoice"),
]

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


def norm(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def _tokens(stem: str) -> list[str]:
    return [norm(t) for t in re.split(r"[^0-9A-Za-z가-힣]+", stem) if t] + [norm(stem)]


def classify_by_name(filename: str) -> DocType | None:
    stem, _, ext = filename.rpartition(".")
    stem = stem or filename
    if f".{ext.lower()}" in IMAGE_EXT:
        return "LABEL" if any(k in norm(stem) for k in ("라벨", "label", "한글표시")) else "PHOTO"
    # 'B/L', 'B-L', 'C/O' 같은 표기를 한 조각으로
    stem = re.sub(r"(?<![A-Za-z])([BbCc])\s*[/\-_.]\s*([LlOo])(?![A-Za-z])", r"\1\2", stem)
    toks = _tokens(stem)
    joined = norm(stem)
    for doc_type, keys in NAME_TOKENS:
        for k in keys:
            # 짧은 약어(ci, pl, bl, co)는 조각이 정확히 같을 때만, 긴 말은 포함되면
            if (len(k) <= 2 and k in toks) or (len(k) > 2 and k in joined):
                return doc_type
    return None


def classify_by_content(head_text: str) -> DocType | None:
    """서류 첫머리 글자(제목 줄 몇 개)로 판별."""
    h = norm(head_text)
    for doc_type, word in TITLE_WORDS:
        if word in h:
            return doc_type
    return None


def classify(filename: str, head_text: str = "") -> DocType | None:
    return classify_by_name(filename) or classify_by_content(head_text)
