"""재질 칸 규칙 검사 — 값은 바꾸지 않고 문제만 돌려준다. 순수 함수. 담당: LSY [재사용] A3-1 (기존 rule_check.py)

RULES 11-4: 식약처 재질 코드명으로, 여러 개면 가나다 순, 쉼표 구분. 프로그램 값은 이미 정리돼 있으므로
주로 담당자가 직접 고친 값(final_value)을 검사한다(RULES 11-9 '프로그램은 표시만').
"""

from app.a3_judge.material.codes import material_list


def check_material(text: str, known: set[str] | frozenset[str] | None = None) -> list[str]:
    """문제 목록(없으면 빈 목록). known이 비면 공식 코드명 확인은 건너뛴다(Supabase 연결 없음)."""
    names = material_list(text)
    if not names:
        return []
    out: list[str] = []
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        out.append(f"같은 재질이 두 번: {', '.join(dup)}")
    uniq = list(dict.fromkeys(names))
    if uniq != sorted(uniq):
        out.append(f"가나다 순 아님 → {', '.join(sorted(uniq))}")
    if known:
        unknown = [n for n in uniq if n not in known]
        if unknown:
            out.append(f"재질 코드명 아님: {', '.join(unknown)}")
    return out
