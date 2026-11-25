"""실적 고르기: 쓸 수 있는 유효 실적 중 재질을 가장 많이 포함한 것(같으면 최신). 순수 함수. 담당: LSY [재사용] A3-2

기존 precise.choose_approval (RULES 11-8)
- 후보 = 같은 공장 + 같은 품명 + 재질 모두 포함 + 신고 기준일에 유효(승인일 + 5년, 그날까지)
- 재질 구분(spec)이 다른 실적은 건너뛴다(same_record_same_spec). 실적 쪽 기록이 없으면 '같은 구분인지 확인 필요'.
- 색상(color_check): 시험성적서 검체 색이 현품 색과 다르면 그 실적을 쓰지 않는다. 사진 추정색은 쓰지 않는다.
- 없음 → 값 비움 + "이 공장(코드)에서 이 재질을 모두 포함하는 유효한 정밀검사 실적 없음 → 정밀검사 대상"
- 만료 판정은 A2 records 함수를 쓴다.
"""

from datetime import date

from pydantic import BaseModel
from pydantic import Field as PField

from app.a2_registry.records.service import expires_on, format_record_cell, is_expired, to_date
from app.a3_judge.record_pick.eligibility import covers_materials, covers_product, factory_match
from app.core.schema.record import Record


class RecordChoice(BaseModel):
    value: str | None = None  # 칸 값 '번호 (승인일)'
    record_no: str = ""
    note: str = ""  # 비고 '⚠️ 실적:' 내용 또는 근거
    need_check: bool = False
    precise_needed: bool = False  # 정밀검사 대상
    candidates: list[dict] = PField(default_factory=list)  # 화면 후보(만료 포함, 만료는 취소선)


def _color_ok(rec: Record, color: str) -> bool | None:
    """None = 비교 불가(검체 색 기록 없음 또는 현품 색 없음)."""
    if not color:
        return None
    colors = {s.color.strip() for s in rec.sample_parts if s.color.strip()}
    if not colors:
        return None
    return color.strip() in colors


def choose_record(
    records: list[Record],
    materials: list[str],
    factory_code: str,
    factory_address: str,
    name_ko: str,
    on: date,
    spec: str = "",
    same_spec: bool = True,
    color: str = "",
    color_check: bool = False,
) -> RecordChoice:
    out = RecordChoice()
    pool: list[tuple[Record, str]] = []
    for r in records:
        how = factory_match(r, factory_code, factory_address)
        approved = to_date(r.approved_on)
        expired = bool(approved and is_expired(approved, on))
        fits = bool(how) and covers_materials(materials, r) and covers_product(name_ko, r)
        out.candidates.append(
            {
                "record_no": r.record_no,
                "value": format_record_cell(r.record_no, r.approved_on),
                "materials": r.materials,
                "factory_code": r.factory_code,
                "approved_on": r.approved_on,
                "expires_on": expires_on(approved).isoformat() if approved else None,
                "expired": expired,
                "fits": fits,
            }
        )
        if fits and not expired and approved:
            pool.append((r, how or ""))

    if not materials:
        out.need_check, out.note = True, "재질이 정해지지 않아 실적을 고르지 않음"
        return out
    if not factory_code and not factory_address:
        out.need_check, out.note = True, "해외제조업소가 정해지지 않아 실적을 고르지 않음"
        return out

    notes: list[str] = []
    if same_spec and spec:
        kept = [(r, h) for r, h in pool if not r.spec_class or r.spec_class == spec]
        skipped = [r.record_no for r, _ in pool if r.spec_class and r.spec_class != spec]
        if skipped:
            notes.append(f"재질 구분이 달라 건너뛴 실적: {', '.join(skipped)}")
        if any(not r.spec_class for r, _ in kept):
            notes.append("실적 쪽 재질 구분 기록 없음 → 같은 구분인지 확인 필요")
        if pool and not kept:
            out.precise_needed, out.need_check = True, True
            out.note = " / ".join(notes) + " → 같은 재질 구분의 유효한 실적 없음 → 정밀검사 대상"
            return out
        pool = kept

    if not pool:
        expired_fit = [c for c in out.candidates if c["fits"] and c["expired"]]
        out.precise_needed, out.need_check = True, True
        if expired_fit:
            last = max(expired_fit, key=lambda c: c["approved_on"] or "")
            out.note = (
                f"실적 만료 ({last['record_no']}, {(last['expires_on'] or '').replace('-', '.')}) "
                "→ 정밀검사 신청 대상"
            )
        else:
            who = factory_code or "주소 기준"
            out.note = f"이 공장({who})에서 이 재질을 모두 포함하는 유효한 정밀검사 실적 없음 → 정밀검사 대상"
        return out

    ordered = sorted(
        pool, key=lambda x: (len(x[0].materials), x[0].approved_on or ""), reverse=True
    )
    best, how = ordered[0]
    if color_check:
        fails = []
        chosen = None
        for r, h in ordered:
            ok = _color_ok(r, color)
            if ok is not False:
                chosen = (r, h)
                if ok is None:
                    notes.append("색상 확인 필요(검체 색 또는 현품 색 기록 없음)")
                break
            fails.append(r.record_no)
        if chosen:
            best, how = chosen
            if fails:
                notes.append(f"색상이 안 맞아 건너뛴 실적: {', '.join(fails)}")
        else:
            out.precise_needed, out.need_check = True, True
            out.note = f"{best.record_no}실적과 현품({color})의 색상이 달라 추가 정밀검사 필요"
            return out

    out.record_no = best.record_no
    out.value = format_record_cell(best.record_no, best.approved_on)
    head = f"모델 재질을 모두 포함하는 가장 포괄적인 실적 ({best.record_no}, 재질 {len(best.materials)}개)"
    if how == "주소":
        notes.append("해외제조업소 코드는 다르지만 주소가 같아 같은 공장으로 봄 - 코드 갱신 추정")
        out.need_check = True
    out.note = " / ".join([head, *notes])
    if any("확인 필요" in n for n in notes):
        out.need_check = True
    return out


def expiry_warning(record: Record, on: date, warn_days: int) -> str:
    approved = to_date(record.approved_on)
    if not approved:
        return ""
    days = (expires_on(approved) - on).days
    if 0 <= days <= warn_days:
        return f"실적 5년 만료 {days}일 전 (만료일 {expires_on(approved):%Y.%m.%d})"
    return ""
