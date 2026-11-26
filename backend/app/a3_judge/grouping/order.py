"""신고건 안 행 순서·신고건 순서 = 화주 설정 sort_by. 순수 함수. 담당: LSY [신규] (로직 점검 반영 11/25)

sort_by는 정렬 기준 목록(앞이 우선). 비우면 서류(표) 순서 그대로.
- model: 모델 코드 순
- name_ko: 한글 제품명 순
- bl: B/L 번호 순
- material: 재질 순
같은 값이면 원래 순서를 지킨다(안정 정렬). 신고건은 정렬된 첫 행 순서대로 만들어지므로 신고건 순서도 따라 바뀐다.
"""

from collections.abc import Callable

from app.core.schema.history import C_BL, C_MATERIAL, C_NAME_KO, HistoryRow

SORT_KEYS: dict[str, Callable[[HistoryRow], str]] = {
    "model": lambda r: r.model.upper(),
    "name_ko": lambda r: r.text(C_NAME_KO),
    "bl": lambda r: r.text(C_BL).upper(),
    "material": lambda r: r.text(C_MATERIAL),
}


def sort_rows(rows: list[HistoryRow], sort_by: list[str] | None) -> list[HistoryRow]:
    keys = [SORT_KEYS[k] for k in (sort_by or []) if k in SORT_KEYS]
    if not keys:
        return list(rows)
    # 빈 값은 뒤로 (값이 있는 행이 먼저)
    return sorted(rows, key=lambda r: tuple((f(r) == "", f(r)) for f in keys))
