"""과거 검역이력에서 같은 모델(완제품/부분품 구분)의 최근 행 찾기. 순수 함수. 담당: LSY [재사용] A3-1

승인된 행(승인번호 있음)을 먼저, 그다음 최근 행. 재질 칸이 '자료 추가 필요'인 행은 쓰지 않는다.
"""

from app.a3_judge.history_lookup.model_key import same_model
from app.core.schema.history import C_MATERIAL, HistoryRow


def _usable(row: HistoryRow) -> bool:
    cell = row.cells.get(C_MATERIAL)
    return bool(cell and cell.value) and cell.flag != "need_input"  # type: ignore[union-attr]


def find_past(
    history: list[HistoryRow], model: str, is_part: bool, exclude_row_id: str = ""
) -> HistoryRow | None:
    """history는 표 순서(오래된 것 → 최근). 같은 모델·같은 완제품/부분품 구분의 가장 알맞은 행."""
    cands = [
        r
        for r in history
        if r.row_id != exclude_row_id
        and r.is_part == is_part
        and same_model(r.model, model)
        and _usable(r)
    ]
    if not cands:
        return None
    approved = [r for r in cands if r.locked]
    return (approved or cands)[-1]
