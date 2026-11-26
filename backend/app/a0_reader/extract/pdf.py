"""글자 PDF → 칸 격자. 표는 표대로, 나머지 줄은 '라벨: 값' 두 칸으로. 담당: KHS [개선] A0-1

스캔 PDF(글자 없음)는 빈 격자를 돌려준다 → service가 AI 판독으로 넘긴다.
"""

import re
from pathlib import Path

from app.a0_reader.extract.excel import Grid


def _line_to_cells(line: str) -> list[object]:
    if ":" in line:
        label, _, value = line.partition(":")
        return [label.strip() + ":", value.strip()]
    return [c for c in re.split(r"\s{2,}", line.strip()) if c]


def read_pdf(path: Path) -> tuple[Grid, str]:
    """(격자, 전체 글자)"""
    import pdfplumber

    grid: Grid = []
    texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            texts.append(text)
            for line in text.splitlines():
                if line.strip():
                    grid.append(_line_to_cells(line))
            for table in page.extract_tables():
                grid.append([])
                grid.extend([list(r) for r in table])
    return grid, "\n".join(texts)


def page_images(
    path: Path, max_pages: int = 3, resolution: int = 150, redact: list[str] | None = None
) -> list[bytes]:
    """스캔 PDF·표가 깨진 PDF → 페이지 PNG(OpenAI 멀티모달 판독용). 앞 몇 쪽만(비용).
    redact: 가릴 이름(화주명). 글자가 있는 PDF는 그 낱말 위치를 검은 칸으로 덮는다(core/masking과 같은 목적).
    글자가 없는 스캔본은 위치를 알 수 없어 가리지 못한다 → 호출한 쪽이 알고 보낸다."""
    from io import BytesIO

    import pdfplumber

    names = [n for n in (redact or []) if n.strip()]
    out: list[bytes] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            im = page.to_image(resolution=resolution)
            for name in names:
                for hit in page.search(re.escape(name), regex=True, case=False):
                    box = (hit["x0"] - 1, hit["top"] - 1, hit["x1"] + 1, hit["bottom"] + 1)
                    im.draw_rect(box, fill=(0, 0, 0), stroke=(0, 0, 0))
            buf = BytesIO()
            im.annotated.save(buf, format="PNG")
            out.append(buf.getvalue())
    return out


def has_text(path: Path) -> bool:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return any((p.extract_text() or "").strip() for p in pdf.pages[:3])
