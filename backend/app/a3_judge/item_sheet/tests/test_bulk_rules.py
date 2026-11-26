"""묶음 내려받기 규칙 (DB 없이): 파일 이름 안전 글자, 모델군, 품목 이름표, 제외 이유. 가상 값."""

from app.a3_judge.item_sheet.bulk import _model_group, _problems, _product_label, _safe
from app.a4_settings.engine.service import merge_rules
from app.core.schema.history import (
    C_BL,
    C_CARGO,
    C_MAKER,
    C_MATERIAL,
    C_NAME_KO,
    C_RECORD,
    HistoryRow,
)


def row(
    rid, mat="금속제", record="202600000101 (2026.01.01)", ko="전기밥솥(RC-100)", model="RC-100"
):
    r = HistoryRow(row_id=rid, shipper_id="T", model=model)
    for k, v in {
        C_BL: "BL-DEMO-1",
        C_CARGO: "26DEMO000010001",
        C_MAKER: "가상공장 (CN1)",
        C_MATERIAL: mat,
        C_RECORD: record,
        C_NAME_KO: ko,
    }.items():
        if v:
            r.set_ai(k, v)
    return r


S = merge_rules({"required_docs": ["CI"]}, {}, "T")


def test_safe_filename():
    assert _safe('A/B:C*?"<>| d') == "A_B_C_d"
    assert _safe("") == "미상"
    assert len(_safe("X" * 50)) == 30


def test_model_group():
    assert _model_group("RC-100") == "RC" and _model_group("pot14") == "POT"
    assert _model_group("100") == ""


def test_product_label_name_then_model_group():
    assert _product_label([row("r1")]) == "전기밥솥"
    assert _product_label([row("r1", ko="한글 제품명 자료 추가 필요")]) == "RC"
    assert _product_label([]) == ""


def test_problems_ok_and_reasons():
    assert _problems([row("r1"), row("r2")], S) == []
    assert _problems([], S) == ["행이 없습니다"]
    no_rec = _problems([row("r1", record="")], S)
    assert any(x.startswith("실적 자료 없음 1행") for x in no_rec)


def test_rows_without_material_excluded():
    """재질이 정해지지 않은 행은 묶음 내려받기에서도 빠진다(11/26, check_one_declaration)."""
    reasons = _problems([row("r1", mat="현품사진·한글표시 자료 추가 필요 (RC-100)")], S)
    assert any("재질이 정해지지 않은 행" in x for x in reasons)
