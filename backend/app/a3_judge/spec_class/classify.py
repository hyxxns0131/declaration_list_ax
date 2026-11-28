"""재질 구분 — 유리제·도자기제·법랑·옹기류만. 순수 함수. 담당: LSY [재사용·개선] A3-1 (기존 spec_class.py)

근거: 「기구 및 용기·포장의 기준 및 규격」 총칙 3.자 — 최신본 확인 필요(확인 필요 7).
자동 입력은 재질 코드명에 표시된 구분만(RULES 11-5):
- 유리제: 코드명에 '(가열조리용)'이 있으면 '가열조리용', 없으면 '가열조리용 이외'
- 도자기제·옹기류·법랑, 깊이·용량은 담당자가 입력 → 빈 칸이면 '칸 입력 필요'
담당자가 적은 칸은 바꾸지 않는다. 읽어서 모자란 입력만 알려 주고, 구분표 설정이 있으면 구분 이름을 근거로 남긴다.
"""

from pydantic import BaseModel

from app.a3_judge.spec_class.family import FAMILIES, families_in
from app.a3_judge.spec_class.parse import HEAT_WORDS, missing_inputs, parse_spec
from app.a3_judge.spec_class.tables import lookup

__all__ = ["FAMILIES", "SpecJudgement", "auto_spec", "families_in", "judge_spec"]


def auto_spec(materials: list[str]) -> tuple[str | None, str]:
    """(자동 값 또는 None, 메모). 4종이 없으면 (None, '')."""
    fams = families_in(materials)
    if not fams:
        return None, ""
    if fams == ["유리제"]:
        glass = [m for m in materials if "유리제" in m]
        heat = any(any(w in m for w in HEAT_WORDS) for m in glass)
        return (
            "가열조리용" if heat else "가열조리용 이외"
        ), "재질 코드명 표시로 정함 — 깊이·용량은 담당자 입력"
    return None, f"{'·'.join(fams)}: 깊이(2.5cm)·용량·가열조리용 여부 입력 필요"


class SpecJudgement(BaseModel):
    families: list[str] = []
    ai_value: str | None = None  # 칸이 비었을 때만 넣을 값
    note: str = ""  # 비고 '⚠️ 재질 구분:' 한 줄(없으면 빈 글자)
    evidence: str = ""  # 근거 메모
    missing: list[str] = []
    label: str | None = None  # 구분표 설정이 있을 때 구분 이름


def judge_spec(materials: list[str], cell_text: str, table: dict | None = None) -> SpecJudgement:
    """재질·칸 글자 → 판단. cell_text = 지금 칸 값(담당자 확정 값 우선)."""
    fams = families_in(materials)
    out = SpecJudgement(families=fams)
    if not fams:
        return out
    text = (cell_text or "").strip()
    if not text:
        value, memo = auto_spec(materials)
        out.ai_value, out.evidence = value, memo
        if value is None:
            out.note = memo
        return out
    spec = parse_spec(text)
    out.missing = missing_inputs(spec)
    notes: list[str] = []
    if out.missing:
        notes.append(f"{'·'.join(fams)}: {', '.join(out.missing)} 입력 필요")
    if len(fams) == 1:
        out.label, memo = lookup(fams[0], spec, table)
        out.evidence = f"칸 입력값 읽음 — {memo}"
    else:
        out.evidence = f"칸 입력값 읽음 — {'·'.join(fams)}가 함께라 구분표 자동 적용 안 함"
    out.note = " / ".join(notes)
    return out
