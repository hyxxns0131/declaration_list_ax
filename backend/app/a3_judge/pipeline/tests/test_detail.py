"""근거 패널용 상세: 재질 근거 순서(화주 설정 material_source_order)와 실적 기준일. 가상 값."""

from datetime import date

from app.a3_judge.pipeline.context import JudgeContext
from app.a3_judge.pipeline.judge_row import judge_row_detail
from app.a4_settings.engine.service import merge_rules
from app.core.schema.history import HistoryRow


def _detail(**rules):
    ctx = JudgeContext(
        settings=merge_rules({"required_docs": ["CI"]}, rules, "T"),
        history=[],
        today=date(2026, 11, 27),
    )
    return judge_row_detail(HistoryRow(row_id="n1", shipper_id="T", model="M1"), ctx)[1]


def test_default_order_and_basis_date():
    d = _detail()
    assert d["material"]["order"] == ["HISTORY", "IMPORT_DECL", "TEST_REPORT", "PHOTO"]
    assert d["record"]["basis_date"] == "2026-11-27"


def test_order_follows_shipper_setting():
    """은진 파트(기업 설정)에서 순서를 바꾸면 판단·화면 순서가 같이 바뀐다."""
    order = ["TEST_REPORT", "HISTORY", "PHOTO", "IMPORT_DECL"]
    assert _detail(material_source_order=order)["material"]["order"] == order
