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
    qty_per_carton: float | None = None  # 입수(카톤 1개에 든 수량, AGENTS 12장)
    quantity: float | None = None  # 수량(PCS 합계). 검역이력 '입수' 칸 값(HS 결정 11/26)
    cartons: float | None = None
    net_kg: float | None = None
    amount: float | None = None
    is_part: bool = False
    color: str = ""  # 내색(또는 색상)
    outer_color: str = ""  # 외색 (서류에 따로 있을 때)

    def pcs(self) -> float | None:
        """전체 개수(PCS 합계) = 검역이력 '입수' 칸 값(HS 결정 11/26).
        서류의 수량(PCS) 칸 값, 없으면 카톤당 수량 x 카톤 수(둘 다 서류 값일 때만), 아니면 None."""
        if self.quantity is not None:
            return self.quantity
        if self.qty_per_carton is not None and self.cartons is not None:
            return round(self.qty_per_carton * self.cartons, 4)
        return None


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
    # 칸마다 출처: {"bl_no": "excel" | "pdf" | "llm" | "llm:image"} (검역 리스트 탭 1단계)
    sources: dict[str, str] = PField(default_factory=dict)
