"""영역 라우터 (서류 등록·실적·만료 알림). 담당: YHS

POST /registry/upload, POST /registry/upload/{upload_id}/commit
GET /registry/records, GET·PATCH /registry/records/{record_no}, POST /registry/records/{no}/approval
GET /registry/alerts, GET /registry/alerts/preview, POST /registry/alerts/send
GET /registry/factories, PATCH /registry/factories/{code} (A2-5, factory_codes/router.py)
"""

from datetime import date

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel
from pydantic import Field as PField

from app.a1_history.rows import service as rows_service
from app.a2_registry.alerts import service as alerts
from app.a2_registry.factory_codes.router import router as factory_codes_router
from app.a2_registry.records import service as records
from app.a2_registry.upload import service as upload
from app.a3_judge.material.codes import load_known_names
from app.a4_settings.engine.service import get_rules
from app.core.errors import AppError
from app.core.schema.record import Record
from app.core.storage import drive, gmail
from app.core.storage import work_db_more as store
from app.core.unipass import client as unipass

router = APIRouter(prefix="/registry", tags=["registry"])
router.include_router(factory_codes_router)
DEFAULT_PREFIXES = ["2BB", "2BD", "2BH", "2CE", "2BC"]  # 기존 도구에서 확인된 통지번호 앞 글자


class CommitIn(BaseModel):
    edits: list[dict] = PField(default_factory=list)


class RecordPatch(BaseModel):
    changes: dict


@router.post("/upload")
async def upload_docs(shipper_id: str = Form(...), files: list[UploadFile] = File(...)) -> dict:
    got = [(f.filename or "file", await f.read()) for f in files]
    if not got:
        raise AppError("invalid_input", "파일을 골라 주세요.")
    body = upload.create_upload(shipper_id, got, load_known_names())
    body["drive"] = drive.status()
    return body


@router.post("/upload/{upload_id}/commit")
def commit(upload_id: str, body: CommitIn) -> dict:
    out = upload.commit_upload(upload_id, body.edits)
    # 등록하면 재질·제조사·실적 판단을 이 데이터로 다시 계산한다(DESIGN 6장)
    out["rejudged"] = rows_service.rejudge(out["shipper_id"])
    up = store.get_upload(upload_id) or {}
    out["drive"] = drive.status()
    if out["drive"]["ok"]:
        for c in up.get("candidates", []):
            folder = store_folder(out["shipper_id"], c)
            path = next(
                iter(sorted((records_dir(out["shipper_id"])).glob(f"{c['doc_id']}_*"))), None
            )
            if path:
                drive.upload(path, c["filename"], folder)
    return out


def records_dir(shipper_id: str):
    from app.core.config import get_settings

    return get_settings().data_path / "registry" / shipper_id


def store_folder(shipper_id: str, c: dict) -> list[str]:
    """드라이브 폴더(RULES 11-1): {화주}/재질 시험성적서/, {화주}/현품사진 및 한글표시 사항/{모델}/"""
    if c.get("kind") == "시험성적서":
        return [shipper_id, "재질 시험성적서"]
    return [shipper_id, "현품사진 및 한글표시 사항", c.get("model") or "모델 미상"]


@router.get("/records")
def list_records(
    shipper_id: str | None = None, maker: str = "", model: str = "", status: str = ""
) -> list[Record]:
    recs = records.list_records(shipper_id, maker, model, status)
    rows = rows_service.list_history(shipper_id) if shipper_id else []
    return records.attach_uses(recs, rows)


@router.get("/records/{record_no}")
def get_record(record_no: str) -> Record:
    return records.get_record(record_no)


@router.patch("/records/{record_no}")
def patch_record(record_no: str, body: RecordPatch) -> Record:
    rec = records.update_record(record_no, body.changes)
    got = store.get_record(record_no)
    if got and got[1]:
        rows_service.rejudge(got[1])
    return rec


@router.post("/records/{record_no}/approval")
def lookup_approval(record_no: str) -> Record:
    """유니패스 검사검역내역으로 승인일(검사/검역 결정일) 조회. live 모드에서만."""
    got = store.get_record(record_no)
    if not got:
        raise AppError("not_found", f"실적 {record_no}이(가) 없습니다.", 404)
    rec, sid = got
    prefixes = [r.ntfc_no[:3] for r, _ in store.list_records() if r.ntfc_no] + DEFAULT_PREFIXES
    info = unipass.find_approval(record_no, list(dict.fromkeys(prefixes)))
    if not info:
        raise AppError(
            "not_found", "유니패스에서 승인일을 찾지 못했습니다(live 모드·키 확인).", 404
        )
    rec.ntfc_no = info["ntfc"]
    rec.approved_on = info["approved"] or rec.approved_on
    rec.applied_on = info["applied"] or rec.applied_on
    rec.memo = f"유니패스 검사검역내역 {info['ntfc']} ({info.get('office', '')})"
    return records.save(rec, sid)


@router.get("/alerts")
def get_alerts(shipper_id: str | None = None, within_days: int | None = None) -> dict:
    items = alerts.expiring(shipper_id, within_days)
    ok, why = gmail.configured()
    return {
        "items": [a.model_dump() for a in items],
        "summary": alerts.summary(items),
        "mail": {"ok": ok, "reason": why},
        "today": date.today().isoformat(),
    }


@router.get("/alerts/preview")
def preview(shipper_id: str | None = None) -> dict:
    items = [a for a in alerts.expiring(shipper_id) if not a.sent]
    label = get_rules(shipper_id).display_name if shipper_id else "전체"
    subject, body = alerts.mail_text(items, label)
    return {"subject": subject, "body": body, "count": len(items)}


@router.post("/alerts/send")
def send_alerts(shipper_id: str | None = None) -> dict:
    label = get_rules(shipper_id).display_name if shipper_id else "전체"
    return alerts.send(shipper_id, label)
