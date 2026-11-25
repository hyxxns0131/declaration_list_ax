"""신고건(Declaration) — A3 출력. 빈 행 1개 = 신고건 경계를 데이터로. AGENTS 5-5. 담당: KHS(모델)"""

from pydantic import BaseModel
from pydantic import Field as PField


class DeclarationKey(BaseModel):
    vessel_key: str = ""  # 화물관리번호 앞 11자리
    factory_code: str = ""
    material: str = ""
    color: str | None = None


class Declaration(BaseModel):
    declaration_id: str
    shipper_id: str
    key: DeclarationKey
    row_ids: list[str] = PField(default_factory=list)  # 순서 유지
    record_nos: list[str] = PField(default_factory=list)
    arrival_date: str | None = None  # 묶인 B/L 중 가장 최근 반입일
    warnings: list[str] = PField(default_factory=list)
