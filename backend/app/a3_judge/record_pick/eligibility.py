"""쓸 수 있는 실적인지: 같은 공장, 같은 품명, 재질 모두 포함. 순수 함수. 담당: LSY [재사용] A3-2

기존 precise.match_by·covers·covers_product (RULES 11-8)
- 같은 공장: 업소코드가 같거나, 코드가 달라도 주소가 같으면 같은 공장(코드 갱신 추정)
- 같은 품명: 부속품만 신고할 때는 본품 실적을 쓸 수 있다(한 방향). 실적 품명이 비어 있으면 품명으로 거르지 않는다.
- 재질: 실적 재질이 제품 재질을 모두 포함해야 한다(실적 재질이 더 많은 것은 문제없음).
"""

from app.a3_judge.factory.address import same_address
from app.a3_judge.history_lookup.model_key import main_product, product_base
from app.core.schema.record import Record


def factory_match(rec: Record, code: str, address: str) -> str | None:
    """'코드' · '주소' · None"""
    if code and rec.factory_code and code.upper() == rec.factory_code.upper():
        return "코드"
    if address and rec.factory_address and same_address(address, rec.factory_address):
        return "주소"
    return None


def covers_product(name_ko: str, rec: Record, spare_to_main: bool = True) -> bool:
    if not rec.product_names:
        return True
    base = product_base(name_ko)
    names = {product_base(n) for n in rec.product_names}
    if base in names:
        return True
    return spare_to_main and main_product(name_ko) != base and main_product(name_ko) in names


def covers_materials(materials: list[str], rec: Record) -> bool:
    return bool(materials) and set(materials) <= set(rec.materials)
