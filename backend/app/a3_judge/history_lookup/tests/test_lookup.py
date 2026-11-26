"""과거 검역이력에서 같은 모델의 행 찾기 (RULES 11-4 ① 이력). 가상(DEMO) 값."""

from app.a3_judge.history_lookup.lookup import find_past
from app.core.schema.fields import Field
from app.core.schema.history import C_APPROVAL, C_MATERIAL, HistoryRow


def row(rid, model="DEMO-M01", mat="금속제", is_part=False, approved="", flag="ok"):
    cells = {C_MATERIAL: Field(ai_value=mat, flag=flag)}
    if approved:
        cells[C_APPROVAL] = Field(ai_value=approved)
    return HistoryRow(row_id=rid, shipper_id="A", model=model, is_part=is_part, cells=cells)


def test_latest_row_wins():
    hist = [row("r1", mat="금속제"), row("r2", mat="고무제, 금속제")]
    assert find_past(hist, "DEMO-M01", False).row_id == "r2"


def test_approved_row_preferred_over_newer():
    hist = [row("r1", approved="DEMO-OK1"), row("r2")]
    assert find_past(hist, "demo-m01", False).row_id == "r1"


def test_part_and_main_kept_apart():
    hist = [row("main"), row("part", is_part=True, mat="폴리프로필렌")]
    assert find_past(hist, "DEMO-M01", True).row_id == "part"
    assert find_past(hist, "DEMO-M01", False).row_id == "main"


def test_exact_model_only():
    assert find_past([row("r1", model="DEMO-M01F")], "DEMO-M01", False) is None


def test_skip_rows_without_material():
    hist = [
        row("ok"),
        row("empty", mat=None),
        row("need", mat="현품사진·한글표시 자료 추가 필요 (DEMO-M01)", flag="need_input"),
    ]
    assert find_past(hist, "DEMO-M01", False).row_id == "ok"


def test_exclude_self():
    hist = [row("old"), row("me")]
    assert find_past(hist, "DEMO-M01", False, exclude_row_id="me").row_id == "old"


def test_no_history():
    assert find_past([], "DEMO-M01", False) is None
