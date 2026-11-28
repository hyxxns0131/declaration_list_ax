"""모델 코드가 없는 행 → 영문 제품명이 같은 과거 이력 찾기. 순수 함수. 담당: LSY [재사용] A3-1 (기존 unmodeled.py)

부속품만 신고하거나 서류에 모델 코드가 없으면 history_lookup.find_past(모델 코드로 찾기)를 쓸 수 없다.
그때 영문 제품명으로 같은 제품의 이력을 찾는다. 보수적으로:
- 영문명은 띄어쓰기·구두점·대소문자만 무시하고 **글자가 같아야** 같은 제품('INNER POT' = 'Inner-Pot', ≠ 'INNER POT 2L')
- 완제품/부분품 구분이 같아야 한다
- 같은 영문명 이력이 여러 개인데 재질이 서로 다르면 고르지 않는다 → 담당자 확인
찾았어도 모델 코드로 찾은 것보다 약한 근거라 판단 결과는 '확인 필요'로 둔다(pipeline이 비고에 한 줄).
"""

import re

from app.core.schema.history import C_BL, C_MATERIAL, C_NAME_EN, HistoryRow

TAG_UNMODELED = "모델 없음"


def name_key(name_en: str) -> str:
    """비교용 영문명: 대문자, 영문·숫자만."""
    return re.sub(r"[^0-9A-Z]", "", (name_en or "").upper())


def _usable(row: HistoryRow) -> bool:
    cell = row.cells.get(C_MATERIAL)
    return bool(cell and cell.value) and cell.flag != "need_input"  # type: ignore[union-attr]


def find_by_name(
    history: list[HistoryRow], name_en: str, is_part: bool, exclude_row_id: str = ""
) -> tuple[HistoryRow | None, str]:
    """(찾은 이력 행 또는 None, 비고 문구). 영문명이 없으면 (None, '')."""
    key = name_key(name_en)
    if not key:
        return None, ""
    cands = [
        r
        for r in history
        if r.row_id != exclude_row_id
        and r.is_part == is_part
        and name_key(r.text(C_NAME_EN)) == key
        and _usable(r)
    ]
    if not cands:
        return None, f"모델 코드 없음 — 영문명 '{name_en}'과 같은 이력 없음, 직접 확인"
    materials = {r.text(C_MATERIAL) for r in cands}
    if len(materials) > 1:
        return None, (
            f"모델 코드 없음 — 영문명이 같은 이력 {len(cands)}건의 재질이 서로 달라 고르지 않음, 직접 확인"
        )
    approved = [r for r in cands if r.locked]
    past = (approved or cands)[-1]
    return (
        past,
        f"모델 코드 없어 영문명이 같은 이력({past.text(C_BL) or past.row_id})으로 채움 — 확인 필요",
    )
