"""모델 코드 추출, 제조사 "회사명 (코드)" 나누기, 품명. 순수 함수. 담당: LSY [재사용] A3-1 (기존 history.py)"""

import re

MAKER_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<code>[A-Za-z0-9\-]+)\)\s*$")
PAREN_RE = re.compile(r"\(([^()]+)\)\s*$")
ANY_PAREN_RE = re.compile(r"\([^()]*\)")
PART_SUFFIX = ("부분품", "부속품")


def split_maker(value: str) -> tuple[str, str]:
    """'회사명 (업소코드)' → (회사명, 코드). 코드가 없으면 (회사명, '')."""
    m = MAKER_RE.match((value or "").strip())
    return (m["name"].strip(), m["code"]) if m else ((value or "").strip(), "")


def join_maker(name: str, code: str) -> str:
    return f"{name} ({code})" if code else name


def same_model(a: str, b: str) -> bool:
    """모델 코드는 정확히 같아야 같은 모델(CR-0655F ≠ CR-0655FR, RULES 11-2). 대소문자·앞뒤 공백만 무시."""
    return bool(a) and a.strip().upper() == b.strip().upper()


def norm_company(name: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (name or "").lower())


def model_from_name(name: str) -> str:
    """'RICE COOKER(RC-100)' → 'RC-100'. 괄호가 없으면 ''."""
    m = PAREN_RE.search((name or "").strip())
    return m.group(1).strip().upper() if m else ""


def product_base(name_ko: str) -> str:
    """한글 제품명 → 품명: '전기밥솥(RC-100)' → '전기밥솥', '전기밥솥 부분품' → '전기밥솥 부분품'."""
    return re.sub(r"\s+", "", ANY_PAREN_RE.sub("", (name_ko or "").strip()))


def is_part_name(name_ko: str) -> bool:
    return product_base(name_ko).endswith(PART_SUFFIX)


def main_product(name_ko: str) -> str:
    """부분품 품명 → 본품 품명('전기밥솥부분품' → '전기밥솥'). 본품이면 그대로."""
    base = product_base(name_ko)
    for s in PART_SUFFIX:
        if base.endswith(s):
            return base[: -len(s)]
    return base
