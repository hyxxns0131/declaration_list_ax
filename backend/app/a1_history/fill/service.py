"""서류 등록 탭(YHS) 정보로 완성된 검역 리스트의 제조사·재질·재질 구분·실적을 채운다. 담당: KHS [신규]
(검역 리스트 탭 4단계, 제안서 1번 둘째 줄, HS 요청 11/26)

판단 로직은 새로 만들지 않는다:
- 제품·실적 데이터는 YHS a2_registry(products.products_for, records.list_records)에서 읽기만.
- 재질·실적·제조사 고르기는 LSY a3_judge/pipeline(judge_rows)을 그대로 부른다(rows_service.rejudge).
  a3가 만료 실적은 고르지 않고, 후보가 여럿·근거 없음이면 비우고 need_check + 비고 '⚠️ 실적: …'.
- final_value는 건드리지 않는다(a3 set_ai 규칙). 등록 정보가 하나도 없는 모델은 비고 '⚠️ 등록 정보: 서류 등록 필요'.
도는 때: 행 생성 직후(업로드 흐름이 이미 판단을 부름), [새로고침], POST /history/fill, on_registry_changed.
"""

from app.a1_history.rows import service as rows_service
from app.a2_registry.products.service import products_for
from app.a2_registry.records.service import list_records
from app.core.schema.history import C_RECORD, HistoryRow
from app.core.storage import work_db

TAG = "등록 정보"
NEED = "서류 등록 필요 (수입신고서·검사성적서를 서류 등록 탭에 올리세요)"


def _registered_models(shipper_id: str) -> set[str]:
    models = {str(p.get("model", "")).upper() for p in products_for(shipper_id)}
    for rec in list_records(shipper_id):
        models |= {m.upper() for m in getattr(rec, "products", [])}
    return {m for m in models if m}


def mark_unregistered(rows: list[HistoryRow], registered: set[str]) -> list[HistoryRow]:
    """등록 정보가 없는 모델의 행에 '서류 등록 필요'(빈 칸만 표시, 값은 만들지 않음). 바뀐 행 목록."""
    changed = []
    for r in rows:
        if r.locked:
            continue
        missing = bool(r.model) and r.model.upper() not in registered and not r.text(C_RECORD)
        before = r.text("비고")
        r.set_note(TAG, NEED if missing else None)
        if r.text("비고") != before:
            r.refresh_status()
            changed.append(r)
    return changed


def fill(shipper_id: str, row_ids: list[str] | None = None) -> dict:
    judged = rows_service.rejudge(
        shipper_id, row_ids
    )  # a3 판단(제조사·재질·재질 구분·실적), final_value 유지
    rows = work_db.list_rows(shipper_id)
    if row_ids is not None:
        rows = [r for r in rows if r.row_id in set(row_ids)]
    changed = mark_unregistered(rows, _registered_models(shipper_id))
    work_db.save_rows(changed)
    return {"judged": judged, "need_registry": sum(1 for r in rows if NEED in r.text("비고"))}


def on_registry_changed(
    shipper_id: str, product_models: list[str] | None = None, record_nos: list[str] | None = None
) -> dict:
    """서류 등록 탭에서 제품·실적이 등록·수정된 뒤 YHS가 부른다(변경 요청). 영향받는 행만 다시 채운다."""
    models = {m.upper() for m in product_models or []}
    nos = set(record_nos or [])
    for no in nos:  # 실적에 묶인 모델도 영향 범위
        for rec in list_records(shipper_id):
            if rec.record_no == no:
                models |= {m.upper() for m in rec.products}
    hit = [
        r.row_id
        for r in work_db.list_rows(shipper_id)
        if not r.locked
        and (r.model.upper() in models or any(no and no in r.text(C_RECORD) for no in nos))
    ]
    if not hit:
        return {"judged": 0, "need_registry": 0, "rows": []}
    out = fill(shipper_id, hit)
    return {**out, "rows": hit}
