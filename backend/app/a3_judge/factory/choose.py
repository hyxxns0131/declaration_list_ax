"""해외제조업소 코드 고르기. 순수 함수(공장 목록은 호출하는 쪽이 넘긴다). 담당: LSY [재사용] A3-3

선택 순서(RULES 11-7, 기존 도구 2026-11-13):
1. 회사명이 같은 식약처 정상 등록 공장
2. C/O 생산자 주소 ↔ 등록 주소 유사도 ≥ 0.45 이고 2등과 ≥ 0.1 차이
3. 같은 모델의 이전 신고 공장 코드가 등록 공장 중 하나로 정해질 때(메모 "확인 필요")
4. 모두 실패 → 코드 비움 + "확인 필요: 해외제조업소 코드 수기 선택 필요", 후보(코드: 주소)
prefer_past_factory_code(화주 요청 예외)면 3을 2보다 먼저 본다.
"""

from pydantic import BaseModel
from pydantic import Field as PField

from app.a3_judge.factory.address import addr_score

MANUAL = "확인 필요: 해외제조업소 코드 수기 선택 필요"


class FactoryChoice(BaseModel):
    code: str = ""
    name: str = ""
    address: str = ""
    how: str = ""  # address · past · single · manual · none
    notes: list[str] = PField(default_factory=list)
    candidates: list[dict] = PField(default_factory=list)  # [{code, address, score, status}]
    need_check: bool = False


def choose_factory(
    company: str,
    doc_address: str,
    factories: list[dict],
    past_codes: set[str],
    prefer_past: bool = False,
    min_score: float = 0.45,
    min_gap: float = 0.10,
) -> FactoryChoice:
    ok = [f for f in factories if f.get("status") == "정상"]
    scored = sorted(
        ({**f, "score": addr_score(doc_address, f.get("address", ""))} for f in ok),
        key=lambda f: -f["score"],
    )
    out = FactoryChoice(name=company, candidates=scored)
    if not factories:
        out.notes.append(
            f"'{company}'로 식약처에 등록된 해외제조업소가 없음 → 등록 여부·회사명 표기 확인"
        )
        out.how, out.need_check = "none", True
        return out
    if not ok:
        bad = "; ".join(f"{f['code']} {f.get('status')}" for f in factories)
        out.notes.append(f"정상 등록 공장 없음({bad})")
        out.how, out.need_check = "none", True
        return out

    def by_past() -> FactoryChoice | None:
        hit = {f["code"] for f in ok} & {c for c in past_codes if c}
        if len(hit) != 1:
            return None
        code = next(iter(hit))
        f = next(x for x in ok if x["code"] == code)
        out.code, out.address, out.how = code, f.get("address", ""), "past"
        score = addr_score(doc_address, f.get("address", "")) if doc_address else 0.0
        if score >= min_score:  # 이전 신고 공장이 서류 주소와도 맞음 → 확인 필요 아님
            out.notes.append(f"이전 신고 공장 {code} = 서류 주소 공장 (유사도 {score:.2f})")
            return out
        out.notes.append(
            f"같은 모델 이전 신고 공장 {code} 사용 → 서류 주소로 확인되지 않았으니 확인 필요"
        )
        out.need_check = True
        return out

    def by_address() -> FactoryChoice | None:
        if not doc_address:
            out.notes.append("선적서류에서 제조사 주소를 찾지 못함")
            return None
        best = scored[0]
        second = scored[1]["score"] if len(scored) > 1 else 0.0
        if best["score"] >= min_score and best["score"] - second >= min_gap:
            out.code, out.address, out.how = best["code"], best.get("address", ""), "address"
            past = {c for c in past_codes if c}
            if past and best["code"] not in past:
                out.notes.append(
                    f"서류 주소 기준 공장 {best['code']}가 같은 모델 이전 신고 공장"
                    f"({', '.join(sorted(past))})과 다름 → 실적은 업소코드 기준이라 확인 필요"
                )
                out.need_check = True
            else:
                out.notes.append(f"C/O 생산자 주소와 등록 주소 유사도 {best['score']:.2f}")
            return out
        out.notes.append(
            f"서류 주소가 등록 공장 주소와 뚜렷하게 맞지 않음 (가장 비슷한 {best['code']}, {best['score']:.2f})"
        )
        return None

    steps = (by_past, by_address) if prefer_past else (by_address, by_past)
    for step in steps:
        got = step()
        if got:
            if prefer_past and got.how == "past" and got.need_check:
                got.notes[-1] = (
                    f"화주 요청 예외: 과거 신고 공장 코드 우선({got.code}) — 서류 주소와 다름"
                )
            return got
    if len(ok) == 1 and not doc_address and not past_codes:
        f = ok[0]
        out.code, out.address, out.how = f["code"], f.get("address", ""), "single"
        out.notes.append(f"회사명으로 등록된 정상 공장이 1곳뿐({f['code']}) → 주소 확인 필요")
        out.need_check = True
        return out
    out.how, out.need_check = "manual", True
    out.notes.append(MANUAL)
    return out
