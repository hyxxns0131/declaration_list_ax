"""영역 라우터 (서류 판독). 담당: KHS

POST /reader/preview   파일 이름 → 서류 종류 미리 보기 (DESIGN 3-1-1 "인식한 서류")
POST /reader/upload    서류 올리기 → 판독 → 검역이력 행까지 (응답: 만든·고친 row_id, 서류별 판별·경고)
GET  /reader/shipments?shipper_id=   선적 건 목록(B/L로 묶음)과 서류별 추출값·빠진 서류 (검역 리스트 탭 1단계)
PUT  /reader/shipments/bl           B/L 번호를 못 읽은 선적 건에 번호 직접 입력 → 그 번호로 묶어 행 다시 만들기
POST /reader/shipments/reread       선적 건 다시 읽기(저장된 원본을 지금 판독 규칙으로)
POST /reader/shipments/delete       선적 건 삭제(서류·행을 DATA_DIR/deleted/에 백업, 승인 행이 있으면 거부)
POST /reader/inbox/scan?shipper_id=  드라이브 접수 폴더에서 가져오기(화주 설정 inbox, 미연결이면 이유)
GET  /reader/documents/{doc_id}        판독 결과
GET  /reader/documents/{doc_id}/file   원본 보기
"""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.a0_reader.shipments import list_shipments
from app.a1_history.rows import service as rows_service
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schema.document import ParsedDocument
from app.core.storage import work_db

router = APIRouter(prefix="/reader", tags=["reader"])
MAX_FILE_MB = 30


class PreviewIn(BaseModel):
    shipper_id: str
    filenames: list[str]


@router.post("/preview")
def preview(body: PreviewIn) -> dict:
    return rows_service.preview(body.filenames, body.shipper_id)


@router.post("/upload")
async def upload(
    shipper_id: str = Form(...),
    files: list[UploadFile] = File(...),
    folder_id: str | None = Form(default=None),  # 주면 그 선적 건에 서류를 더 올린다
) -> dict:
    got: list[tuple[str, bytes]] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_MB * 1024 * 1024:
            raise AppError(
                "too_large", f"{f.filename}: {MAX_FILE_MB}MB를 넘는 파일은 올릴 수 없습니다."
            )
        got.append((f.filename or "file", data))
    return rows_service.process_upload(shipper_id, got, folder_id or None)


@router.get("/shipments")
def shipments(shipper_id: str) -> list[dict]:
    return list_shipments(shipper_id)


class ShipmentBlIn(BaseModel):
    shipper_id: str
    folder_ids: list[str]
    bl_no: str


class ShipmentDeleteIn(BaseModel):
    shipper_id: str
    folder_ids: list[str]


@router.put("/shipments/bl")
def shipment_bl(body: ShipmentBlIn) -> dict:
    return rows_service.assign_folder_bl(body.shipper_id, body.folder_ids, body.bl_no)


@router.post("/shipments/reread")
def shipment_reread(body: ShipmentDeleteIn) -> dict:
    """[이 건 다시 읽기]: 저장된 원본을 지금 판독 규칙으로 다시 읽고 행을 다시 만든다."""
    return rows_service.reread_shipment(body.shipper_id, body.folder_ids)


@router.post("/shipments/delete")
def shipment_delete(body: ShipmentDeleteIn) -> dict:
    return rows_service.delete_shipment(body.shipper_id, body.folder_ids)


@router.get("/documents/{doc_id}")
def document(doc_id: str) -> ParsedDocument:
    got = work_db.get_document(doc_id)
    if not got:
        raise AppError("not_found", "서류가 없습니다.", 404)
    return got[0]


@router.get("/documents/{doc_id}/file")
def document_file(doc_id: str) -> FileResponse:
    got = work_db.get_document(doc_id)
    if not got:
        raise AppError("not_found", "서류가 없습니다.", 404)
    _, filename, rel = got
    base = get_settings().data_path.resolve()
    path = (base / rel).resolve()
    if base not in path.parents or not path.exists():
        raise AppError("not_found", "원본 파일이 없습니다.", 404)
    return FileResponse(path, filename=filename, content_disposition_type="inline")


@router.post("/inbox/scan")
def inbox_scan(shipper_id: str) -> dict:
    return rows_service.scan_inbox(shipper_id)
