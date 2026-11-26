"""B/L 머리 줄의 라벨 글자를 값(모선명 등)으로 읽지 않는지 (HS 요청 11/26). 가상 줄만 쓴다."""

from app.a0_reader.extract.grid_parse import _parse_head, looks_like_label
from app.a0_reader.extract.pdf import _line_to_cells


def test_label_line_is_not_vessel():
    # PDF 한 줄이 'Vessel & Voyage: Port of loading: Sailing Date: Place of Receipt:' 처럼 라벨만 이어진 경우
    grid = [_line_to_cells("Vessel & Voyage: Port of loading: Sailing Date: Place of Receipt:")]
    assert "vessel" not in _parse_head(grid)


def test_next_cell_label_is_not_value():
    grid = [["Ocean Vessel", "Port of Discharge", "INCHEON"]]
    assert "vessel" not in _parse_head(grid)


def test_multiline_table_cell_starting_with_labels():
    # PDF 표 칸: 첫 줄이 라벨, 다음 줄이 값들 → 어느 값이 모선인지 모르므로 비운다
    cell = (
        "Port of loading: Sailing Date: Place of Receipt:" + chr(10) + "VIRTUAL STAR V.001E PORT A"
    )
    assert "vessel" not in _parse_head([["Vessel & Voyage:", cell]])


def test_real_value_is_kept():
    assert (
        _parse_head([_line_to_cells("Vessel & Voyage: VIRTUAL STAR V.001E")])["vessel"]
        == "VIRTUAL STAR V.001E"
    )
    assert _parse_head([["Ocean Vessel", "VIRTUAL OCEAN 12W"]])["vessel"] == "VIRTUAL OCEAN 12W"


def test_looks_like_label():
    assert looks_like_label("Port of loading: Sailing Date:")
    assert looks_like_label("Place of Receipt")
    assert not looks_like_label("VIRTUAL STAR V.001E")
    assert not looks_like_label("BANGKOK PORT 2")
