"""표가 안 읽히는 PDF·스캔본 → AI 판독. core/llm.py만 부른다(AGENTS 7장). 담당: KHS [개선] A0-1

LLM_ENABLED=false거나 결과를 못 얻으면 None → 호출한 쪽이 "확인 필요"로 둔다.
"""

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.llm import call_structured
from app.core.schema.document import DocumentLine

Grid = list[list[object]]

PROMPT = "a0_reader/read_shipping_docs"
VERSION = 3
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


def read_with_ai(
    doc_type: str, text: str, mask_names: list[str], images: list[bytes] | None = None
) -> AiDocument | None:
    """글자(text) 또는 페이지 이미지(images)로 판독. 둘 다 없으면 None."""
    if not text.strip() and not images:
        return None
    return call_structured(
        PROMPT,
        VERSION,
        {"doc_type": doc_type, "text": text[:MAX_CHARS], "has_images": bool(images)},
        AiDocument,
        mask_names=mask_names,
        images=images,
    )


def grid_text(grid: Grid, max_rows: int = 400) -> str:
    """엑셀·PDF 표 격자 → 탭으로 나눈 글자(줄마다 한 행). AI 판독 입력용."""
    rows = []
    for r in grid[:max_rows]:
        cells = ["" if c is None else str(c).strip() for c in r]
        if any(cells):
            rows.append("\t".join(cells).rstrip())
    return "\n".join(rows)
