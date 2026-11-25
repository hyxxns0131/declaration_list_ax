"""해외제조업소 코드 갱신 관리. 담당: YHS [신규] A2-5

제안서 2번, HS 결정 11/25로 범위에 다시 넣음(RULES 11-8-1).
- 만료일 = 등록(갱신)일 + FACTORY_CODE_VALID_YEARS(기본 2년).
  근거: 수입식품안전관리 특별법 시행규칙(해외제조업소 등록 유효기간) — 최신본 확인 필요.
- 등록일을 모르면 만료일을 추측하지 않고 "확인 필요"로 둔다.
- 코드 목록은 등록된 실적·제품(수입신고서·성적서)의 제조업소 코드와 samples/mfds/factories.json(가상)에서 모은다.
  이미 저장된 등록일(담당자 입력)은 덮어쓰지 않는다.

공개 함수(다른 영역·alerts는 이것만): expires_on, status_for, list_factories, update_registered_on
"""

import json
from datetime import date

from app.a2_registry.factory_codes.models import FactoryCode, FactoryStatus
from app.a2_registry.records.service import to_date
from app.core.config import REPO_ROOT, get_settings
from app.core.errors import AppError
from app.core.storage import work_db_more as store

SAMPLE_FILE = REPO_ROOT / "samples" / "mfds" / "factories.json"


def expires_on(registered_on: date, years: int | None = None) -> date:
    """등록(갱신)일 + 설정 년수. 2월 29일은 28일로."""
    y = years if years is not None else get_settings().factory_code_valid_years
    try:
        return registered_on.replace(year=registered_on.year + y)
    except ValueError:
        return registered_on.replace(year=registered_on.year + y, day=28)


def status_for(
    registered_on: date | None, today: date, stages: list[int], years: int | None = None
) -> tuple[FactoryStatus, date | None, int | None]:
    """(상태, 만료일, 남은 날). 순수 함수. 만료일 당일까지는 유효."""
    if registered_on is None:
        return "확인 필요", None, None
    exp = expires_on(registered_on, years)
    days = (exp - today).days
    if days < 0:
        return "만료", exp, days
    if stages and days <= max(stages):
        return "만료 임박", exp, days
    return "유효", exp, days


def _discovered() -> dict[str, dict]:
    """등록 데이터·가상 샘플에서 코드 모으기. code → {name, address, source}"""
    found: dict[str, dict] = {}

    def add(code: str, name: str, address: str, source: str) -> None:
        code = (code or "").strip().upper()
        if not code:
            return
        cur = found.setdefault(code, {"name": "", "address": "", "source": source})
        cur["name"] = cur["name"] or (name or "")
        cur["address"] = cur["address"] or (address or "")

    for rec, _ in store.list_records():
        add(rec.factory_code, rec.factory_name, rec.factory_address, "실적")
    for p in store.list_products():
        add(
            p.get("maker_code", ""),
            p.get("maker_name", ""),
            p.get("maker_address", ""),
            "제품 등록",
        )
    if SAMPLE_FILE.exists():
        for f in json.loads(SAMPLE_FILE.read_text(encoding="utf-8")):
            add(f.get("code", ""), f.get("name", ""), f.get("address", ""), "samples(가상)")
    return found


def sync() -> None:
    """새로 보인 코드를 표에 넣는다. 저장된 등록일·이름은 그대로 둔다."""
    for code, info in _discovered().items():
        if store.get_factory(code):
            continue
        store.save_factory(
            {"code": code, **info, "registered_on": None, "expires_on": None, "status": "확인 필요"}
        )


def _to_model(row: dict, today: date, stages: list[int]) -> FactoryCode:
    reg = to_date(row.get("registered_on"))
    status, exp, days = status_for(reg, today, stages)
    return FactoryCode(
        code=row["code"],
        name=row.get("name") or "",
        address=row.get("address") or "",
        registered_on=reg.isoformat() if reg else None,
        expires_on=exp.isoformat() if exp else None,
        days_left=days,
        status=status,
        source=row.get("source") or "",
    )


def list_factories(within_days: int | None = None, today: date | None = None) -> list[FactoryCode]:
    """전체 목록. within_days를 주면 그 안에 만료되는 코드만(이미 만료·확인 필요 제외)."""
    sync()
    today = today or date.today()
    stages = get_settings().alert_days
    out = [_to_model(r, today, stages) for r in store.list_factories()]
    if within_days is not None:
        out = [f for f in out if f.days_left is not None and 0 <= f.days_left <= within_days]
    order = {"만료": 0, "만료 임박": 1, "확인 필요": 2, "유효": 3}
    return sorted(
        out, key=lambda f: (order[f.status], f.days_left if f.days_left is not None else 0, f.code)
    )


def update_registered_on(
    code: str, registered_on: str | None, today: date | None = None
) -> FactoryCode:
    row = store.get_factory(code.upper())
    if not row:
        raise AppError("not_found", f"해외제조업소 코드 {code}이(가) 없습니다.", 404)
    reg = to_date(registered_on) if registered_on else None
    if registered_on and not reg:
        raise AppError("invalid_input", "등록일은 YYYY-MM-DD 형식으로 넣어 주세요.")
    today = today or date.today()
    model = _to_model(
        {**row, "registered_on": reg.isoformat() if reg else None}, today, get_settings().alert_days
    )
    store.save_factory(
        {
            **row,
            "registered_on": model.registered_on,
            "expires_on": model.expires_on,
            "status": model.status,
            "source": row.get("source") or "담당자",
        }
    )
    return model
