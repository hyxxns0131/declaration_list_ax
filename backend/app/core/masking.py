"""LLM으로 보내기 전에 화주명을 [화주]로 가린다 (AGENTS 7장 2번). 담당: KHS

가릴 이름 목록은 코드에 쓰지 않는다. 화주 설정(rules/shippers/*.json)의 `mask_names`나
호출하는 쪽이 넘긴 목록을 쓴다. 돌려받은 값에 화주명을 다시 채우지 않는다.
"""

import re

MASK = "[화주]"


SHORT = 5  # 이 글자 수 이하 이름(약칭)은 낱말 전체가 같을 때만 가린다 — 다른 낱말 속 글자까지 가리지 않게


def mask_text(text: str, names: list[str]) -> str:
    for name in sorted({n.strip() for n in names if n.strip()}, key=len, reverse=True):
        pat = re.escape(name)
        if len(name) <= SHORT:
            pat = rf"(?<![0-9A-Za-z가-힣]){pat}(?![0-9A-Za-z가-힣])"
        text = re.sub(pat, MASK, text, flags=re.IGNORECASE)
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


# ── 실제 화주명 목록: PC 전용 파일에서만 읽는다(임시 안전 조치 11/26, HS 결정 전) ─────────────
# 위치: DATA_DIR/mask_names.json (data/는 .gitignore). rules/shippers/*.json 등 커밋되는 파일에는 두지 않는다(공개 저장소).
# 형식: {"A": ["A기업", "A기업 영문 표기"], "B": ["B기업"]}  — 화주 id → 서류에 적히는 이름들(영문·약칭 포함)
#       배열만 두면 모든 화주 공통 목록으로 본다.
MASK_FILE = "mask_names.json"


def mask_file():  # -> Path (config를 늦게 불러 순환 import를 피한다)
    from app.core.config import get_settings

    return get_settings().data_path / MASK_FILE


def load_names() -> dict[str, list[str]]:
    """{화주 id: [이름]}. 파일이 없거나 형식이 틀리면 빈 dict(→ AI로 보내지 않는다)."""
    import json

    path = mask_file()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(raw, list):
        raw = {"*": raw}
    if not isinstance(raw, dict):
        return {}
    return {
        str(k): [str(n).strip() for n in v if str(n).strip()]
        for k, v in raw.items()
        if isinstance(v, list)
    }


def all_names() -> list[str]:
    """모든 화주의 이름(한 서류에 다른 화주 이름이 섞여도 가리도록 전부 쓴다)."""
    return sorted({n for names in load_names().values() for n in names}, key=len, reverse=True)
