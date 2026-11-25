"""수입신고서·시험성적서 판독 값과 등록 후보. 담당: YHS

판독 값 형식은 기존 도구 수입신고서.json / test_reports/<번호>.json과 같다(키 이름 유지).
"""

from typing import Literal

from pydantic import BaseModel
from pydantic import Field as PField


class DeclMaterial(BaseModel):
    code: str = ""  # 14자리 재질 코드
    name: str = ""  # 재질 코드명


class ImportDecl(BaseModel):
    receipt_no: str = ""
    receipt_date: str | None = None
    accepted_date: str | None = None  # 신고수리일
    inspection_type: str | None = None  # 정밀 · 서류 · 현장 …
    product_en: str | None = None
    product_ko: str | None = None
    materials: list[DeclMaterial] = PField(default_factory=list)
    maker_code: str | None = None
    maker_name: str | None = None
    maker_address: str | None = None


class TestSample(BaseModel):
    material: str = ""
    part: str = ""
    color: str = ""
    remark: str = ""


class TestReport(BaseModel):
    receipt_no: str = ""  # = 실적접수번호
    samples: list[TestSample] = PField(default_factory=list)
    approval_date: str | None = None
    applied_date: str | None = None
    maker_code: str | None = None
    maker_name: str | None = None
    models: list[str] = PField(default_factory=list)


class Candidate(BaseModel):
    """등록 후보 1줄(DESIGN 6장 '등록 후보' 표). 칸마다 상태: ok · need_check · different(기존 등록과 다름)."""

    cand_id: str
    kind: Literal["수입신고서", "시험성적서"]
    filename: str
    doc_id: str = ""  # 저장한 원본(로컬 사본) id
    receipt_no: str = ""
    model: str = ""
    product_ko: str = ""
    product_en: str = ""
    materials: list[str] = PField(default_factory=list)
    material_codes: list[str] = PField(default_factory=list)
    maker_code: str = ""
    maker_name: str = ""
    maker_address: str = ""
    inspection_type: str = ""  # 정밀 · 서류
    applied_on: str = ""
    approved_on: str = ""
    sample_parts: list[TestSample] = PField(default_factory=list)
    status: dict[str, str] = PField(default_factory=dict)  # 칸 이름 → ok|need_check|different
    previous: dict[str, str] = PField(default_factory=dict)  # 기존 등록 값(다를 때만)
    warnings: list[str] = PField(default_factory=list)
    parser: Literal["json", "llm", "none"] = "json"
