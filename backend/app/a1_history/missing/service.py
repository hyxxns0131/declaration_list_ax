"""빠진 서류 칸에 "○○ 자료 추가 필요". 빈 칸에만 쓴다. 순수 함수. 담당: KHS [재사용] A1-2

RULES 11-2 (기존 need_input.py 문구 그대로):
- 인보이스·PL 없음 → 한글 제품명 칸 "인보이스·PL 자료 추가 필요"
- B/L 없음 → 선적일 칸 "B/L 자료 추가 필요"
- 신규 모델 재질 자료 없음 → 재질 칸 (A3 재질 판단이 쓴다)
"""

from app.core.schema.fields import Evidence
from app.core.schema.history import C_NAME_KO, HistoryRow

C_SHIP_DATE = "선적일"
MARK_CI_PL = "인보이스·PL 자료 추가 필요"
MARK_BL = "B/L 자료 추가 필요"
MARK_COLUMNS = {C_NAME_KO: MARK_CI_PL, C_SHIP_DATE: MARK_BL}

DOC_LABELS = {
    "CI": "인보이스",
    "PL": "포장명세서",
    "BL": "B/L",
    "CO": "원산지증명서",
    "INTAKE_LIST": "입고리스트",
    "PHOTO": "현품사진",
    "LABEL": "한글표시",
}


def missing_docs(present: set[str], required: list[str]) -> list[str]:
    return [d for d in required if d not in present]


def is_mark(value: object) -> bool:
    return isinstance(value, str) and value.endswith("자료 추가 필요")


def _mark(row: HistoryRow, col: str, text: str, missing: list[str]) -> None:
    cell = row.cells.get(col)
    if cell and cell.value not in (None, "") and not is_mark(cell.value):
        return  # 빈 칸에만
    row.set_ai(
        col,
        text,
        [Evidence(source="RULE", ref="required_docs", note=f"빠진 서류: {', '.join(missing)}")],
        flag="need_input",
    )


def apply_missing(row: HistoryRow, present: set[str], required: list[str]) -> None:
    miss = missing_docs(present, required)
    if {"CI", "PL"} & set(miss):
        _mark(row, C_NAME_KO, MARK_CI_PL, miss)
    if "BL" in miss:
        _mark(row, C_SHIP_DATE, MARK_BL, miss)
