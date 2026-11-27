"""제조사(해외제조업소 코드) 칸 규칙 검사 — 값은 바꾸지 않고 문제만 돌려준다. 순수 함수. 담당: LSY [재사용] A3-3

RULES 11-7 '담당자가 코드를 바꿈':
- 그 회사명의 식약처 정상 등록 공장 코드가 아니면 "제조사 코드 규칙 위배"
- 등록 주소가 서류(C/O 생산자) 주소와 다르면 "서류와 불일치 (제조사 주소)"
- A사(prefer_past_factory_code)는 같은 모델의 과거 신고 코드면 주소 검사를 생략한다(화주 요청 예외)
공장 목록을 못 읽었으면(조회 실패) 검사하지 않는다(추측 금지).
"""

from app.a3_judge.factory.address import addr_score


def check_maker(
    code: str,
    factories: list[dict] | None,
    doc_address: str,
    past_codes: set[str],
    prefer_past: bool = False,
    min_score: float = 0.45,
) -> list[str]:
    if not code or factories is None:
        return []
    code_u = code.upper()
    ok = [f for f in factories if f.get("status") == "정상"]
    hit = next((f for f in ok if str(f.get("code", "")).upper() == code_u), None)
    if hit is None:
        known = ", ".join(f["code"] for f in ok) or "정상 등록 공장 없음"
        return [f"제조사 코드 규칙 위배: {code}는 이 회사의 정상 등록 공장이 아님 (등록: {known})"]
    if prefer_past and code_u in {c.upper() for c in past_codes if c}:
        return []  # 화주 요청 예외: 과거 신고 코드면 주소 검사 생략
    if doc_address and addr_score(doc_address, hit.get("address", "")) < min_score:
        return ["서류와 불일치 (제조사 주소): 등록 주소가 C/O 생산자 주소와 다름"]
    return []
