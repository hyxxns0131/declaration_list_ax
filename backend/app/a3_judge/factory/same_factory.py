"""같은 공장인지: 코드가 같거나, 코드가 달라도 주소가 같으면 같은 공장(코드 갱신 추정). 순수 함수. 담당: LSY [재사용] A3-3

기존 precise.match_by (RULES 11-8). 주소 비교는 factory/address.py(표기 차이 정리 후 비교).
실적 고르기(record_pick)·규칙 검사(rule_check)가 이 함수를 쓴다.
"""

from app.a3_judge.factory.address import same_address


def same_factory(code_a: str, address_a: str, code_b: str, address_b: str) -> str | None:
    """'코드'(업소코드 같음) · '주소'(코드는 달라도 주소 같음 → 코드 갱신 추정) · None(다른 공장)."""
    if code_a and code_b and code_a.strip().upper() == code_b.strip().upper():
        return "코드"
    if address_a and address_b and same_address(address_a, address_b):
        return "주소"
    return None
