"""정밀검사 실적(Record) — A2 소유 데이터. AGENTS 5-5. 담당: KHS(모델)"""

from typing import Literal

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.schema.fields import Evidence

RecordStatus = Literal["유효", "만료 임박", "만료"]


class SamplePart(BaseModel):
    material: str = ""
    part: str = ""
    color: str = ""


class RecordUse(BaseModel):
    """이 실적으로 신고한 행(서류검사 내역). 정밀/서류 구분(RULES 11-8)."""

    bl_no: str = ""
    model: str = ""
    kind: Literal["정밀", "서류"] = "서류"
    row_id: str = ""


class Record(BaseModel):
    record_no: str
    factory_code: str = ""
    factory_name: str = ""
    factory_address: str = ""
    materials: list[str] = PField(default_factory=list)  # 그 실적으로 승인된 재질만
    spec_class: str = ""
    sample_parts: list[SamplePart] = PField(default_factory=list)
    applied_on: str | None = None  # YYYY-MM-DD
    approved_on: str | None = None  # 검사/검역 결정일
    expires_on: str | None = None  # 승인일 + RECORD_VALID_YEARS (설정값)
    products: list[str] = PField(default_factory=list)  # 실적 인정 모델
    product_names: list[str] = PField(default_factory=list)  # 품명(예: 전기밥솥). 같은 품명 판정
    ntfc_no: str = ""  # 유니패스 통지번호(승인일 조회에 씀)
    uses: list[RecordUse] = PField(default_factory=list)
    status: RecordStatus = "유효"
    evidence: list[Evidence] = PField(default_factory=list)  # 어느 서류에서 왔나
    memo: str = ""
