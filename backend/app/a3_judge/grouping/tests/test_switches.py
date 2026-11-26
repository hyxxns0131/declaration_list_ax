"""기업 설정 스위치가 신고건 결과를 바꾸는지(로직 점검 반영 11/25): sort_by, group_by_color + color_basis,
group_by_maker(공통 규칙, 끌 수 없음). 가상 행만 쓴다."""

import pytest

from app.a3_judge.grouping.split import group_rows
from app.a4_settings.engine.service import merge_rules
from app.a4_settings.shippers.service import validate
from app.core.errors import AppError
from app.core.schema.history import (
    C_BL,
    C_CARGO,
    C_MAKER,
    C_MATERIAL,
    COLOR_COLUMN,
    OUTER_COLOR_COLUMN,
    HistoryRow,
)


def _row(
    rid: str, model: str, inner: str = "", outer: str = "", maker: str = "가상공장 (CN900000001)"
) -> HistoryRow:
    r = HistoryRow(row_id=rid, shipper_id="T", model=model)
    r.set_ai(C_BL, "BLTEST900")
    r.set_ai(C_CARGO, "26VTEST9000100")
    r.set_ai(C_MAKER, maker)
    r.set_ai(C_MATERIAL, "폴리프로필렌")
    if inner:
        r.set_ai(COLOR_COLUMN, inner)
    if outer:
        r.set_ai(OUTER_COLOR_COLUMN, outer)
    return r


def _settings(**kw: object):
    return merge_rules({"required_docs": ["CI"]}, kw, "T")


def test_sort_by_changes_row_and_declaration_order():
    rows = [_row("r1", "ZZ-9"), _row("r2", "AA-1"), _row("r3", "MM-5")]
    plain = group_rows(rows, _settings())
    by_model = group_rows(rows, _settings(sort_by=["model"]))
    assert plain[0].row_ids == ["r1", "r2", "r3"]  # 비우면 서류 순서
    assert by_model[0].row_ids == ["r2", "r3", "r1"]  # 모델 순
    # 최대 행 수로 끊으면 신고건 구성도 바뀐다
    cut_plain = group_rows(rows, _settings(max_rows_per_declaration=2))
    cut_sorted = group_rows(rows, _settings(max_rows_per_declaration=2, sort_by=["model"]))
    assert cut_plain[0].row_ids != cut_sorted[0].row_ids


def test_color_basis_changes_grouping():
    rows = [
        _row("r1", "A1", inner="흰색", outer="빨강"),
        _row("r2", "A2", inner="흰색", outer="파랑"),
    ]
    off = group_rows(rows, _settings(group_by_color=False))
    inner = group_rows(rows, _settings(group_by_color=True, color_basis="내색"))
    outer = group_rows(rows, _settings(group_by_color=True, color_basis="외색"))
    both = group_rows(rows, _settings(group_by_color=True, color_basis=None))
    assert len(off) == 1 and len(inner) == 1  # 내색이 같으면 한 신고
    assert len(outer) == 2 and len(both) == 2  # 외색(또는 전체)이 다르면 나뉨


def test_group_by_maker_is_locked_on():
    s = merge_rules({}, {"group_by_maker": False}, "T")
    assert s.group_by_maker is True  # RULES 11-6: 끌 수 없음
    rows = [_row("r1", "A1"), _row("r2", "A2", maker="다른공장 (CN900000002)")]
    assert len(group_rows(rows, s)) == 2  # 제조업소가 다르면 항상 나뉨
    with pytest.raises(AppError):
        validate({"group_by_maker": False})
