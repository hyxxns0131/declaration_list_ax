"""PC 안 OCR 글자로 B/L 번호 후보 찾기 (HS 11/27). 가상 값만 쓴다. 담당: KHS"""

from app.a0_reader.extract.scan_local import bl_from_lines


def test_bl_after_label_keeps_letters():
    lines = ["BILL OF LADING", "B/L No.", "ABCDZ0000001", "CONTAINER TEMU1234567"]
    assert bl_from_lines(lines) == "ABCDZ0000001"


def test_bl_skips_container_and_short_tokens():
    assert bl_from_lines(["TEMU1234567 SEAL", "INVOICE ABCDEF", "WXYZ12345678"]) == "WXYZ12345678"


def test_bl_none():
    assert bl_from_lines(["SHIPPER", "CONSIGNEE"]) == ""
