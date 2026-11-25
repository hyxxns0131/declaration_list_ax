"""검역이력 행(HistoryRow)과 26칸 열 이름 상수. 열 이름은 이 파일에서만 정한다(AGENTS 0-7). 담당: KHS"""

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.schema.fields import Evidence, Field, Flag

# 기존 검역이력 시트(A기업 탭) 26칸. 이름·순서를 바꾸지 않는다.
COLUMNS: tuple[str, ...] = (
    "B/L Number",
    "반입지 코드",
    "반입일",
    "입항일",
    "선적일",
    "모선명",
    "도착항 코드",
    "선적항 코드",
    "제조사",
    "화물관리번호",
    "한글 제품명(모델넘버)",
    "입수",
    "카톤 수",
    "순중량",
    "가격(USD)",
    "USD 환율",
    "CI 통화",
    "가격(수출국)",
    "CI 통화 환율",
    "재질 (재질 코드명으로 작성, 가나다 순으로 기재)",
    "실적접수번호 (승인일)",
    "영문 제품명",
    "재질 구분 (깊이·용량·용도)",
    "검역 신고일자",
    "승인번호",
    "비고",
)
COLOR_COLUMN = "색상"  # B사 탭: 재질 다음 칸
HIDDEN_COLUMNS = ("USD 환율", "CI 통화", "CI 통화 환율")

# 반입 전: 판단은 끝났지만 반입일이 없어 아직 신청할 수 없음(RULES 11-3 '반입일 들어온 묶음만 신청 전')
RowStatus = Literal["자료 추가 필요", "확인 필요", "반입 전", "신청 전", "승인"]

# 자주 쓰는 열 이름 (COLUMNS의 값과 같아야 한다)
C_BL = "B/L Number"
C_ARRIVAL = "반입일"
C_VESSEL = "모선명"
C_MAKER = "제조사"
C_CARGO = "화물관리번호"
C_NAME_KO = "한글 제품명(모델넘버)"
C_QTY = "입수"
C_CARTONS = "카톤 수"
C_NET = "순중량"
C_PRICE_USD = "가격(USD)"
C_CURRENCY = "CI 통화"
C_PRICE = "가격(수출국)"
C_MATERIAL = "재질 (재질 코드명으로 작성, 가나다 순으로 기재)"
C_RECORD = "실적접수번호 (승인일)"
C_NAME_EN = "영문 제품명"
C_SPEC = "재질 구분 (깊이·용량·용도)"
C_APPROVAL = "승인번호"
C_NOTE = "비고"
NOTE_MARK = "⚠️"
ATTENTION_FLAGS: tuple[Flag, ...] = ("mismatch", "need_check", "need_input")


class HistoryRow(BaseModel):
    row_id: str
    shipper_id: str
    declaration_id: str | None = None
    is_part: bool = False  # 부분품
    parent_row_id: str | None = None
    model: str = ""  # 모델 코드(이력 조회·같은 행 판정 키). 26칸에는 없는 내부 칸
    part_lines: list[str] = PField(default_factory=list)  # 합친 부분품 원래 줄(모델·품명)
    status: RowStatus = "자료 추가 필요"
    source_doc_ids: list[str] = PField(default_factory=list)
    cells: dict[str, Field] = PField(default_factory=dict)  # 키 = COLUMNS의 열 이름
    # 확인함(RULES 11-9): 켜면 확인 필요·불일치 경고를 해제. 자료 추가 필요는 그대로. 다시 누르면 취소
    confirmed: bool = False
    pending: bool = False  # 판독 중(DESIGN 3-1-1 "판독 중…")

    @property
    def locked(self) -> bool:
        """승인번호가 있으면 그 행은 수정 금지 (AGENTS 5-5 25번)."""
        cell = self.cells.get(C_APPROVAL)
        return bool(cell and cell.value)

    def val(self, col: str) -> Any:
        cell = self.cells.get(col)
        return cell.value if cell else None

    def text(self, col: str) -> str:
        v = self.val(col)
        return "" if v is None else str(v)

    def set_ai(
        self,
        col: str,
        value: Any,
        evidence: list[Evidence] | None = None,
        flag: Flag = "ok",
        memo: str = "",
    ) -> None:
        """프로그램 값 쓰기. final_value(사람 값)는 건드리지 않는다(AGENTS 0-5)."""
        cell = self.cells.setdefault(col, Field())
        cell.ai_value = value
        cell.evidence = evidence or []
        if cell.final_value is not None:
            # 사람 값이 프로그램(서류) 값과 다를 때만 주황(edited). 비교할 값이 없으면 ok
            same = value is None or str(cell.final_value) == str(value)
            cell.flag = "ok" if same else "edited"
        else:
            cell.flag = flag
            cell.memo = memo

    def set_note(self, tag: str, text: str | None) -> None:
        """비고: `⚠️ 태그: 내용` 한 줄씩. 같은 태그는 교체, text가 None이면 지움(RULES 11-2)."""
        cell = self.cells.setdefault(C_NOTE, Field())
        lines = [ln for ln in str(cell.ai_value or "").splitlines() if ln.strip()]
        lines = [ln for ln in lines if not ln.startswith(f"{NOTE_MARK} {tag}:")]
        if text:
            lines.append(f"{NOTE_MARK} {tag}: {text}")
        cell.ai_value = "\n".join(lines) or None

    def attention_flags(self) -> list[Flag]:
        """경고로 셀 flag 목록. 확인함이면 need_input만 남는다."""
        flags = [c.flag for c in self.cells.values() if c.flag in ATTENTION_FLAGS]
        return [f for f in flags if f == "need_input"] if self.confirmed else flags

    def needs_attention(self) -> bool:
        return not self.locked and bool(self.attention_flags())

    def refresh_status(self) -> None:
        flags = self.attention_flags()
        if self.locked:
            self.status = "승인"
        elif "need_input" in flags:
            self.status = "자료 추가 필요"
        elif flags:
            self.status = "확인 필요"
        else:
            self.status = "신청 전"
