"""행 → 신고건 묶음. 키가 같은 행끼리, 최대 행 수에서 끊는다. 순수 함수. 담당: LSY [개선] A3-4"""

from app.a3_judge.grouping.keys import NO_CARGO_PREFIX, key_tuple, row_key
from app.a3_judge.grouping.order import sort_rows
from app.core.schema.declaration import Declaration, DeclarationKey
from app.core.schema.history import C_ARRIVAL, C_RECORD, HistoryRow
from app.core.schema.shipper import ShipperSettings

W_NO_CARGO = "화물관리번호 없음: 모선명으로 묶음 (확인 필요)"
W_NO_FACTORY = "제조사 없음: 제조사 확인 후 다시 묶어야 함"
W_MULTI_RECORD = "한 신고에 실적번호가 여러 개 (one_record_per_declaration)"
W_NO_ARRIVAL = "반입일 없음"


def _record_nos(rows: list[HistoryRow]) -> list[str]:
    out: list[str] = []
    for r in rows:
        no = r.text(C_RECORD).split(" ")[0].strip()
        if no and no not in out:
            out.append(no)
    return out


def _arrival(rows: list[HistoryRow]) -> str | None:
    """묶인 B/L 중 가장 최근 반입일(RULES 11-3)."""
    dates = [r.text(C_ARRIVAL) for r in rows if r.text(C_ARRIVAL)]
    return max(dates) if dates else None


def group_rows(rows: list[HistoryRow], settings: ShipperSettings) -> list[Declaration]:
    """rows는 표 순서. 화주 설정 sort_by로 먼저 정렬하고(비우면 표 순서), 같은 키의 첫 행 순서대로 신고건을 만든다."""
    buckets: dict[tuple[str, str, str, str], tuple[DeclarationKey, list[HistoryRow]]] = {}
    for r in sort_rows(rows, list(getattr(settings, "sort_by", []) or [])):
        k = row_key(r, settings)
        buckets.setdefault(key_tuple(k), (k, []))[1].append(r)

    max_rows = settings.max_rows_per_declaration
    one_record = getattr(settings, "one_record_per_declaration", True)
    out: list[Declaration] = []
    for k, members in buckets.values():
        size = max_rows if max_rows and max_rows > 0 else len(members) or 1
        for i in range(0, len(members), size):
            chunk = members[i : i + size]
            warnings: list[str] = []
            if k.vessel_key.startswith(NO_CARGO_PREFIX) or not k.vessel_key:
                warnings.append(W_NO_CARGO)
            if not k.factory_code:
                warnings.append(W_NO_FACTORY)
            records = _record_nos(chunk)
            if one_record and len(records) > 1:
                warnings.append(W_MULTI_RECORD)
            arrival = _arrival(chunk)
            if not arrival:
                warnings.append(W_NO_ARRIVAL)
            out.append(
                Declaration(
                    declaration_id=f"{settings.shipper_id}-D{len(out) + 1:03d}",
                    shipper_id=settings.shipper_id,
                    key=k,
                    row_ids=[r.row_id for r in chunk],
                    record_nos=records,
                    arrival_date=arrival,
                    warnings=warnings,
                )
            )
    return out
