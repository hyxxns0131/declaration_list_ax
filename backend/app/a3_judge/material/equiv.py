"""라벨 표기 ↔ 재질 코드명이 같은 재질인지. 순수 함수. 담당: LSY [재사용·개선] A3-1 (기존 material_equiv.py)

예(AGENTS 4-5): 라벨 '불소수지' / '불소수지 코팅' = 코드명 '금속제(불소수지도장)'.
쓰는 곳: 이전 신고 재질과 라벨이 다를 때 경고(label_diff.py), 담당자가 고른 재질 확인.

판정은 세 가지 — 'same'(같음) · 'different'(다름) · 'unknown'(모름 → 확인 필요). 애매하면 unknown(보수적).
1) 약어표(Supabase material_aliases)로 바꿔서 코드명과 같으면 same
2) 띄어쓰기·표기 차이(스테인리스/스테인레스, 코팅/도장)를 없애고 같으면 same
3) 코드명 '바탕(세부)'에서 라벨이 세부의 핵심어를 담으면 same ('불소수지 코팅' ↔ '금속제(불소수지도장)')
4) 라벨이 바탕에서 '제'만 뺀 말이면 same ('유리' ↔ '유리제'). 단 코드명에 세부가 있으면 unknown
   ('금속' ↔ '금속제(불소수지도장)': 코팅이 있는지 라벨만으로 모름)
5) 라벨이 다른 공식 코드명(또는 약어)으로 읽히면 different, 아무것도 아니면 unknown
"""

import re
from typing import Literal

Verdict = Literal["same", "different", "unknown"]

# 표기만 다른 말(앞 → 뒤로 맞춤). 재질 판정 기준이 아니라 글자 맞추기용
SPELLING = (
    ("스테인리스", "스테인레스"),
    ("STAINLESSSTEEL", "스테인레스"),
    ("STAINLESS", "스테인레스"),
    ("코팅", "도장"),
    ("코트", "도장"),
)
COATING_WORDS = ("도장", "가공")  # 세부의 핵심어를 뽑을 때 떼는 말
_PAREN_RE = re.compile(r"^(?P<base>[^(（]+)[(（](?P<detail>[^)）]*)[)）]\s*$")


def squash(text: str) -> str:
    """비교용: 띄어쓰기 없애고 영문은 대문자, 표기 차이를 맞춘다."""
    s = re.sub(r"\s+", "", text or "").upper()
    for a, b in SPELLING:
        s = s.replace(a, b)
    return s


def split_code_name(name: str) -> tuple[str, str]:
    """'금속제(불소수지도장)' → ('금속제', '불소수지도장'). 괄호가 없으면 (이름, '')."""
    m = _PAREN_RE.match((name or "").strip())
    if not m:
        return (name or "").strip(), ""
    return m.group("base").strip(), m.group("detail").strip()


def _core(detail: str) -> str:
    s = squash(detail)
    for w in COATING_WORDS:
        s = s.replace(w, "")
    return s


def compare(
    label: str,
    code_name: str,
    aliases: dict[str, str] | None = None,
    known: set[str] | frozenset[str] | None = None,
) -> Verdict:
    """라벨 표기 1개 ↔ 재질 코드명 1개."""
    if not (label or "").strip() or not (code_name or "").strip():
        return "unknown"
    lower = {k.lower(): v for k, v in (aliases or {}).items()}
    mapped = lower.get(label.strip().lower(), label.strip())
    target = squash(code_name)
    if squash(mapped) == target or squash(label) == target:
        return "same"
    base, detail = split_code_name(code_name)
    lab = squash(mapped)
    if detail:
        core = _core(detail)
        if core and core in lab:
            return "same"
    if lab and squash(base).removesuffix("제") == lab.removesuffix("제"):
        return "unknown" if detail else "same"
    names = set(known or ()) | set(lower.values())
    if any(squash(n) == lab for n in names):
        return "different"
    return "unknown"


def compare_sets(
    labels: list[str],
    code_names: list[str],
    aliases: dict[str, str] | None = None,
    known: set[str] | frozenset[str] | None = None,
) -> dict[str, Verdict]:
    """라벨 표기마다: 코드명 중 하나와 same이면 same, 모두 different면 different, 아니면 unknown."""
    out: dict[str, Verdict] = {}
    for lab in labels:
        verdicts = [compare(lab, c, aliases, known) for c in code_names]
        if "same" in verdicts:
            out[lab] = "same"
        elif verdicts and all(v == "different" for v in verdicts):
            out[lab] = "different"
        else:
            out[lab] = "unknown"
    return out
