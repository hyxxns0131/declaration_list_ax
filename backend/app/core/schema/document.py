"""서류 판독 결과(ParsedDocument) — A0 출력. AGENTS 5-5. 담당: KHS"""

from typing import Literal

from pydantic import BaseModel
from pydantic import Field as PField

DocType = Literal[
    "CI", "PL", "BL", "CO", "INTAKE_LIST", "IMPORT_DECL", "TEST_REPORT", "PHOTO", "LABEL"
]


class DocumentLine(BaseModel):
    model: str = ""
    description: str = ""
    qty_per_carton: float | None = None  # 입수
    cartons: float | None = None
    net_kg: float | None = None
    amount: float | None = None
    is_part: bool = False
    color: str = ""  # 내색(또는 색상)
    outer_color: str = ""  # 외색 (서류에 따로 있을 때)


class ParsedDocument(BaseModel):
    doc_id: str
    shipper_id: str
    folder_id: str  # 폴더 1개 = 선적서류 1건
    doc_type: DocType
    bl_no: str = ""
    invoice_no: str = ""
    doc_date: str = ""
    vessel: str = ""
    manufacturer_name: str = ""
    manufacturer_address: str = ""
    currency: str = ""
    total_amount: float | None = None
    total_cartons: float | None = None
    total_gross_kg: float | None = None
    lines: list[DocumentLine] = PField(default_factory=list)
    parser: Literal["excel", "pdf", "llm"] = "excel"
    warnings: list[str] = PField(default_factory=list)
