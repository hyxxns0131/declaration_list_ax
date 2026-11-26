"""품목사항 엑셀 (RULES 11-10): 한 신고건 검사, 칸 채우기, 길이 경고, 엑셀 쓰기. AI 없음. 가상 행만."""

from io import BytesIO

from openpyxl import load_workbook

from app.a3_judge.item_sheet.build import HEADERS, build_item_sheet, clean_name_en, split_cargo
from app.a3_judge.item_sheet.validate import check_one_declaration
from app.a3_judge.item_sheet.writer import write_xlsx
from app.a4_settings.engine.service import merge_rules
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
    C_RECORD,
    HistoryRow,
)

CARGO = "26DEMO000010001-0002"


def row(rid, cargo=CARGO, maker="가상공장 (CN900000001)", mat="금속제", en=None, **cells):
    r = HistoryRow(row_id=rid, shipper_id="T", model=rid.upper())
    base = {
        C_BL: "BL-DEMO-001",
        C_CARGO: cargo,
        C_MAKER: maker,
        C_MATERIAL: mat,
        C_NAME_EN: en or f"RICE COOKER({rid.upper()})",
        C_NAME_KO: f"전기밥솥({rid.upper()})",
        C_CARTONS: "12",
        C_NET: "96.50",
        C_PRICE_USD: "1,234.5",
        C_RECORD: "DEMO-101 (2028.01.01)",
        C_ARRIVAL: "2026-11-20",
    }
    base.update(cells)
    for k, v in base.items():
        if v is not None:
            r.set_ai(k, v)
    return r


def s(**kw):
    return merge_rules({"required_docs": ["CI"]}, kw, "T")


# --- 한 신고건 검사 ---
def test_one_declaration_ok():
    assert check_one_declaration([row("m1"), row("m2")], s()) == []


def test_reject_mixed_with_reason():
    reasons = check_one_declaration(
        [row("m1"), row("m2", cargo="26DEMO000020001"), row("m3", maker="다른공장 (CN900000002)")],
        s(),
    )
    assert len(reasons) == 2
    assert "모선" in reasons[0] and "BL-DEMO-001 M2" in reasons[0]
    assert "제조사" in reasons[1]


def test_reject_rows_without_material():
    reasons = check_one_declaration(
        [row("m1", mat="현품사진·한글표시 자료 추가 필요 (M1)"), row("m2", mat="")], s()
    )
    assert any("재질이 정해지지 않은 행" in x and "M1" in x and "M2" in x for x in reasons)


def test_reject_over_max_rows_and_empty():
    assert check_one_declaration([], s()) == ["고른 행이 없습니다."]
    reasons = check_one_declaration([row("m1"), row("m2")], s(max_rows_per_declaration=1))
    assert any("최대 1행" in x for x in reasons)


# --- 칸 채우기 ---
def test_build_values():
    sheet = build_item_sheet([row("m1"), row("m2")])
    first, second = sheet.rows
    assert first[:9] == [
        "RICE COOKER(M1)",
        "전기밥솥(M1)",
        "Y",
        "12",  # 수량 = 카톤 수
        "96.5",
        "1234.5",  # 과세가격 = 가격(USD), 쉼표 없이
        "26DEMO00001",
        "0001",
        "0002",
    ]
    assert second[2] == "N" and first[9:] == [""] * 6
    assert len(first) == len(HEADERS) == 15


def test_split_cargo_keeps_leading_zero():
    assert split_cargo("26DEMO00001-0001-0002") == ("26DEMO00001", "0001", "0002")


def test_manual_mark_removed_from_name():
    """영문 제품명의 수기 표시 '정밀검사'는 품목사항에서 뗀다(11/25 결정)."""
    assert clean_name_en("RICE COOKER(M1) 정밀검사") == "RICE COOKER(M1)"
    sheet = build_item_sheet([row("m1", en="RICE COOKER(M1)정밀검사")])
    assert sheet.rows[0][0] == "RICE COOKER(M1)"


def test_warnings():
    sheet = build_item_sheet(
        [row("m1", en="X" * 101, **{C_PRICE_USD: None, C_RECORD: None, C_ARRIVAL: None})]
    )
    w = " ".join(sheet.warnings)
    assert "제품명 101자 (최대 100자)" in w
    assert (
        "가격(USD)이 비어 있음" in w
        and "실적접수번호가 비어 있음" in w
        and "반입일이 없습니다" in w
    )


# --- 엑셀 쓰기 ---
def test_write_xlsx_text_cells():
    data = write_xlsx(build_item_sheet([row("m1")]))
    ws = load_workbook(BytesIO(data)).active
    assert [c.value for c in ws[1]] == [h for h, _ in HEADERS]
    assert ws.cell(2, 8).value == "0001"  # 앞자리 0 보존(글자로)
    assert ws.cell(2, 3).value == "Y"
