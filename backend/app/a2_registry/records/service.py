"""실적 유효기간·만료 판정, 실적 조회·수정. 담당: YHS [개선] A2-2

정밀검사 실적 유효기간: 승인일 + 5년, 그날까지 사용 가능
(SAMC 실무 규칙, 기존 도구 MAINTENANCE.md 8장 2026-11-05 확정)
근거 법령: 수입식품안전관리 특별법 시행규칙 — 해당 조항 최신본 확인 필요
연수는 설정값(RECORD_VALID_YEARS)을 쓴다. 만료 실적은 지우지 않고 status=만료로 남긴다(RULES 11-8).

공개 함수(다른 영역은 이것만): parse_record_cell, format_record_cell, expires_on, is_expired,
record_status, list_records, get_record, update_record, valid_records
"""

import re
from datetime import date

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schema.history import HistoryRow
from app.core.schema.record import Record, RecordStatus, RecordUse
from app.core.storage import work_db_more as store

ACTIVE = "사용 가능"
RECORD_RE = re.compile(r"(?P<no>\d{6,})\s*(?:\((?P<date>\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})\))?")
EDITABLE = {
    "factory_code",
    "factory_name",
    "factory_address",
    "materials",
    "spec_class",
    "applied_on",
    "approved_on",
    "products",
    "product_names",
    "memo",
}


def parse_record_cell(value: str) -> tuple[str, date | None]:
    """'202300233982 (2023.04.25)' → ('202300233982', date(2023,4,25))"""
    m = RECORD_RE.search(value or "")
    if not m:
        return "", None
    d = None
    if m["date"]:
        y, mo, dd = (int(x) for x in re.split(r"[.\-/]", m["date"]))
        d = date(y, mo, dd)
    return m["no"], d


def to_date(value: str | None) -> date | None:
    m = re.match(r"(\d{4})[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})", value or "")
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def format_record_cell(record_no: str, approved_on: str | None) -> str:
    """칸 값 형식: `202300233982 (2023.04.25)` (RULES 11-8)."""
    d = to_date(approved_on)
    return f"{record_no} ({d:%Y.%m.%d})" if d else record_no


def expires_on(approved_on: date, years: int | None = None) -> date:
    y = years if years is not None else get_settings().record_valid_years
    try:
        return approved_on.replace(year=approved_on.year + y)
    except ValueError:  # 2월 29일
        return approved_on.replace(year=approved_on.year + y, day=28)


def is_expired(approved_on: date, today: date | None = None, years: int | None = None) -> bool:
    """만료일 당일까지는 유효(RULES 11-8)."""
    return (today or date.today()) > expires_on(approved_on, years)


def record_status(rec: Record, today: date | None = None) -> RecordStatus:
    """승인일이 없으면 '유효'(승인일 확인 필요는 memo로). 만료 임박 = 가장 이른 알림 단계 안."""
    approved = to_date(rec.approved_on)
    if not approved:
        return "유효"
    today = today or date.today()
    if is_expired(approved, today):
        return "만료"
    days = (expires_on(approved) - today).days
    stages = get_settings().alert_days
    return "만료 임박" if stages and days <= max(stages) else "유효"


def refresh(rec: Record, today: date | None = None) -> Record:
    approved = to_date(rec.approved_on)
    rec.expires_on = expires_on(approved).isoformat() if approved else None
    rec.status = record_status(rec, today)
    return rec


def list_records(
    shipper_id: str | None = None,
    maker: str = "",
    model: str = "",
    status: str = "",
    today: date | None = None,
) -> list[Record]:
    out: list[Record] = []
    for rec, _sid in store.list_records(shipper_id):
        rec = refresh(rec, today)
        if maker and maker.lower() not in f"{rec.factory_name} {rec.factory_code}".lower():
            continue
        if model and not any(model.upper() in p.upper() for p in rec.products):
            continue
        if status == ACTIVE:  # 사용 가능 = 유효 + 만료 임박
            if rec.status == "만료":
                continue
        elif status and rec.status != status:
            continue
        out.append(rec)
    return out


def valid_records(shipper_id: str, today: date | None = None) -> list[Record]:
    """실적 고르기 후보(A3-2): 만료 제외 전부(만료 판정은 고르는 쪽이 신고일 기준으로 다시 한다)."""
    return [r for r in list_records(shipper_id, today=today)]


def get_record(record_no: str) -> Record:
    got = store.get_record(record_no)
    if not got:
        raise AppError("not_found", f"실적 {record_no}이(가) 없습니다.", 404)
    return refresh(got[0])


def update_record(record_no: str, changes: dict) -> Record:
    got = store.get_record(record_no)
    if not got:
        raise AppError("not_found", f"실적 {record_no}이(가) 없습니다.", 404)
    rec, sid = got
    bad = set(changes) - EDITABLE
    if bad:
        raise AppError("invalid_input", f"고칠 수 없는 칸: {', '.join(sorted(bad))}")
    rec = rec.model_copy(update=changes)
    rec = refresh(rec)
    store.save_record(rec, sid)
    return rec


def save(rec: Record, shipper_id: str) -> Record:
    rec = refresh(rec)
    store.save_record(rec, shipper_id)
    return rec


def attach_uses(recs: list[Record], rows: list[HistoryRow]) -> list[Record]:
    """서류검사 내역: 검역이력에서 이 실적번호를 쓴 행(RULES 11-8). 정밀검사 신고 모델이면 '정밀'. 순수 함수."""
    by_no: dict[str, list[HistoryRow]] = {}
    for r in rows:
        no, _ = parse_record_cell(r.text("실적접수번호 (승인일)"))
        if no:
            by_no.setdefault(no, []).append(r)
    for rec in recs:
        rec.uses = [
            RecordUse(
                bl_no=r.text("B/L Number"),
                model=r.model + (" 부분품" if r.is_part else ""),
                kind="정밀"
                if (r.model.upper() in (p.upper() for p in rec.products) and not r.is_part)
                else "서류",
                row_id=r.row_id,
            )
            for r in by_no.get(rec.record_no, [])
        ]
    return recs
