"""부분품 줄 기록 — 합친 부분품 행이 어떤 부품들로 이뤄졌는지. 순수 함수. 담당: LSY [재사용] A3-1 (기존 spare_parts)

본품 1행으로 합치면(merge.py) 부품번호·품명·수량이 행에서 사라진다. 검수·품목사항 확인 때 되돌아볼 수 있게
B/L(=한 번의 합치기)마다 원래 줄을 같은 형식으로 남긴다. 저장은 행의 part_lines(글자 목록).
"""

from pydantic import BaseModel

from app.core.schema.document import DocumentLine


class PartLine(BaseModel):
    part_no: str = ""
    description: str = ""
    quantity: float | None = None  # PCS 합계
    cartons: float | None = None
    amount: float | None = None


def collect_parts(lines: list[DocumentLine]) -> list[PartLine]:
    return [
        PartLine(
            part_no=ln.model.strip(),
            description=ln.description.strip(),
            quantity=ln.pcs(),
            cartons=ln.cartons,
            amount=ln.amount,
        )
        for ln in lines
        if ln.is_part
    ]


def _n(v: float | None) -> str:
    return "?" if v is None else f"{v:g}"


def format_part_line(p: PartLine) -> str:
    """'RC-100-IP INNER POT (SPARE PART) — 20 PCS, 2 CTNS'. 모르는 수는 '?'."""
    head = " ".join(x for x in (p.part_no, p.description) if x)
    return f"{head} — {_n(p.quantity)} PCS, {_n(p.cartons)} CTNS".strip()
