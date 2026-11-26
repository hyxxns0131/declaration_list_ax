"""서류 3종(CI·PL·B/L) 대조 OpenAI 분석. core/llm.py call_structured 한 곳만 부른다. 담당: KHS [신규]
(검역 리스트 탭 2단계, HS 요청 11/26 — PM 결정: 서류 대조에 OpenAI 분석 사용, AGENTS 7-5 예외)

- 선적 건(B/L) 하나에 한 번 부른다(비용). 항목마다 {같은지, 무엇이 다른지, 오타로 보이는 서류, 추천 값, 이유, confidence}.
- 코드로 짝이 안 지어진 품목 줄(모델 표기 차이)의 짝도 함께 받는다(참고용, 자동으로 합치지 않음).
- LLM_ENABLED=false·키 없음·실패면 None → 코드 대조만으로 판정('AI 분석 꺼짐').
- 화주명은 call_structured 안에서 가린다. 추천 값은 자동으로 final_value에 넣지 않는다.
"""

from typing import Literal

from pydantic import BaseModel
from pydantic import Field as PField

from app.core import llm
from app.core.schema.document import ParsedDocument
from app.core.schema.history import HistoryRow

PROMPT = "a1_history/crosscheck_docs"
VERSION = 1
DocName = Literal["CI", "PL", "BL", ""]


class AiItem(BaseModel):
    key: str  # "<row_id>|<항목 이름>"
    same: bool = True
    what: str = ""  # 무엇이 어떻게 다른지 한 줄
    typo_doc: DocName = ""  # 오타로 보이는 서류
    suggested: str = ""  # 추천 값(자동 적용하지 않음)
    reason: str = ""
    confidence: float = 0.0


class AiPair(BaseModel):
    ci_model: str = ""
    pl_model: str = ""
    reason: str = ""


class AiOut(BaseModel):
    items: list[AiItem] = PField(default_factory=list)
    pairs: list[AiPair] = PField(default_factory=list)


def _head(doc: ParsedDocument | None) -> dict | None:
    if not doc:
        return None
    return {
        "bl_no": doc.bl_no,
        "invoice_no": doc.invoice_no,
        "doc_date": doc.doc_date,
        "vessel": doc.vessel,
        "currency": doc.currency,
        "total_amount": doc.total_amount,
        "total_cartons": doc.total_cartons,
        "total_gross_kg": doc.total_gross_kg,
        "models": [ln.model for ln in doc.lines][:60],
    }


def analyze(
    rows_items: list[tuple[HistoryRow, list[dict]]],
    docs: list[ParsedDocument],
    mask_names: list[str],
) -> dict[str, dict[str, dict]] | None:
    """{row_id: {항목 이름: ai 결과 dict}}. AI를 못 쓰면 None."""
    if not llm.send_allowed() or not rows_items:  # 꺼짐·키 없음·화주명 목록 없음
        return None
    latest = {
        t: next((d for d in reversed(docs) if d.doc_type == t), None) for t in ("CI", "PL", "BL")
    }
    payload = {
        "documents": {t: _head(d) for t, d in latest.items()},
        "items": [
            {
                "key": f"{row.row_id}|{it['item']}",
                "model": row.model,
                "item": it["item"],
                "CI": it["CI"],
                "PL": it["PL"],
                "BL": it["BL"],
                "code_different": it["code_different"],
            }
            for row, items in rows_items
            for it in items
            if any(it[d] not in (None, "") for d in ("CI", "PL", "BL"))
        ],
    }
    out = llm.call_structured(PROMPT, VERSION, payload, AiOut, mask_names=mask_names)
    if out is None:
        return None
    res: dict[str, dict[str, dict]] = {}
    for a in out.items:
        rid, _, name = a.key.partition("|")
        res.setdefault(rid, {})[name] = a.model_dump(exclude={"key"})
    return res
