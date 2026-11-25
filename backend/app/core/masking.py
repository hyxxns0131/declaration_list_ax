"""LLM으로 보내기 전에 화주명을 [화주]로 가린다 (AGENTS 7장 2번). 담당: KHS

가릴 이름 목록은 코드에 쓰지 않는다. 화주 설정(rules/shippers/*.json)의 `mask_names`나
호출하는 쪽이 넘긴 목록을 쓴다. 돌려받은 값에 화주명을 다시 채우지 않는다.
"""

import re

MASK = "[화주]"


def mask_text(text: str, names: list[str]) -> str:
    for name in sorted({n for n in names if n.strip()}, key=len, reverse=True):
        text = re.sub(re.escape(name), MASK, text, flags=re.IGNORECASE)
    return text


def mask_inputs(value: object, names: list[str]) -> object:
    """dict·list·str 안의 글자를 모두 가린다."""
    if isinstance(value, str):
        return mask_text(value, names)
    if isinstance(value, list):
        return [mask_inputs(v, names) for v in value]
    if isinstance(value, dict):
        return {k: mask_inputs(v, names) for k, v in value.items()}
    return value
