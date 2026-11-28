"""재질 구분 칸 읽기·정리. 순수 함수. 담당: LSY [개선] A3-1

칸 적는 법(RULES 11-5): `깊이 3cm, 용량 1.2L` / `깊이 2cm` / `평판(액체 못 채움)` / `용량 800mL, 가열조리용`.
담당자가 순서·단위를 다르게 적어도(`용량 1200ml 깊이 30mm`) 같은 값으로 읽고, 같은 형식으로 다시 쓴다.
→ 실적 재질 구분과 비교할 때 글자 차이로 '다름'이 되지 않게(record_pick/rank.py).
"""

import re

from pydantic import BaseModel

HEAT_WORDS = ("가열조리용", "직화", "오븐", "전자레인지", "열탕")  # RULES 11-5: 가열조리용으로 봄
NOT_HEAT_WORDS = ("가열조리용 이외", "가열조리용이외", "비가열", "가열조리용 아님")
FLAT_WORDS = ("평판", "액체 못 채움", "액체를 채울 수 없")

_NUM = r"(\d+(?:[.,]\d+)?)"
DEPTH_RE = re.compile(r"깊이\s*[:：]?\s*" + _NUM + r"\s*(mm|cm|㎜|㎝)?", re.I)
VOLUME_RE = re.compile(r"용량\s*[:：]?\s*" + _NUM + r"\s*(ml|mℓ|㎖|l|ℓ|리터)?", re.I)


class SpecInput(BaseModel):
    depth_cm: float | None = None
    volume_ml: float | None = None
    flat: bool | None = None
    heat: bool | None = None  # None = 적지 않음

    def empty(self) -> bool:
        return (
            self.depth_cm is None and self.volume_ml is None and not self.flat and self.heat is None
        )


def _num(text: str) -> float:
    return float(text.replace(",", "."))


def parse_spec(text: str) -> SpecInput:
    t = (text or "").strip()
    out = SpecInput()
    if not t:
        return out
    if m := DEPTH_RE.search(t):
        v = _num(m.group(1))
        out.depth_cm = v / 10 if (m.group(2) or "").lower() in ("mm", "㎜") else v
    if m := VOLUME_RE.search(t):
        v = _num(m.group(1))
        unit = (m.group(2) or "ml").lower()
        out.volume_ml = v * 1000 if unit in ("l", "ℓ", "리터") else v
    if any(w in t for w in FLAT_WORDS):
        out.flat = True
    if any(w in t for w in NOT_HEAT_WORDS):
        out.heat = False
    elif any(w in t for w in HEAT_WORDS):
        out.heat = True
    return out


def _fmt(v: float) -> str:
    return f"{v:g}"


def format_spec(s: SpecInput) -> str:
    """RULES 11-5 형식으로: 깊이 → 용량 → 평판 → 가열조리용."""
    parts: list[str] = []
    if s.flat:
        parts.append("평판(액체 못 채움)")
    elif s.depth_cm is not None:
        parts.append(f"깊이 {_fmt(s.depth_cm)}cm")
    if s.volume_ml is not None:
        v = s.volume_ml
        parts.append(f"용량 {_fmt(v / 1000)}L" if v >= 1000 else f"용량 {_fmt(v)}mL")
    if s.heat is True:
        parts.append("가열조리용")
    elif s.heat is False:
        parts.append("가열조리용 이외")
    return ", ".join(parts)


def canonical(text: str) -> str:
    """비교용 형식. 읽을 수 있는 게 없으면 원래 글자(공백 정리)."""
    s = parse_spec(text)
    return format_spec(s) if not s.empty() else " ".join((text or "").split())


def same_spec(a: str, b: str) -> bool:
    return canonical(a) == canonical(b)


def missing_inputs(s: SpecInput) -> list[str]:
    """4종 행에 더 적어야 할 것. 평판이면 깊이·용량 없이 끝.
    가열조리용 여부는 적지 않으면 '가열조리용 이외'로 보는 기존 적는 법(RULES 11-5 예시)에 따라 묻지 않는다."""
    if s.flat:
        return []
    out = []
    if s.depth_cm is None:
        out.append("깊이(또는 평판)")
    if s.volume_ml is None:
        out.append("용량")
    return out
