"""주소 정규화·유사도(addr_score). 순수 함수. 담당: LSY [재사용] A3-3 (기존 overseas_maker.addr_score)

- 지명·번지 낱말 겹침 비율. 띄어쓰기만 다른 표기('DONG CHENG' ↔ 'DONGCHENG')는 같은 부분으로 본다.
- 번지 숫자가 서로 다르면 크게 깎는다(6자리 우편번호는 번지로 보지 않음).
기준 점수(0.45, 2등과 0.1 차)는 설정값(core/config.py factory_addr_*).
"""

import re

ADDR_STOP = {
    "CHINA", "PR", "P", "R", "PEOPLES", "REPUBLIC", "OF", "PROVINCE", "CITY", "TOWN", "ROAD", "RD",
    "STREET", "ST", "NO", "THE", "AND", "DISTRICT", "COUNTY", "VILLAGE", "CN",
}  # fmt: skip


def _tokens(a: str) -> set[str]:
    toks = re.findall(r"[A-Z]+|\d+", (a or "").upper())
    return {t for t in toks if t.isdigit() or (len(t) > 1 and t not in ADDR_STOP)}


def _parts(a: str) -> list[str]:
    out = []
    for seg in re.split(r"[,;]", (a or "").upper()):
        s = re.sub(r"[^0-9A-Z]", "", seg)
        if s and s not in ("CHINA", "PRCHINA", "CN"):
            out.append(s)
    return out


def _nums(a: str) -> set[str]:
    return {t for t in re.findall(r"\d+", (a or "").upper()) if len(t) < 6}


def norm_address(a: str) -> str:
    return "".join(_parts(a))


def addr_score(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    score = len(ta & tb) / len(ta | tb)
    pa, pb = _parts(a), _parts(b)
    if pa and pb:
        hit = sum(
            1
            for x in pa
            if any(x == y or (len(x) >= 5 and x in y) or (len(y) >= 5 and y in x) for y in pb)
        )
        score = max(score, hit / max(len(pa), len(pb)))
    na, nb = _nums(a), _nums(b)
    if na and nb and not (na & nb):
        score *= 0.5
    return round(score, 3)


def same_address(a: str, b: str) -> bool:
    """코드가 달라도 주소(정규화)가 같으면 같은 공장(코드 갱신 추정, RULES 11-7)."""
    return bool(a and b) and norm_address(a) == norm_address(b)
