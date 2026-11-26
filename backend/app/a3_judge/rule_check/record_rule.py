"""실적 칸 규칙 검사 — 값은 바꾸지 않고 문제만 돌려준다. 순수 함수. 담당: LSY [재사용] A3-2 (기존 rule_check.py)

담당자가 실적을 직접 고르면(final_value) 그 실적이 이 행에 쓸 수 있는지 확인한다(RULES 11-8):
등록된 실적인지, 같은 공장인지, 재질을 모두 포함하는지, 신고 기준일에 유효한지.
"""

from datetime import date

from app.a2_registry.records.service import expires_on, is_expired, parse_record_cell, to_date
from app.a3_judge.record_pick.eligibility import covers_product, factory_match
from app.core.schema.record import Record


def check_record(
    cell: str,
    materials: list[str],
    factory_code: str,
    factory_address: str,
    name_ko: str,
    records: list[Record],
    on: date,
) -> list[str]:
    no, _ = parse_record_cell(cell or "")
    if not no:
        return []
    rec = next((r for r in records if r.record_no == no), None)
    if rec is None:
        return [f"등록된 실적이 아님({no}) — 실적 탭에서 확인"] if records else []
    out: list[str] = []
    if (factory_code or factory_address) and not factory_match(rec, factory_code, factory_address):
        out.append(f"다른 공장의 실적({rec.factory_code or '코드 없음'})")
    missing = sorted(set(materials) - set(rec.materials))
    if missing:
        out.append(f"실적에 없는 재질: {', '.join(missing)}")
    if not covers_product(name_ko, rec):
        out.append("다른 품명의 실적")
    approved = to_date(rec.approved_on)
    if approved and is_expired(approved, on):
        out.append(f"만료된 실적({expires_on(approved):%Y.%m.%d})")
    return out
