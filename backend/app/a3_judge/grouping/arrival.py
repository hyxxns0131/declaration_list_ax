"""반입일 — 신고건의 반입일과 '신청 전' 판정. 순수 함수. 담당: LSY [재사용] A3-4

RULES 11-3: 한 신고건에 B/L이 여러 개면 **가장 최근 반입일**. 반입일이 들어온 묶음만 '신청 전',
아직 없으면 '반입 전'(반입되기 전에는 신청할 수 없음).
"""

from app.core.schema.history import C_ARRIVAL, HistoryRow

READY = "신청 전"
NOT_ARRIVED = "반입 전"


def latest_arrival(rows: list[HistoryRow]) -> str | None:
    """묶인 행(B/L) 중 가장 최근 반입일. 날짜는 YYYY-MM-DD 글자라 글자 비교 = 날짜 비교."""
    dates = [r.text(C_ARRIVAL) for r in rows if r.text(C_ARRIVAL)]
    return max(dates) if dates else None


def arrival_status(status: str, arrival_date: str | None) -> str:
    """행 상태 → 반입일을 반영한 상태. '신청 전'인데 묶음 반입일이 없으면 '반입 전'. 나머지는 그대로."""
    if status == READY and not arrival_date:
        return NOT_ARRIVED
    return status
