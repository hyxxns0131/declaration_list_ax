"""구분표 적용 — 수치는 시험용 가짜 표(실제 공전 수치 아님). 설정이 없으면 이름을 붙이지 않는다."""

from app.a3_judge.spec_class.parse import parse_spec
from app.a3_judge.spec_class.tables import lookup

FAKE = {
    "도자기제": [
        {"label": "가짜-평판", "flat": True},
        {"label": "가짜-얕음", "depth_max_cm": 10},
        {"label": "가짜-깊고 작음", "depth_min_cm": 10, "volume_max_ml": 1000},
        {"label": "가짜-깊고 큼", "depth_min_cm": 10, "volume_min_ml": 1000},
    ]
}


def test_no_table_no_label():
    label, memo = lookup("도자기제", parse_spec("깊이 3cm, 용량 1L"), None)
    assert label is None and "구분표 설정 없음" in memo


def test_first_matching_row():
    assert lookup("도자기제", parse_spec("평판"), FAKE)[0] == "가짜-평판"
    assert lookup("도자기제", parse_spec("깊이 3cm, 용량 1L"), FAKE)[0] == "가짜-얕음"
    assert lookup("도자기제", parse_spec("깊이 12cm, 용량 800mL"), FAKE)[0] == "가짜-깊고 작음"
    assert lookup("도자기제", parse_spec("깊이 12cm, 용량 1.5L"), FAKE)[0] == "가짜-깊고 큼"


def test_missing_input_returns_none():
    label, memo = lookup("도자기제", parse_spec("용량 1L"), FAKE)
    assert label is None and "모자람" in memo
