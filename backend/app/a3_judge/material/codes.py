"""재질 표기 정리: 약어 → 재질 코드명(Supabase material_aliases), 가나다 정렬. 담당: LSY [재사용] A3-1

정리 규칙(RULES 11-4): 식약처 재질 코드명으로, 여러 개면 가나다 순, 쉼표 구분.
약어를 못 바꾸면 그대로 두고 uncertain=True("확인 필요").
"""

from functools import lru_cache

from app.core.errors import AppError
from app.core.storage import public_db

SEPARATORS = ",，/·"


def split_materials(text: str) -> list[str]:
    """괄호 밖의 쉼표·/·가운뎃점에서만 나눈다. 괄호 안은 재질 코드명의 일부라 그대로 둔다
    ('합성수지제(PP, PE), 금속제' → ['합성수지제(PP, PE)', '금속제'], 11/25 결정)."""
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text or "":
        if ch in "(（":
            depth += 1
        elif ch in ")）" and depth:
            depth -= 1
        if ch in SEPARATORS and depth == 0:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return [t for t in out if t]


def normalize(
    text: str, aliases: dict[str, str], known: set[str] | None = None
) -> tuple[str, bool]:
    """(정리한 재질, 확인 필요 여부). 순수 함수."""
    out: list[str] = []
    uncertain = False
    lower = {k.lower(): v for k, v in aliases.items()}
    for t in split_materials(text):
        name = lower.get(t.lower(), t)
        if known is not None and name not in known:
            uncertain = True
        if name not in out:
            out.append(name)
    return ", ".join(sorted(out)), uncertain


@lru_cache
def load_aliases() -> dict[str, str]:
    """Supabase 약어표. 못 읽으면 빈 표(약어 변환 없이 그대로 둔다)."""
    try:
        rows = public_db.select_public("material_aliases", {"select": "alias,name"})
    except (AppError, OSError, ValueError):
        return {}
    except Exception:  # 네트워크 오류 등 — 판단은 계속한다
        return {}
    return {r["alias"]: r["name"] for r in rows if r.get("alias") and r.get("name")}


@lru_cache
def load_known_names() -> frozenset[str]:
    """Supabase 재질 코드명 목록(공식 이름 확인용). 못 읽으면 빈 집합(확인을 건너뛴다)."""
    try:
        rows = public_db.select_public("material_codes", {"select": "name"})
    except Exception:  # 네트워크·키 없음 — 판단은 계속한다
        return frozenset()
    return frozenset(r["name"] for r in rows if r.get("name"))


def material_list(text: str) -> list[str]:
    """재질 칸 값 → 재질 이름 목록(정렬 전). '자료 추가 필요' 같은 표시는 빈 목록."""
    if not text or "자료 추가 필요" in text:
        return []
    return split_materials(text)
