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
from app.a3_judge.record_pick import no_record
from app.a3_judge.record_pick.eligibility import covers_materials, covers_product, factory_match
from app.core.schema.record import Record


class RecordChoice(BaseModel):
    value: str | None = None  # 칸 값 '번호 (승인일)'
    record_no: str = ""
    note: str = ""  # 비고 '⚠️ 실적:' 내용 또는 근거
    need_check: bool = False
    precise_needed: bool = False  # 정밀검사 대상
    candidates: list[dict] = PField(default_factory=list)  # 화면 후보(만료 포함, 만료는 취소선)
    basis_date: str = ""  # 유효기간을 비교한 기준일(신고일, 없으면 오늘) — 화면에 "○월 ○일 기준"


def _color_ok(rec: Record, color: str) -> bool | None:
    """None = 비교 불가(검체 색 기록 없음 또는 현품 색 없음)."""
    if not color:
        return None
    colors = {s.color.strip() for s in rec.sample_parts if s.color.strip()}
    if not colors:
        return None
    return color.strip() in colors


def _reason(
    checks: dict[str, bool], materials: list[str], rec: Record, approved: date | None, on: date
) -> str:
    """빠진 검사를 사람이 읽을 이유로. 모두 통과하면 빈 글자."""
    out: list[str] = []
    if not checks["공장"]:
        out.append("다른 공장(업소코드·주소 모두 다름)")
    if not checks["품명"]:
        out.append("다른 품명")
    if not checks["재질"]:
        missing = sorted(set(materials) - set(rec.materials))
        out.append(f"재질 부족: {', '.join(missing)} 없음" if missing else "재질이 정해지지 않음")
    if not checks["재질 구분"]:
        out.append(f"재질 구분 다름({rec.spec_class})")
    if not checks["기간"]:
        out.append(
            f"만료 ({expires_on(approved):%Y.%m.%d}) (기준일 {on:%Y.%m.%d})"
            if approved
            else "승인일 없음"
        )
    return " / ".join(out)


def _mark(out: RecordChoice) -> None:
    """고른 실적은 '선택', 검사에 빠진 실적은 '제외', 나머지(쓸 수 있지만 덜 포괄적)는 '후보'."""
    for c in out.candidates:
        if out.record_no and c["record_no"] == out.record_no:
            c["status"], c["reason"] = "선택", "재질을 가장 많이 포함 (같으면 최신 승인일)"
        elif c["reason"]:
            c["status"] = "제외"


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
    out = RecordChoice(basis_date=on.isoformat())
    pool: list[tuple[Record, str]] = []
    for r in records:
        how = factory_match(r, factory_code, factory_address)
        approved = to_date(r.approved_on)
        expired = bool(approved and is_expired(approved, on))
        mats_ok = covers_materials(materials, r)
        name_ok = covers_product(name_ko, r)
        fits = bool(how) and mats_ok and name_ok
        spec_ok = not (same_spec and spec and r.spec_class and r.spec_class != spec)
        checks = {
            "공장": bool(how),
            "품명": name_ok,
            "재질": mats_ok,
            "재질 구분": spec_ok,
            "기간": bool(approved) and not expired,
        }
        color_bad = color_check and _color_ok(r, color) is False
        if color_check:
            checks["색상"] = not color_bad
        reason = _reason(checks, materials, r, approved, on)
        if color_bad:
            sample = ", ".join(sorted({s.color.strip() for s in r.sample_parts if s.color.strip()}))
            reason = " / ".join(
                x for x in (reason, f"색상 다름(검체 {sample}, 현품 {color.strip()})") if x
            )
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
                # 근거 패널용: 검사별 통과 여부·빠진 재질·제외 이유 (11/26 [개선])
                "checks": checks,
                "missing_materials": sorted(set(materials) - set(r.materials)),
                "status": "후보",
                "reason": reason,
            }
        )
        if fits and not expired and approved:
            pool.append((r, how or ""))

    if not materials:
        out.need_check, out.note = True, "재질이 정해지지 않아 실적을 고르지 않음"
        _mark(out)
        return out
    if not factory_code and not factory_address:
        out.need_check, out.note = True, "해외제조업소가 정해지지 않아 실적을 고르지 않음"
        _mark(out)
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
            out.note = no_record.spec_mismatch(notes)
            _mark(out)
            return out
        pool = kept

    if not pool:
        expired_fit = [c for c in out.candidates if c["fits"] and c["expired"]]
        out.precise_needed, out.need_check = True, True
        if expired_fit:
            last = max(expired_fit, key=lambda c: c["approved_on"] or "")
            out.note = no_record.expired(
                last["record_no"], (last["expires_on"] or "").replace("-", ".")
            )
        else:
            out.note = no_record.no_valid_record(factory_code)
        _mark(out)
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
            out.note = no_record.color_mismatch(best.record_no, color)
            _mark(out)
            return out

    out.record_no = best.record_no
    out.value = format_record_cell(best.record_no, best.approved_on)
    _mark(out)
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
