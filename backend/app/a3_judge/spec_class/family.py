"""재질이 4종(유리제·도자기제·법랑·옹기류)에 해당하는지. 순수 함수. 담당: LSY [재사용] A3-1

근거: 「기구 및 용기·포장의 기준 및 규격」 총칙 3.자 — 4종만 깊이·용량·가열조리용 여부로 규격이 갈림
(RULES 11-5). 최신본 확인 필요(확인 필요 7).
재질 칸은 재질 코드명으로 적혀 있다고 본다(약어는 material/codes.py가 먼저 코드명으로 바꿈).
"""

FAMILIES = ("유리제", "도자기제", "법랑", "옹기류")


def families_in(materials: list[str]) -> list[str]:
    """재질 목록에 든 4종(FAMILIES 순서)."""
    return [f for f in FAMILIES if any(f in m for m in materials)]
