"""한글 제품명에 모델명 붙이기(product_name_with_model). 순수 함수. 담당: KHS [신규] (로직 점검 반영 11/25)

켜면 '전기밥솥(RC-100)'처럼 모델 코드를 괄호로 붙이고, 끄면 붙어 있던 '(모델)'을 뗀다.
프로그램 값(ai_value)만 바꾸고 담당자가 고친 값(final_value)은 건드리지 않는다(AGENTS 0-5).
판단(이력·수입신고서에서 제품명 채우기)이 끝난 뒤에 부른다.
"""

import re

from app.core.schema.history import C_NAME_KO, HistoryRow
from app.core.schema.shipper import ShipperSettings


def style_name(name: str, model: str, with_model: bool) -> str:
    """켜면 '(모델)'이 없을 때만 끝에 붙이고, 끄면 이름 안의 '(모델)'을 모두 뗀다."""
    name, model = name.strip(), model.strip()
    if not name or not model:
        return name
    tag = re.compile(r"\s*\(" + re.escape(model) + r"\)", re.I)
    if with_model:
        return name if tag.search(name) else f"{name}({model})"
    return re.sub(r"\s{2,}", " ", tag.sub("", name)).strip()


def apply_name_style(rows: list[HistoryRow], settings: ShipperSettings) -> None:
    with_model = bool(getattr(settings, "product_name_with_model", False))
    for r in rows:
        cell = r.cells.get(C_NAME_KO)
        if not cell or not isinstance(cell.ai_value, str) or not cell.ai_value:
            continue
        cell.ai_value = style_name(cell.ai_value, r.model, with_model)
