"""검역 리스트 탭 단계 표시줄(① 서류 올리기·추출 → ② 서류 대조·검수 → ③ 완성된 검역 리스트)의 완료 판단.
화주별로 한 번에 계산한다. 순수 계산(저장 없음). 담당: KHS [신규] (검역 리스트 탭 0단계, HS 요청 11/26)

- ① 올린 선적 건(B/L)마다 CI·PL·B/L이 모두 있다 = '○○ 자료 추가 필요' 칸이 있는 선적 건 0
- ② 미해결 불일치 0 = 담당자 값(final_value)이 없는 flag=mismatch 칸 0 (확인함 행은 뺀다)
- ③ 완성된 검역 리스트에 빈 필수 칸 0 (등록 정보 연동 칸 포함). 승인 행은 뺀다.
"""

from app.a1_history.missing.service import MARK_BL, MARK_CI_PL
from app.core.schema.history import (
    C_ARRIVAL,
    C_BL,
    C_CARGO,
    C_CARTONS,
    C_MAKER,
    C_MATERIAL,
    C_NAME_EN,
    C_NAME_KO,
    C_NET,
    C_PRICE_USD,
    C_QTY,
    C_RECORD,
    C_SPEC,
    C_VESSEL,
    HistoryRow,
)

# 신청에 꼭 필요한 칸 14개 (검역 신고일자·승인번호·비고·숨김 칸은 뺀다). 확정: HS 결정 11/26 (AGENTS 4-6)
REQUIRED_COLUMNS: tuple[str, ...] = (
    C_BL,
    C_VESSEL,
    C_MAKER,
    C_CARGO,
    C_NAME_KO,
    C_QTY,
    C_CARTONS,
    C_NET,
    C_PRICE_USD,
    C_MATERIAL,
    C_RECORD,
    C_NAME_EN,
    C_SPEC,
    C_ARRIVAL,
)
MISSING_SUFFIX = "자료 추가 필요"


def _is_missing_doc(value: object) -> bool:
    """선적서류(CI·PL·B/L)가 빠진 표시만 (현품사진 등 다른 '자료 추가 필요'는 ①이 아니라 ③에서 센다)."""
    return value in (MARK_CI_PL, MARK_BL)


def _missing_any(value: object) -> bool:
    return isinstance(value, str) and MISSING_SUFFIX in value


def _empty(row: HistoryRow, col: str) -> bool:
    v = row.val(col)
    return v is None or v == "" or _missing_any(v)


def steps(rows: list[HistoryRow]) -> dict:
    active = [r for r in rows if not r.locked]
    shipments = {r.shipment_key or f"(B/L 미상:{r.row_id})" for r in rows}
    missing_docs = {
        r.shipment_key or f"(B/L 미상:{r.row_id})"
        for r in active
        if any(_is_missing_doc(c.value) for c in r.cells.values())
    }
    mismatches = sum(
        1
        for r in active
        if not r.confirmed
        for c in r.cells.values()
        if c.flag == "mismatch" and c.final_value is None
    )
    empty_rows = sum(1 for r in active if any(_empty(r, c) for c in REQUIRED_COLUMNS))
    has_rows = bool(rows)
    return {
        "shipments": len(shipments),
        "rows": len(rows),
        "steps": [
            {
                "key": "upload",
                "done": has_rows and not missing_docs,
                "remaining": len(missing_docs),
                "label": "자료 추가 필요" if has_rows else "올린 서류 없음",
            },
            {
                "key": "review",
                "done": has_rows and mismatches == 0,
                "remaining": mismatches,
                "label": "불일치",
            },
            {
                "key": "list",
                "done": has_rows and empty_rows == 0,
                "remaining": empty_rows,
                "label": "빈 필수 칸 행",
            },
        ],
    }
