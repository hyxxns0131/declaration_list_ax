"""부속품만 신고 → 본품 실적 사용(한 방향). 순수 함수. 담당: LSY [재사용] A3-2

RULES 11-8: 부속품만 신고할 때는 본품 실적을 쓸 수 있다. 반대(부속품 실적으로 본품)는 안 된다 [미팅].
품명은 괄호·띄어쓰기를 뺀 '품명'으로 비교한다('전기밥솥 부분품(RC-100)' → '전기밥솥부분품').
"""

from app.a3_judge.history_lookup.model_key import main_product, product_base


def same_product(name_ko: str, record_names: list[str], spare_to_main: bool = True) -> bool:
    """실적 품명 목록이 이 제품을 덮는지. 실적 품명 기록이 없으면 거르지 않는다(True)."""
    if not record_names:
        return True
    base = product_base(name_ko)
    names = {product_base(n) for n in record_names}
    if base in names:
        return True
    main = main_product(name_ko)
    return spare_to_main and main != base and main in names
