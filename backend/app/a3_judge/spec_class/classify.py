"""재질 구분 — 유리제·도자기제·법랑·옹기류만. 순수 함수. 담당: LSY [재사용] A3-1 (기존 spec_class.py)

근거: 「기구 및 용기·포장의 기준 및 규격」 총칙 3.자 — 최신본 확인 필요(확인 필요 7).
자동 입력은 재질 코드명에 표시된 구분만(RULES 11-5):
- 유리제: 코드명에 '(가열조리용)'이 있으면 '가열조리용', 없으면 '가열조리용 이외'
- 도자기제·옹기류·법랑, 깊이·용량은 담당자가 입력 → 빈 칸이면 '칸 입력 필요'
"""

FAMILIES = ("유리제", "도자기제", "법랑", "옹기류")
HEAT_WORDS = ("가열조리용", "직화", "오븐", "전자레인지", "열탕")


def families_in(materials: list[str]) -> list[str]:
    return [f for f in FAMILIES if any(f in m for m in materials)]


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
