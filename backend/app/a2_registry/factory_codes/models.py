"""해외제조업소 코드 갱신 관리 모델 (A2-5). 담당: YHS"""

from typing import Literal

from pydantic import BaseModel

FactoryStatus = Literal["유효", "만료 임박", "만료", "확인 필요"]


class FactoryCode(BaseModel):
    code: str
    name: str = ""
    address: str = ""
    registered_on: str | None = None  # 등록(갱신)일 YYYY-MM-DD. 모르면 None → "확인 필요"
    expires_on: str | None = None  # 등록일 + FACTORY_CODE_VALID_YEARS
    days_left: int | None = None
    status: FactoryStatus = "확인 필요"
    source: str = ""  # 실적 · 제품 등록 · samples(가상) · 담당자


class FactoryPatch(BaseModel):
    registered_on: str | None = None  # 비우면 등록일 모름("확인 필요")으로 되돌린다
