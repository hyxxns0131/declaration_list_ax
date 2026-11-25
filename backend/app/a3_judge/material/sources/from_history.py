"""재질 근거 ① 이력: 같은 모델의 과거 검역이력 재질. 담당: LSY [재사용] A3-1"""

from app.core.schema.fields import Evidence
from app.core.schema.history import C_BL, C_MATERIAL, HistoryRow


def from_history(past: HistoryRow | None) -> tuple[str, Evidence] | None:
    if not past or not past.text(C_MATERIAL):
        return None
    state = "승인" if past.locked else "미승인"
    ev = Evidence(
        source="HISTORY",
        ref=past.row_id,
        note=f"이력 {past.text(C_BL)} 같은 모델({past.model}) 재질 [{state}]",
    )
    return past.text(C_MATERIAL), ev
