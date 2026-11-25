"""해외제조업소 코드 갱신 API (A2-5). a2_registry 영역 라우터에 포함된다. 담당: YHS

GET /registry/factories?within_days=, PATCH /registry/factories/{code}
"""

from fastapi import APIRouter

from app.a2_registry.factory_codes import service
from app.a2_registry.factory_codes.models import FactoryCode, FactoryPatch

router = APIRouter()


@router.get("/factories")
def list_factories(within_days: int | None = None) -> list[FactoryCode]:
    return service.list_factories(within_days)


@router.patch("/factories/{code}")
def patch_factory(code: str, body: FactoryPatch) -> FactoryCode:
    return service.update_registered_on(code, body.registered_on)
