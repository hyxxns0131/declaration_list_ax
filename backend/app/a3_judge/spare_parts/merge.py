"""부분품 줄을 B/L마다 본품 모델 1행으로 합치기(merge_spare_parts). 순수 함수. 담당: LSY [재사용]

RULES 11-6 부분품:
- 수량·카톤·순중량·금액은 합계
- 이름 모델: ① 부분품 모델 = 같은 B/L 본품 모델 → ② (컨테이너 정보가 있을 때) 본품 수량이 적은 컨테이너
  → ③ 본품 중 카톤 수가 가장 적은 모델 + "확인 필요"
  ①에는 부분품 코드가 '본품코드-…'로 시작하는 경우도 넣는다(제안, 기존 도구와 같은지 확인 필요).
  ②는 컨테이너 정보를 아직 읽지 않으므로 건너뛴다.
"""

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.schema.document import DocumentLine


class MergedParts(BaseModel):
    line: DocumentLine
    name_model: str
    part_lines: list[str] = PField(default_factory=list)
    need_check: bool = False
    note: str = ""


def _sum(vals: list[float | None]) -> float | None:
    got = [v for v in vals if v is not None]
    return sum(got) if got else None


def choose_name_model(
    mains: list[DocumentLine], parts: list[DocumentLine]
) -> tuple[str, bool, str]:
    main_models = [m.model for m in mains if m.model]
    for p in parts:  # ① 같은 모델
        for mm in main_models:
            if p.model.strip().upper() == mm.strip().upper():
                return mm, False, "부분품 모델이 같은 B/L 본품 모델과 같음"
    for p in parts:  # ① 확장: 본품 코드로 시작
        for mm in sorted(main_models, key=len, reverse=True):
            if p.model.strip().upper().startswith(mm.strip().upper() + "-"):
                return mm, False, f"부분품 코드 {p.model}가 본품 {mm}로 시작"
    if mains:  # ③
        smallest = min(mains, key=lambda m: m.cartons or 0)
        return smallest.model, True, "본품 중 카톤 수가 가장 적은 모델로 정함 — 확인 필요"
    return (parts[0].model if parts else ""), True, "같은 B/L에 본품 없음 — 확인 필요"


def merge_spare_lines(lines: list[DocumentLine]) -> tuple[list[DocumentLine], MergedParts | None]:
    """(본품 줄, 합친 부분품 1행 또는 None)"""
    mains = [ln for ln in lines if not ln.is_part]
    parts = [ln for ln in lines if ln.is_part]
    if not parts:
        return lines, None
    model, need_check, note = choose_name_model(mains, parts)
    merged = DocumentLine(
        model=model,
        description=f"SPARE PARTS FOR {model}".strip(),
        qty_per_carton=None,  # 여러 부품을 합쳐 입수는 정하지 않는다
        cartons=_sum([p.cartons for p in parts]),
        net_kg=_sum([p.net_kg for p in parts]),
        amount=_sum([p.amount for p in parts]),
        is_part=True,
    )
    part_lines = [f"{p.model} {p.description} ({p.cartons or 0:g} CTNS)".strip() for p in parts]
    return mains, MergedParts(
        line=merged, name_model=model, part_lines=part_lines, need_check=need_check, note=note
    )
