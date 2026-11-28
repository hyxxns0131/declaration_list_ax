"""쓸 수 있는 실적인지: 같은 공장, 같은 품명, 재질 모두 포함. 순수 함수. 담당: LSY [재사용] A3-2

기존 precise.match_by·covers·covers_product (RULES 11-8)
- 같은 공장: 업소코드가 같거나, 코드가 달라도 주소가 같으면 같은 공장(코드 갱신 추정)
- 같은 품명: 부속품만 신고할 때는 본품 실적을 쓸 수 있다(한 방향). 실적 품명이 비어 있으면 품명으로 거르지 않는다.
- 재질: 실적 재질이 제품 재질을 모두 포함해야 한다(실적 재질이 더 많은 것은 문제없음).
"""

from app.a3_judge.factory.same_factory import same_factory
from app.a3_judge.record_pick.spare_rule import same_product
from app.core.schema.record import Record


def factory_match(rec: Record, code: str, address: str) -> str | None:
    """'코드' · '주소' · None (factory/same_factory.py)"""
    return same_factory(code, address, rec.factory_code, rec.factory_address)


def covers_product(name_ko: str, rec: Record, spare_to_main: bool = True) -> bool:
    """실적 품명이 이 제품을 덮는지(부속품 → 본품 실적 한 방향, record_pick/spare_rule.py)."""
    return same_product(name_ko, rec.product_names, spare_to_main)


def covers_materials(materials: list[str], rec: Record) -> bool:
    return bool(materials) and set(materials) <= set(rec.materials)
