"""품목사항 공개 함수: 미리보기·생성·다운로드. AI 없음. 담당: LSY [재사용] A3-5

- 고른 행이 한 신고건이 아니면 만들지 않고 이유를 돌려준다(check_one_declaration).
- 행 순서는 검역이력 표 순서. 첫 행 = 대표품목 Y.
- 파일 이름 `품목사항_<화주ID>_<B/L>_<날짜>.xlsx` (DESIGN 5장). 파일은 DATA_DIR/item_sheets/.
"""

import uuid
from datetime import date

from app.a3_judge.grouping.keys import row_key
from app.a3_judge.item_sheet.build import HEADERS, build_item_sheet
from app.a3_judge.item_sheet.validate import check_one_declaration
from app.a3_judge.item_sheet.writer import write_xlsx
from app.a4_settings.engine.service import get_rules
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schema.history import C_ARRIVAL, C_BL, C_RECORD, HistoryRow
from app.core.storage import local_db, work_db, work_db_more


def _rows(row_ids: list[str]) -> list[HistoryRow]:
    if not row_ids:
        raise AppError("invalid_input", "행을 골라 주세요.")
    got = work_db.get_rows(row_ids)
    if len(got) != len(set(row_ids)):
        raise AppError("not_found", "없는 행이 있습니다. 표를 새로 불러오세요.", 404)
    order = {r.row_id: i for i, r in enumerate(work_db.list_rows(got[0].shipper_id))}
    return sorted(got, key=lambda r: order.get(r.row_id, 0))


def preview(row_ids: list[str]) -> dict:
    rows = _rows(row_ids)
    shipper_id = rows[0].shipper_id
    settings = get_rules(shipper_id)
    reasons = check_one_declaration(rows, settings)
    if len({r.shipper_id for r in rows}) > 1:
        reasons.append("화주가 다른 행이 섞여 있습니다.")
    sheet = build_item_sheet(rows)
    key = row_key(rows[0], settings)
    arrivals = sorted({r.text(C_ARRIVAL) for r in rows if r.text(C_ARRIVAL)})
    bls = sorted({r.text(C_BL) for r in rows if r.text(C_BL)})
    records = sorted({r.text(C_RECORD).split(" ")[0] for r in rows if r.text(C_RECORD)})
    return {
        "ok": not reasons,
        "reasons": reasons,
        "headers": [h for h, _ in HEADERS],
        "rows": sheet.rows,
        "warnings": sheet.warnings,
        "key": key.model_dump(),
        "arrival_date": arrivals[-1] if arrivals else None,
        "bl_count": len(bls),
        "record_nos": records,
        "missing_record_rows": [
            f"{r.text(C_BL)} {r.model}".strip() for r in rows if not r.text(C_RECORD)
        ],
    }


def create(row_ids: list[str]) -> dict:
    info = preview(row_ids)
    if not info["ok"]:
        raise AppError("not_one_declaration", " / ".join(info["reasons"]), 400)
    rows = _rows(row_ids)
    shipper_id = rows[0].shipper_id
    data = write_xlsx(build_item_sheet(rows))
    bl = rows[0].text(C_BL) or "BL미상"
    filename = f"품목사항_{shipper_id}_{bl}_{date.today():%Y%m%d}.xlsx"
    file_id = uuid.uuid4().hex[:12]
    base = get_settings().data_path
    folder = base / "item_sheets"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{file_id}.xlsx"
    path.write_bytes(data)
    work_db_more.save_item_file(
        file_id, shipper_id, filename, path.relative_to(base).as_posix(), row_ids
    )
    local_db.audit("item_sheet", shipper_id, f"rows={len(row_ids)}")
    return {"file_id": file_id, "filename": filename, "warnings": info["warnings"]}


def file_path(file_id: str) -> tuple[str, str]:
    got = work_db_more.get_item_file(file_id)
    if not got:
        raise AppError("not_found", "파일이 없습니다.", 404)
    filename, rel = got
    return filename, str(get_settings().data_path / rel)
