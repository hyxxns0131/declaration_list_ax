"""칸 공통 형태: Field(ai_value / final_value / evidence / flag / memo). AGENTS 5-5. 담당: KHS"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel
from pydantic import Field as PField

T = TypeVar("T")

EvidenceSource = Literal[
    "CI",
    "PL",
    "BL",
    "CO",
    "INTAKE_LIST",
    "IMPORT_DECL",
    "TEST_REPORT",
    "HISTORY",
    "PHOTO",
    "LABEL",
    "UNIPASS",
    "FX",
    "RULE",
    "MANUAL",
]
Flag = Literal["ok", "mismatch", "edited", "need_input", "need_check"]


class Evidence(BaseModel):
    source: EvidenceSource
    ref: str  # 문서 id, 이력 행 id, 규칙 키 등
    note: str = ""  # 사람이 읽을 근거 한 줄


class Field(BaseModel, Generic[T]):
    ai_value: T | None = None
    final_value: T | None = None  # 담당자 확정 값. 재실행이 덮어쓰지 않음 (AGENTS 0-5)
    evidence: list[Evidence] = PField(default_factory=list)
    flag: Flag = "ok"
    memo: str = ""  # 지우면 '확인함' (RULES 11-9)

    @property
    def value(self) -> T | None:
        """화면에 보일 값: final_value가 있으면 그것."""
        return self.final_value if self.final_value is not None else self.ai_value

    def rerun(self, new_ai_value: T | None, evidence: list[Evidence]) -> "Field[T]":
        """재실행: ai_value·근거만 바꾸고 final_value는 그대로 둔다."""
        return self.model_copy(update={"ai_value": new_ai_value, "evidence": evidence})
