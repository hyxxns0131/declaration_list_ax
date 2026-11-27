"""유니패스 반입 상태·반입일·반입지·입항일 갱신. 담당: KHS [재사용] A1-6 (기존 progress.py)

- 반입일 칸에는 최종 반입 날짜만(중간 위치는 쓰지 않음). 반입 전이면 빈칸(RULES 11-3).
- '입항보고 수리'가 보이면 입항일·도착항·선적항을 다시 맞춘다.
- 관리대상화물이면 비고 `⚠️ 관리대상화물: 검색기`.
- 모선명은 유니패스 기준(서류 판독 → 유니패스, AGENTS 5-5 6번).
"""

from app.core.schema.fields import Evidence
from app.core.schema.history import C_ARRIVAL, C_CARGO, C_VESSEL, HistoryRow
from app.core.unipass.client import CargoInfo

COLS = (
    ("반입지 코드", "arrival_place_code"),
    (C_ARRIVAL, "arrival_date"),
    ("입항일", "entry_date"),
    ("도착항 코드", "port_of_arrival"),
    ("선적항 코드", "port_of_loading"),
    (C_CARGO, "cargo_no"),
)


def apply_cargo(row: HistoryRow, cargo: CargoInfo | None) -> None:
    """순수 함수."""
    if cargo is None:
        row.set_note("유니패스", "화물 정보를 찾지 못함(B/L 번호·입항 전 여부 확인)")
        return
    label = "유니패스 화물진행정보" + ("" if cargo.source == "live" else " (가상 자료)")
    ev = [Evidence(source="UNIPASS", ref=cargo.cargo_no or cargo.bl_no, note=label)]
    for col, attr in COLS:
        v = getattr(cargo, attr) or None
        if col == "입항일" and v and not cargo.entry_reported and cargo.source == "live":
            row.set_ai(col, v, ev, memo="입항보고 수리 전: 예정일일 수 있음")
            continue
        row.set_ai(col, v, ev if v else [])
    if cargo.vessel:
        row.set_ai(
            C_VESSEL,
            cargo.vessel,
            [
                *ev,
                Evidence(
                    source="UNIPASS", ref=cargo.bl_no, note=f"유니패스 모선명: {cargo.vessel}"
                ),
            ],
        )
    row.set_note("유니패스", None)
    row.set_note(
        "관리대상화물", cargo.managed_cargo.split(": ", 1)[-1] if cargo.managed_cargo else None
    )
