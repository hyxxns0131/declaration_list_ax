"""부분품 줄 합치기 (RULES 11-6 부분품, A사 merge_spare_parts). 가상 값."""

from app.a3_judge.spare_parts.merge import choose_name_model, merge_spare_lines
from app.core.schema.document import DocumentLine


def main(model, cartons=10.0):
    return DocumentLine(
        model=model, description="RICE COOKER", cartons=cartons, net_kg=50, amount=100
    )


def part(model, cartons=1.0, net=2.0, amount=5.0, desc="INNER POT"):
    return DocumentLine(
        model=model, description=desc, cartons=cartons, net_kg=net, amount=amount, is_part=True
    )


def test_no_parts_unchanged():
    lines = [main("M1")]
    assert merge_spare_lines(lines) == (lines, None)


def test_sum_and_one_row():
    mains, merged = merge_spare_lines([main("M1"), part("M1", 1, 2, 5), part("M1", 2, 3, 7.5)])
    assert [m.model for m in mains] == ["M1"]
    ln = merged.line
    assert (ln.cartons, ln.net_kg, ln.amount, ln.is_part) == (3, 5, 12.5, True)
    assert ln.model == "M1" and ln.description == "SPARE PARTS FOR M1"
    assert ln.qty_per_carton is None  # 여러 부품이라 입수는 정하지 않음
    assert len(merged.part_lines) == 2 and not merged.need_check


def test_name_model_same_model_first():
    assert choose_name_model([main("M1"), main("M2")], [part("M2")])[:2] == ("M2", False)


def test_name_model_prefix():
    assert choose_name_model([main("M1"), main("M1-PRO")], [part("M1-PRO-LID")])[:2] == (
        "M1-PRO",
        False,
    )


def test_name_model_smallest_cartons_needs_check():
    got = choose_name_model([main("M1", 10), main("M2", 3)], [part("X9")])
    assert got[:2] == ("M2", True) and "확인 필요" in got[2]


def test_smallest_ignores_empty_cartons():
    """카톤 수가 빈 본품을 0으로 보지 않는다(11/26 수정)."""
    assert choose_name_model([main("M1", None), main("M2", 3)], [part("X9")])[0] == "M2"


def test_no_main_needs_check():
    got = choose_name_model([], [part("X9")])
    assert got[:2] == ("X9", True) and "본품 없음" in got[2]


def test_quantity_is_sum_of_part_pcs():
    """합친 행의 입수 = 부분품 줄 전체 개수 합(수량 PCS, 없으면 카톤당 수량 x 카톤 수, AGENTS 4-6)."""
    a = part("M1", cartons=2)
    a.quantity = 40
    b = part("M1", cartons=3)
    b.qty_per_carton = 10  # → 30
    assert merge_spare_lines([main("M1"), a, b])[1].line.quantity == 70


def test_quantity_empty_when_any_part_unknown():
    a = part("M1")
    a.quantity = 40
    assert merge_spare_lines([main("M1"), a, part("M1")])[1].line.quantity is None
