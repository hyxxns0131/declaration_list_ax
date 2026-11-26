"""뚜껑 등 부품별 실적 분리(split_record_by_part). 순수 함수. 담당: LSY [신규] (로직 점검 반영 11/25)

설정을 켜면: 한 실적이 제품 재질을 모두 포함하지 못할 때, 본체 실적 + 부품 실적(검체 부위가 '뚜껑' 등으로
기록된 실적)으로 나눠 쓴다. 칸 값은 '본체번호 (승인일) / 뚜껑: 부품번호 (승인일)'.
끄면(기본) 한 실적이 재질을 모두 포함해야 하고, 없으면 정밀검사 대상(rank.choose_record 그대로).
최소 구현: 부품 실적은 실적의 검체(sample_parts) 부위 이름으로만 알아본다 — 부위 기록이 없으면 나누지 않는다.
"""

from datetime import date

from app.a2_registry.records.service import format_record_cell, is_expired, to_date
from app.a3_judge.record_pick.eligibility import covers_product, factory_match
from app.a3_judge.record_pick.rank import RecordChoice
from app.core.schema.record import Record

BODY_WORDS = {"", "본체", "몸체", "몸통", "BODY", "전체"}


def part_label(rec: Record) -> str:
    """실적 검체 부위 중 본체가 아닌 첫 이름(예: 뚜껑). 없으면 ''."""
    for s in rec.sample_parts:
        p = s.part.strip()
        if p.upper() not in BODY_WORDS:
            return p
    return ""


def _usable(rec: Record, code: str, address: str, name_ko: str, on: date) -> bool:
    approved = to_date(rec.approved_on)
    return bool(
        approved
        and not is_expired(approved, on)
        and factory_match(rec, code, address)
        and covers_product(name_ko, rec)
    )


def choose_split(
    records: list[Record],
    materials: list[str],
    factory_code: str,
    factory_address: str,
    name_ko: str,
    on: date,
) -> RecordChoice | None:
    """본체 + 부품 실적으로 재질을 모두 덮으면 그 선택, 못 덮으면 None."""
    mats = set(materials)
    if not mats:
        return None
    pool = [r for r in records if _usable(r, factory_code, factory_address, name_ko, on)]
    bodies = [r for r in pool if not part_label(r) and mats & set(r.materials)]
    if not bodies:
        return None
    body = max(bodies, key=lambda r: (len(mats & set(r.materials)), r.approved_on or ""))
    rest = mats - set(body.materials)
    if not rest:
        return None  # 본체 실적 하나로 충분 — 나눌 필요 없음
    parts = [r for r in pool if part_label(r) and rest <= set(r.materials)]
    if not parts:
        return None
    part = max(parts, key=lambda r: r.approved_on or "")
    label = part_label(part)
    body_cell = format_record_cell(body.record_no, body.approved_on)
    part_cell = format_record_cell(part.record_no, part.approved_on)
    return RecordChoice(
        value=f"{body_cell} / {label}: {part_cell}",
        record_no=body.record_no,
        note=(
            f"부품별 실적 분리(split_record_by_part): 본체 {body.record_no}, "
            f"{label} {part.record_no} (재질 {', '.join(sorted(rest))})"
        ),
    )
