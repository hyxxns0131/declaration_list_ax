"""영역 라우터 (판단·신고건·품목사항). 담당: LSY

GET  /judge/{row_id}                  재질·실적·제조사 판단 근거와 후보 (DESIGN 5장 JudgeEvidence)
POST /judge/rejudge?shipper_id=       기업 설정 바꾼 뒤 재질·제조사·실적 다시 판단(확정 값 유지) — 11/28
POST /judge/declarations?shipper_id=  신고건 나누기 계산(저장하고 돌려준다)
GET  /judge/declarations?shipper_id=  저장된 신고건
POST /judge/item-sheet/preview        고른 행 → 한 신고건인지 + 품목사항 미리보기
POST /judge/item-sheet                품목사항 엑셀 생성 → file_id
GET  /judge/item-sheet/{file_id}      엑셀 다운로드
GET  /judge/item-sheet-groups?shipper_id=&group_by=   같은 품목끼리 묶음 (재질·제조업소·품목·실적번호) — HS 요청 11/26
GET  /judge/item-sheet/review?shipper_id=&declaration_ids=  검토용 전체 엑셀 1개(신고건 사이 빈 행, 막힌 건 포함) — 시연 피드백 11/27
POST /judge/item-sheet/bulk           전체 / 고른 신고건 / 고른 묶음 → ZIP(신고건마다 xlsx + 검토용 전체 + 제외됨.txt) file_id
GET  /judge/item-sheet/bulk/{file_id} ZIP 다운로드
POST /judge/item-sheet/google?shipper_id=&declaration_id=  신고건 1건 → 공유 폴더에 구글 시트 새로 만들기 — 11/28
GET  /judge/{row_id}/model-docs       모델 자료(현품사진·라벨 엑셀·수입신고서.json) 목록 — 드라이브 읽기만 (11/27)
GET  /judge/model-docs/file/{file_id} 모델 자료 파일 내려받기
"""

import mimetypes
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.a3_judge.grouping.service import recompute
from app.a3_judge.item_sheet import bulk as item_bulk
from app.a3_judge.item_sheet import service as item_sheet
from app.a3_judge.model_docs import service as model_docs
from app.a3_judge.pipeline.service import judge_detail
from app.core.errors import AppError
from app.core.schema.declaration import Declaration
from app.core.storage import work_db, work_db_more

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
router = APIRouter(prefix="/judge", tags=["judge"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ZIP = "application/zip"


class RowIds(BaseModel):
    row_ids: list[str]


class BulkIn(BaseModel):
    shipper_id: str
    declaration_ids: list[str] | None = None
    group_by: str | None = None  # material | factory | product | record
    groups: list[str] | None = None


@router.post("/item-sheet/google")
def item_sheet_google(shipper_id: str, declaration_id: str) -> dict:
    """신고건 1건을 공유 폴더(ITEM_SHEET_FOLDER_ID)에 구글 시트로 새로 만든다. 로그인·폴더가 없으면 이유만."""
    from app.a3_judge.item_sheet.google_sheet import create_item_sheet

    return create_item_sheet(shipper_id, declaration_id)


@router.post("/rejudge")
def rejudge(shipper_id: str) -> dict:
    """기업 설정(재질 근거 순서 등)을 바꾼 뒤 재질·제조사·실적 다시 판단 + 신고건 다시 묶기. 확정 값·승인 행 유지.
    설정 저장(기능 4)이 판단을 다시 부르지 않아서 탭 4에서 누른다(11/28)."""
    from app.a1_history.rows.service import rejudge as rows_rejudge

    return {"rejudged": rows_rejudge(shipper_id)}


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


@router.get("/item-sheet-groups")
def item_sheet_groups(shipper_id: str, group_by: str) -> list[dict]:
    return item_bulk.groups(shipper_id, group_by)


@router.post("/item-sheet/bulk")
def item_sheet_bulk(body: BulkIn) -> dict:
    return item_bulk.export(body.shipper_id, body.declaration_ids, body.group_by, body.groups)


@router.get("/item-sheet/review")
def item_sheet_review(shipper_id: str, declaration_ids: str = "") -> Response:
    """검토용 전체 엑셀 1개(시트 1장, 신고건 사이 빈 행, 막힌 건도 이유와 함께). 신고용이 아님.
    declaration_ids: 쉼표로 여러 개(비우면 전체)."""
    ids = [x for x in declaration_ids.split(",") if x.strip()]
    filename, data = item_bulk.review_export(shipper_id, ids or None)
    return Response(
        data,
        media_type=XLSX_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/item-sheet/bulk/{file_id}")
def item_sheet_bulk_download(file_id: str) -> FileResponse:
    filename, path = item_sheet.file_path(file_id)
    return FileResponse(path, filename=filename, media_type=ZIP)


@router.get("/item-sheet/{file_id}")
def item_sheet_download(file_id: str) -> FileResponse:
    filename, path = item_sheet.file_path(file_id)
    return FileResponse(path, filename=filename, media_type=XLSX)


@router.get("/model-docs/file/{file_id}")
def model_doc_file(file_id: str) -> Response:
    """모델 자료 파일 내려받기. 목록(/judge/{row_id}/model-docs)으로 보여 준 파일만."""
    got = model_docs.download_model_doc(file_id)
    if not got:
        raise AppError("not_found", "모델 자료를 다시 불러온 뒤 받아 주세요.", 404)
    name, data = got
    kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return Response(
        data,
        media_type=kind,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@router.get("/{row_id}/model-docs")
def row_model_docs(row_id: str) -> dict:
    """그 행 모델의 자료 폴더(서류 접수/{화주}/현품사진 및 한글표시 사항/{모델명}) 파일 목록. 읽기만."""
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    return model_docs.find_model_docs(row.shipper_id, row.model)


@router.get("/{row_id}")
def judge(row_id: str) -> dict:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    detail = judge_detail(row, work_db.list_rows(row.shipper_id))
    return {"row_id": row_id, "model": row.model, "is_part": row.is_part, **detail}
