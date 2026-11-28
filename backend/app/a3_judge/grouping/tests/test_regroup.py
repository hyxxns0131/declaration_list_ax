"""다시 묶기: 담당자가 한 행 재질을 바꿔도 다른 신고건 번호는 그대로. 반입일 상태. 가상 행만."""

from app.a3_judge.grouping.arrival import arrival_status, latest_arrival
from app.a3_judge.grouping.regroup import keep_ids
from app.a3_judge.grouping.split import group_rows
from app.a3_judge.grouping.tests.test_grouping import row
from app.a4_settings.engine.service import merge_rules
from app.core.schema.history import C_MATERIAL

S = merge_rules({"required_docs": ["CI"]}, {}, "T")


def _ids(decls):
    return {d.declaration_id: sorted(d.row_ids) for d in decls}


def test_changed_row_moves_others_keep_ids():
    rows = [row("a"), row("b"), row("c", mat="유리제"), row("d", mat="유리제")]
    before = keep_ids([], group_rows(rows, S), "T")
    assert _ids(before) == {"T-D001": ["a", "b"], "T-D002": ["c", "d"]}
    # 순서상 앞의 'a' 재질을 유리제로 고침 → 그냥 다시 계산하면 번호가 바뀔 수 있다
    rows[0].set_ai(C_MATERIAL, "유리제")
    after = keep_ids(before, group_rows(rows, S), "T")
    assert _ids(after) == {"T-D001": ["b"], "T-D002": ["a", "c", "d"]}


def test_new_group_gets_next_number_not_reused():
    rows = [row("a"), row("c", mat="유리제")]
    before = keep_ids([], group_rows(rows, S), "T")  # D001(a), D002(c)
    rows[0].set_ai(C_MATERIAL, "유리제")  # D001이 비고, 모두 D002로
    mid = keep_ids(before, group_rows(rows, S), "T")
    assert _ids(mid) == {"T-D002": ["a", "c"]}
    rows.append(row("e", mat="고무제"))  # 새 묶음 → D003 (비었던 D001을 다시 쓰지 않음)
    after = keep_ids(mid, group_rows(rows, S), "T")
    assert _ids(after) == {"T-D002": ["a", "c"], "T-D003": ["e"]}


def test_added_row_joins_existing_declaration():
    rows = [row("a"), row("b")]
    before = keep_ids([], group_rows(rows, S), "T")
    rows.insert(0, row("z"))  # 같은 키의 새 행이 맨 앞에 들어와도 같은 신고건 번호
    after = keep_ids(before, group_rows(rows, S), "T")
    assert _ids(after) == {"T-D001": ["a", "b", "z"]}


def test_arrival_latest_and_status():
    rows = [row("a", arrival="2026-11-20"), row("b", arrival="2026-11-25"), row("c", arrival="")]
    assert latest_arrival(rows) == "2026-11-25"
    assert latest_arrival([row("x", arrival="")]) is None
    assert arrival_status("신청 전", None) == "반입 전"
    assert arrival_status("신청 전", "2026-11-25") == "신청 전"
    assert arrival_status("확인 필요", None) == "확인 필요"


def test_row_getting_material_keeps_its_number():
    """재질이 없어 혼자 있던 행이 재질을 얻으면 키가 바뀌어도 같은 번호."""
    rows = [row("a", mat=""), row("b", mat="")]
    before = keep_ids([], group_rows(rows, S), "T")
    assert _ids(before) == {"T-D001": ["a"], "T-D002": ["b"]}
    rows[0].set_ai(C_MATERIAL, "도자기제")
    rows[1].set_ai(C_MATERIAL, "유리제")
    after = keep_ids(before, group_rows(rows, S), "T")
    assert _ids(after) == {"T-D001": ["a"], "T-D002": ["b"]}
