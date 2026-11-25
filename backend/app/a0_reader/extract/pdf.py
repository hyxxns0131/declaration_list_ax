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
