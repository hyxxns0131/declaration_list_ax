"""신고건 나누기 공개 함수. 담당: LSY [개선] A3-4

- declarations_for: 행 → 신고건(순수 계산)
- recompute: 화주의 전체 행으로 신고건을 다시 계산해 저장하고, 각 행의 declaration_id·상태를 맞춘다.
  반입일이 들어온 묶음만 '신청 전'(RULES 11-3). 승인 행은 바꾸지 않는다.
"""

from app.a3_judge.grouping.split import group_rows
from app.a4_settings.engine.service import get_rules
from app.core.schema.declaration import Declaration
from app.core.schema.history import HistoryRow
from app.core.schema.shipper import ShipperSettings
from app.core.storage import work_db, work_db_more


def declarations_for(
    shipper_id: str, rows: list[HistoryRow], settings: ShipperSettings | None = None
) -> list[Declaration]:
    return group_rows(rows, settings or get_rules(shipper_id))


def recompute(shipper_id: str) -> list[Declaration]:
    rows = work_db.list_rows(shipper_id)
    active = [r for r in rows if r.status != "승인"]
    decls = declarations_for(shipper_id, active)
    by_row = {rid: d for d in decls for rid in d.row_ids}
    changed: list[HistoryRow] = []
    for r in active:
        d = by_row.get(r.row_id)
        new_id = d.declaration_id if d else None
        before = (r.declaration_id, r.status)
        r.declaration_id = new_id
        r.refresh_status()
        if r.status == "신청 전" and not (d and d.arrival_date):
            r.status = "반입 전"  # 반입일이 들어온 묶음만 '신청 전'(RULES 11-3)
        if (r.declaration_id, r.status) != before:
            changed.append(r)
    work_db.save_rows(changed)
    work_db_more.save_declarations(shipper_id, decls)
    return decls
