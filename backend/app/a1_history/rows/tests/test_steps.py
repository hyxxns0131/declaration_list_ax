"""검역 리스트 단계 표시줄 완료 판단 (0단계). 가상 행만 쓴다."""

from app.a1_history.missing.service import C_SHIP_DATE
from app.a1_history.rows.steps import REQUIRED_COLUMNS, steps
from app.core.schema.history import C_BL, C_NAME_KO, HistoryRow


def _row(rid: str, bl: str = "BLTEST900") -> HistoryRow:
    r = HistoryRow(row_id=rid, shipper_id="T", model="M1")
    for c in REQUIRED_COLUMNS:
        r.set_ai(c, "값")
    r.set_ai(C_BL, bl)
    return r


def test_no_rows():
    s = steps([])
    assert [x["done"] for x in s["steps"]] == [False, False, False]
    assert s["steps"][0]["label"] == "올린 서류 없음"


def test_all_done():
    s = steps([_row("r1"), _row("r2")])
    assert all(x["done"] for x in s["steps"]) and s["shipments"] == 1


def test_missing_doc_mismatch_and_empty():
    a = _row("r1")
    a.set_ai(C_SHIP_DATE, "B/L 자료 추가 필요", flag="need_input")
    b = _row("r2", "BLTEST901")
    b.set_ai(C_NAME_KO, None, flag="mismatch")
    s = {x["key"]: x for x in steps([a, b])["steps"]}
    assert s["upload"]["remaining"] == 1 and not s["upload"]["done"]
    assert s["review"]["remaining"] == 1
    assert s["list"]["remaining"] == 1  # b의 한글 제품명이 비어 있음
    b.cells[C_NAME_KO].final_value = "담당자 값"
    s = {x["key"]: x for x in steps([a, b])["steps"]}
    assert s["review"]["done"] and s["list"]["done"]
