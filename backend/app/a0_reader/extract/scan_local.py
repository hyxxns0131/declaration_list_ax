"""스캔본을 PC 안에서만 읽기: Windows 기본 OCR 글자로 서류 종류와 B/L 번호 후보를 찾는다. 담당: KHS [개선] A0-1

화주명을 가리지 못해 AI로 보낼 수 없는 스캔본도(HS 11/27 "왜 읽어서 못하는거야") 글자는 PC 안에서 읽을 수 있다.
밖으로 아무것도 보내지 않는다. 새 라이브러리 없음(redact.ocr_lines = Windows.Media.Ocr).
OCR 값은 틀릴 수 있으므로(글자 C↔G 등, 실제 B/L에는 영문 Z도 들어간다 — 글자를 숫자로 고치지 않는다) B/L 번호는 '확인 필요' 경고와 함께 넣고, 출처는 "ocr"로 남긴다.
"""

import re
from pathlib import Path

from app.a0_reader.extract.pdf import page_images
from app.a0_reader.extract.redact import ocr_lines, to_png

OCR_BL_WARNING = "B/L 번호: 스캔본 글자 읽기(PC 안 OCR) 값 - 원본과 같은지 확인 필요"

_LABEL = re.compile(r"\b(B\s*/\s*L|BILL\s+OF\s+LADING|WAYBILL|HB/?L|MB/?L)\s*(NO|NUMBER|#)", re.I)
_TOKEN = re.compile(r"\b[A-Z]{4}[A-Z0-9]{6,14}\b")
_CONTAINER = re.compile(r"^[A-Z]{3}U\d{7}$")  # 컨테이너 번호(ISO 6346)는 B/L이 아니다


def ocr_text_lines(path: Path) -> list[str]:
    """첫 쪽 OCR 줄 글자. Windows가 아니거나 실패하면 []."""
    imgs = page_images(path, max_pages=1)
    if not imgs:
        return []
    got = ocr_lines(to_png(imgs[0])) or []
    return [str(x.get("text") or "") for x in got]


def _candidates(text: str) -> list[str]:
    out = []
    for t in _TOKEN.findall(text.upper()):
        if _CONTAINER.match(t) or sum(ch.isdigit() for ch in t) < 6:
            continue
        if t not in out:
            out.append(t)
    return out


def bl_from_lines(lines: list[str]) -> str:
    """B/L 번호 후보 1개. 'B/L NO' 표시 바로 뒤(같은 줄·다음 두 줄)를 먼저, 없으면 첫 쪽 위에서 처음 나온 번호."""
    for i, ln in enumerate(lines):
        m = _LABEL.search(ln)
        if m:
            near = _candidates(" ".join([ln[m.end() :], *lines[i + 1 : i + 3]]))
            if near:
                return near[0]
    for ln in lines:
        got = _candidates(ln)
        if got:
            return got[0]
    return ""
