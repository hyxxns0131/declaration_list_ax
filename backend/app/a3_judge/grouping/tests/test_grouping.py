"""신고건 나누기 (RULES 11-6): 반드시 조건(모선·제조업소), 재질, 최대 행 수, 반입일·실적 경고. 가상 행만."""

from app.a3_judge.grouping.keys import material_key, vessel_key
from app.a3_judge.grouping.split import (
    W_MULTI_RECORD,
    W_NO_ARRIVAL,
    W_NO_CARGO,
    W_NO_FACTORY,
    W_NO_MATERIAL,
    group_rows,
)
from app.a4_settings.engine.service import merge_rules
from app.core.schema.history import (
    C_ARRIVAL,
    C_CARGO,
    C_MAKER,
    C_MATERIAL,
    C_RECORD,
    C_VESSEL,
    HistoryRow,
)

CARGO1 = "26DEMO000010001"  # 앞 11자리 = 모선
CARGO2 = "26DEMO000020001"


def row(
    rid,
    cargo=CARGO1,
    maker="가상공장 (CN900000001)",
    mat="금속제",
    arrival="2026-11-20",
    record="",
):
    r = HistoryRow(row_id=rid, shipper_id="T", model=rid.upper())
    r.set_ai(C_CARGO, cargo)
    r.set_ai(C_MAKER, maker)
    r.set_ai(C_MATERIAL, mat)
    if arrival:
        r.set_ai(C_ARRIVAL, arrival)
    if record:
        r.set_ai(C_RECORD, record)
    return r


def s(**kw):
    return merge_rules({"required_docs": ["CI"]}, kw, "T")


def ids(decls):
    return [d.row_ids for d in decls]


# --- 키 ---
def test_vessel_key_first_11_and_fallback():
    assert vessel_key(row("r1", cargo="26DEMO-00001-0001")) == "26DEMO00001"
    r = row("r2", cargo="")
    r.set_ai(C_VESSEL, "demo vessel")
    assert vessel_key(r) == "모선명:DEMO VESSEL"  # 화물관리번호 전에는 모선명 (확인 필요 2)


def test_material_key_need_input_is_empty():
    assert material_key(row("r1", mat="현품사진·한글표시 자료 추가 필요 (R1)")) == ""


# --- 반드시 조건 ---
def test_one_declaration_when_all_same():
    assert ids(group_rows([row("r1"), row("r2")], s())) == [["r1", "r2"]]


def test_different_vessel_split():
    assert ids(group_rows([row("r1"), row("r2", cargo=CARGO2)], s())) == [["r1"], ["r2"]]


def test_different_factory_code_split():
    rows = [row("r1"), row("r2", maker="가상공장 (CN900000002)")]
    assert ids(group_rows(rows, s())) == [["r1"], ["r2"]]


def test_same_code_different_name_spelling_together():
    """공장은 업소코드로 비교 — 이름 표기만 다르면 같은 신고 (11/25 결정)."""
    rows = [row("r1"), row("r2", maker="GA-SANG FACTORY CO.,LTD (CN900000001)")]
    assert ids(group_rows(rows, s())) == [["r1", "r2"]]


# --- 재질 (화주 설정) ---
def test_material_split_and_switch_off():
    rows = [row("r1"), row("r2", mat="폴리프로필렌")]
    assert ids(group_rows(rows, s())) == [["r1"], ["r2"]]
    assert ids(group_rows(rows, s(group_by_material=False))) == [["r1", "r2"]]


def test_material_order_only_different_same_declaration():
    """가나다순·중복 제거 후 목록이 같으면 같은 신고 (11/25 결정 Q3)."""
    rows = [row("r1", mat="금속제, 폴리프로필렌"), row("r2", mat="폴리프로필렌, 금속제, 금속제")]
    assert ids(group_rows(rows, s())) == [["r1", "r2"]]


def test_rows_without_material_kept_apart():
    """재질이 정해지지 않은 행은 한 행씩 따로 두고 경고 (11/26)."""
    rows = [
        row("r1", mat="현품사진·한글표시 자료 추가 필요 (R1)"),
        row("r2", mat="현품사진·한글표시 자료 추가 필요 (R2)"),
        row("r3", mat=""),
        row("r4"),
    ]
    decls = group_rows(rows, s())
    assert ids(decls) == [["r1"], ["r2"], ["r3"], ["r4"]]
    assert all(W_NO_MATERIAL in d.warnings for d in decls[:3])
    assert W_NO_MATERIAL not in decls[3].warnings


# --- 최대 행 수 ---
def test_max_rows_cut():
    rows = [row(f"r{i}") for i in range(1, 6)]
    assert ids(group_rows(rows, s(max_rows_per_declaration=2))) == [
        ["r1", "r2"],
        ["r3", "r4"],
        ["r5"],
    ]
    assert len(group_rows(rows, s())) == 1  # 기본은 끊지 않음


# --- 신고건 칸·경고 ---
def test_latest_arrival_date():
    rows = [row("r1", arrival="2026-11-18"), row("r2", arrival="2026-11-21")]
    assert group_rows(rows, s())[0].arrival_date == "2026-11-21"  # RULES 11-3


def test_warnings_no_cargo_no_factory_no_arrival():
    d = group_rows([row("r1", cargo="", maker="", arrival="")], s())[0]
    assert W_NO_CARGO in d.warnings and W_NO_FACTORY in d.warnings and W_NO_ARRIVAL in d.warnings


def test_multi_record_warning_by_setting():
    rows = [row("r1", record="DEMO-101 (2028.01.01)"), row("r2", record="DEMO-102 (2028.01.01)")]
    one = group_rows(rows, s())[0]
    assert one.record_nos == ["DEMO-101", "DEMO-102"] and W_MULTI_RECORD in one.warnings
    many = group_rows(rows, s(one_record_per_declaration=False))[0]
    assert W_MULTI_RECORD not in many.warnings  # B사처럼 여러 실적 허용


def test_declaration_ids_in_order():
    decls = group_rows([row("r1"), row("r2", cargo=CARGO2)], s())
    assert [d.declaration_id for d in decls] == ["T-D001", "T-D002"]
