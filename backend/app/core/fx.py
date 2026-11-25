"""관세환율 조회·캐시, 가격(USD) 계산. 담당: KHS [재사용] A1-7 (기존 unipass_client.query_customs_fx)

- 가격(USD) = 가격(수출국) × CI 통화 환율 ÷ USD 환율, **신고일이 속한 주의 관세환율**(RULES 11-2).
  신고일이 아직 없으면 오늘 기준 주의 환율로 계산하고 근거에 적는다.
- 엔화는 관세청 API가 1엔 단위로 준다(RULES 11-2). 단위 표기(mtryUtNm)에 100이 있을 때만 100으로 나눈다.
- 조회 순서: 로컬 캐시 → 유니패스 관세환율 API(live) → samples/unipass/fx.json(가상) → 없음.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import httpx

from app.core.config import REPO_ROOT, get_settings
from app.core.storage import work_db_more as store

FX_URL = "https://unipass.customs.go.kr:38010/ext/rest/trifFxrtInfoQry/retrieveTrifFxrtInfo"
IMPORT = "2"  # imexTp: 1=수출, 2=수입
MOCK_FILE = REPO_ROOT / "samples" / "unipass" / "fx.json"

Rates = dict[str, dict]  # {"USD": {"rate": 1380.5, "unit": 1, "from": "2026-11-23"}}


def week_start(d: date) -> date:
    """관세환율은 주 단위(일요일 시작) 고시 — 기존 도구는 조회일을 그대로 넘겼다. 캐시 키만 주 단위로."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def to_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 8:
        return None
    try:
        return datetime.strptime(digits[:8], "%Y%m%d").date()
    except ValueError:
        return None


def parse_rates(xml_bytes: bytes) -> Rates:
    root = ET.fromstring(xml_bytes)
    rates: Rates = {}
    for el in root.iter():
        cur, fx = el.findtext("currSgn"), el.findtext("fxrt")
        if not cur or not fx:
            continue
        unit = 100 if "100" in (el.findtext("mtryUtNm") or "") else 1
        try:
            rates[cur.strip().upper()] = {
                "rate": float(fx.replace(",", "")),
                "unit": unit,
                "from": (el.findtext("aplyBgnDt") or "").strip(),
            }
        except ValueError:
            continue
    return rates


def _live(d: date) -> Rates:
    key = get_settings().unipass_fxrt_api_key
    if not key or get_settings().unipass_mode != "live":
        return {}
    try:
        r = httpx.get(
            FX_URL,
            params={"crkyCn": key, "qryYymmDd": d.strftime("%Y%m%d"), "imexTp": IMPORT},
            timeout=get_settings().unipass_timeout_sec,
        )
        r.raise_for_status()
        return parse_rates(r.content)
    except (httpx.HTTPError, ET.ParseError):
        return {}


def _mock() -> Rates:
    if not MOCK_FILE.exists():
        return {}
    return json.loads(MOCK_FILE.read_text(encoding="utf-8"))


def get_rates(on: date | None = None) -> tuple[Rates, str]:
    """(환율표, 출처 'live'·'cache'·'mock'·''). 못 구하면 ({}, '')."""
    d = on or date.today()
    wk = week_start(d).strftime("%Y%m%d")
    hit = store.fx_get(wk)
    if hit:
        return hit, "cache"
    rates = _live(d)
    if rates:
        store.fx_put(wk, rates)
        return rates, "live"
    rates = _mock()
    return (rates, "mock") if rates else ({}, "")


def convert_to_usd(amount: float | None, currency: str, rates: Rates) -> tuple[float | None, str]:
    """원화 경유: amount × (통화 환율/단위) ÷ USD 환율. 순수 함수. (USD 금액 또는 None, 이유)"""
    if amount is None or not currency:
        return None, "금액·통화 없음"
    cur = currency.upper()
    if cur == "USD":
        return round(amount, 2), ""
    if cur not in rates or "USD" not in rates:
        return None, f"환율 없음 ({cur} 또는 USD)"
    krw = amount * rates[cur]["rate"] / rates[cur]["unit"]
    return round(krw / rates["USD"]["rate"], 2), ""
