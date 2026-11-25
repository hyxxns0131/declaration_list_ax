"""표가 안 읽히는 PDF·스캔본 → AI 판독. core/llm.py만 부른다(AGENTS 7장). 담당: KHS [개선] A0-1

LLM_ENABLED=false거나 결과를 못 얻으면 None → 호출한 쪽이 "확인 필요"로 둔다.
"""

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.llm import call_structured
from app.core.schema.document import DocumentLine

PROMPT = "a0_reader/read_shipping_docs"
VERSION = 1
MAX_CHARS = 20000  # 보내는 글자 상한(비용). 원문은 로그에 남기지 않는다


class AiDocument(BaseModel):
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


def read_with_ai(doc_type: str, text: str, mask_names: list[str]) -> AiDocument | None:
    if not text.strip():
        return None
    return call_structured(
        PROMPT,
        VERSION,
        {"doc_type": doc_type, "text": text[:MAX_CHARS]},
        AiDocument,
        mask_names=mask_names,
    )
