"""제품별 재질·해외제조업소(수입신고서 등록). 담당: YHS [개선] A2-1 (기존 material_json.py, declarations.py)

공개 함수(A3 재질 판단 ②가 부른다): latest_for_model, products_for, save_product
저장 형태(dict): model, product_ko, product_en, materials[이름], material_codes[코드],
  maker_code, maker_name, maker_address, receipt_no, receipt_date, accepted_date, inspection_type, source
"""

from app.core.storage import work_db_more as store


def product_id(shipper_id: str, model: str, receipt_no: str) -> str:
    return f"{shipper_id}:{model.upper()}:{receipt_no}"


def save_product(shipper_id: str, data: dict) -> None:
    model = (data.get("model") or "").upper()
    store.save_product(
        product_id(shipper_id, model, data.get("receipt_no") or ""), shipper_id, model, data
    )


def products_for(shipper_id: str, model: str | None = None) -> list[dict]:
    return store.list_products(shipper_id, model)


def latest_for_model(shipper_id: str, model: str) -> dict | None:
    """같은 모델의 가장 최근 수입신고서(접수일 기준)."""
    if not model:
        return None
    rows = products_for(shipper_id, model)
    if not rows:
        return None
    return max(rows, key=lambda d: (d.get("receipt_date") or "", d.get("receipt_no") or ""))
