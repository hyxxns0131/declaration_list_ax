"""영역 라우터 (판단·신고건·품목사항). 담당: LSY

GET  /judge/{row_id}                  재질·실적·제조사 판단 근거와 후보 (DESIGN 5장 JudgeEvidence)
POST /judge/declarations?shipper_id=  신고건 나누기 계산(저장하고 돌려준다)
GET  /judge/declarations?shipper_id=  저장된 신고건
POST /judge/item-sheet/preview        고른 행 → 한 신고건인지 + 품목사항 미리보기
POST /judge/item-sheet                품목사항 엑셀 생성 → file_id
GET  /judge/item-sheet/{file_id}      엑셀 다운로드
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.a3_judge.grouping.service import recompute
from app.a3_judge.item_sheet import service as item_sheet
from app.a3_judge.pipeline.service import judge_detail
from app.core.errors import AppError
from app.core.schema.declaration import Declaration
from app.core.storage import work_db, work_db_more

router = APIRouter(prefix="/judge", tags=["judge"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class RowIds(BaseModel):
    row_ids: list[str]


@router.post("/declarations")
def declarations(shipper_id: str) -> list[Declaration]:
    return recompute(shipper_id)


@router.get("/declarations")
def saved_declarations(shipper_id: str) -> list[Declaration]:
    return work_db_more.list_declarations(shipper_id)


@router.post("/item-sheet/preview")
def item_sheet_preview(body: RowIds) -> dict:
    return item_sheet.preview(body.row_ids)


@router.post("/item-sheet")
def item_sheet_create(body: RowIds) -> dict:
    return item_sheet.create(body.row_ids)


@router.get("/item-sheet/{file_id}")
def item_sheet_download(file_id: str) -> FileResponse:
    filename, path = item_sheet.file_path(file_id)
    return FileResponse(path, filename=filename, media_type=XLSX)


@router.get("/{row_id}")
def judge(row_id: str) -> dict:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    detail = judge_detail(row, work_db.list_rows(row.shipper_id))
    return {"row_id": row_id, "model": row.model, "is_part": row.is_part, **detail}
