"""가격(USD) = 가격(수출국) × CI 통화 환율 ÷ USD 환율. 담당: KHS [재사용] A1-7 (기존 fill_new_columns)

- 신고일(검역 신고일자)이 속한 주의 관세환율. 신고일이 없으면 오늘 기준(근거에 적는다)(RULES 11-2).
- 가격(USD)은 계산 칸: 직접 입력 금지(PATCH에서 거절).
- 환율을 못 구하면 칸을 비우고 '확인 필요: 관세환율 조회 실패'.
"""

from datetime import date

from app.core import fx
from app.core.schema.fields import Evidence
from app.core.schema.history import C_CURRENCY, C_PRICE, C_PRICE_USD, HistoryRow

C_USD_RATE = "USD 환율"
C_CUR_RATE = "CI 통화 환율"
C_DECL_DATE = "검역 신고일자"


def apply_price(
    row: HistoryRow, rates: fx.Rates, source: str, basis: date, basis_label: str
) -> None:
    """순수 함수: 환율표로 행의 환율·가격(USD) 칸을 채운다."""
    amount = row.val(C_PRICE)
    try:
        amount_f = float(str(amount).replace(",", "")) if amount not in (None, "") else None
    except ValueError:
        amount_f = None
    cur = (row.text(C_CURRENCY) or "").upper()
    if amount_f is None or not cur:
        return
    note = f"관세환율 {basis:%Y.%m.%d} 주({basis_label}, {source or '없음'})"
    ev = [Evidence(source="FX", ref=basis.isoformat(), note=note)]
    usd = rates.get("USD")
    if usd:
        row.set_ai(C_USD_RATE, usd["rate"], ev)
    if cur in rates:
        row.set_ai(C_CUR_RATE, rates[cur]["rate"] / rates[cur]["unit"], ev)
    elif cur == "USD":
        row.set_ai(C_CUR_RATE, usd["rate"] if usd else None, ev)
    value, why = fx.convert_to_usd(amount_f, cur, rates)
    if value is None and cur == "USD":
        value, why = round(amount_f, 2), ""
    if value is None:
        row.set_ai(
            C_PRICE_USD,
            None,
            ev,
            flag="need_check",
            memo=f"확인 필요: {why or '관세환율 조회 실패'}",
        )
        return
    formula = f"{amount_f:g} × {cur} 환율 ÷ USD 환율" if cur != "USD" else "CI 통화가 USD라 그대로"
    row.set_ai(
        C_PRICE_USD,
        value,
        [Evidence(source="FX", ref=basis.isoformat(), note=f"{formula} — {note}")],
    )


def basis_date(row: HistoryRow) -> tuple[date, str]:
    d = fx.to_date(row.val(C_DECL_DATE))
    return (d, "신고일") if d else (date.today(), "신고일 없음: 오늘 기준")


def fill_prices(rows: list[HistoryRow]) -> None:
    """행마다 기준 주의 환율을 구해 채운다(같은 주는 캐시)."""
    cache: dict[str, tuple[fx.Rates, str]] = {}
    for row in rows:
        if row.locked:
            continue
        d, label = basis_date(row)
        key = fx.week_start(d).isoformat()
        if key not in cache:
            cache[key] = fx.get_rates(d)
        rates, src = cache[key]
        apply_price(row, rates, src, d, label)
