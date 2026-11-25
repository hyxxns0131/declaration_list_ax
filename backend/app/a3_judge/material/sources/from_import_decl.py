"""재질 근거 ② 이전 수입신고서 (A2 products 데이터). 순수 함수. 담당: LSY [재사용] A3-1

신고한 재질(재질 코드명)을 쓴다. 코드명 확인은 resolve.py의 normalize가 한다.
"""

from app.core.schema.fields import Evidence


def from_import_decl(product: dict | None) -> tuple[str, Evidence] | None:
    if not product or not product.get("materials"):
        return None
    mats = ", ".join(product["materials"])
    kind = product.get("inspection_type") or "-"
    ev = Evidence(
        source="IMPORT_DECL",
        ref=product.get("receipt_no") or "",
        note=f"이전 수입신고서 {product.get('receipt_no')} ({product.get('receipt_date') or '날짜 미상'}, "
        f"{kind}검사) 같은 모델 재질",
    )
    return mats, ev
