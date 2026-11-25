"""영역 라우터 (화주 설정·규칙 엔진). 담당: JUJ

GET  /settings/rules                      규칙 목록(묶음·설명·기본값)
GET  /settings/shippers                   화주 목록(가명)
POST /settings/shippers                   화주 추가(default.json 기본값으로)
GET  /settings/shippers/{id}              화주 설정(기본값과 합친 값, 기본과 다른 키)
PUT  /settings/shippers/{id}              저장(검증, 모르는 키 거절) → 그 화주 행 재판단
POST /settings/shippers/{id}/dry-run      시험 실행(저장 없이 전/후)
DELETE /settings/shippers/{id}            화주 삭제(기본 A·B 불가, 백업으로 옮김) — HS 요청 11/25
"""

from fastapi import APIRouter
from pydantic import BaseModel
from pydantic import Field as PField

from app.a1_history.rows import service as rows_service
from app.a4_settings.dry_run.service import dry_run
from app.a4_settings.shippers import service

router = APIRouter(prefix="/settings", tags=["settings"])


class NewShipper(BaseModel):
    shipper_id: str
    display_name: str
    required_docs: list[str] | None = None


class SaveIn(BaseModel):
    settings: dict


class DryRunIn(BaseModel):
    settings: dict = PField(default_factory=dict)
    bl_no: str | None = None


@router.get("/rules")
def rules() -> dict:
    return {"catalog": service.catalog(), "default": service.default()}


@router.get("/shippers")
def shippers() -> list[dict]:
    return service.list_shippers()


@router.post("/shippers")
def create(body: NewShipper) -> dict:
    return service.create_shipper(body.shipper_id, body.display_name, body.required_docs)


@router.get("/shippers/{shipper_id}")
def get(shipper_id: str) -> dict:
    return service.get_shipper(shipper_id)


@router.put("/shippers/{shipper_id}")
def save(shipper_id: str, body: SaveIn) -> dict:
    out = service.save_shipper(shipper_id, body.settings)
    out["rebuilt"] = rows_service.rebuild_all(shipper_id)  # 설정 변경 → 행·판단 재계산(AGENTS 3장)
    return out


@router.post("/shippers/{shipper_id}/dry-run")
def run(shipper_id: str, body: DryRunIn) -> dict:
    return dry_run(shipper_id, body.settings, body.bl_no)


@router.delete("/shippers/{shipper_id}")
def delete(shipper_id: str) -> dict:
    return service.delete_shipper(shipper_id)
