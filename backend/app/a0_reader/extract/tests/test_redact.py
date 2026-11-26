"""스캔본·사진: 화주명을 가린 PNG만 보낸다(HS 결정 11/26). Windows 기본 OCR. 가상 이름만 쓴다. 담당: KHS"""

import sys
from io import BytesIO

import pytest

from app.a0_reader.extract import redact
from app.a0_reader.extract.redact import find_boxes, name_keys, redact_png


def _image() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    im = Image.new("RGB", (1400, 360), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("arial.ttf", 38)
    d.text((40, 40), "BILL OF LADING  B/L NO. VTST0000123", fill="black", font=f)
    d.text((40, 140), "CONSIGNEE: TEST TRADING CO., LTD.", fill="black", font=f)
    d.text((40, 240), "VESSEL: VIRTUAL STAR 101E", fill="black", font=f)
    buf = BytesIO()
    im.save(buf, format="JPEG")
    return buf.getvalue()


def test_name_keys_strip_company_form():
    assert name_keys(["Test Trading Co., Ltd."]) == ["TESTTRADINGCOLTD", "TESTTRADING"]
    assert name_keys(["", "A"]) == []


def test_find_boxes_spans_words():
    lines = [
        {
            "words": [
                {"text": "TO:", "x": 0, "y": 0, "w": 30, "h": 10},
                {"text": "TEST", "x": 40, "y": 0, "w": 40, "h": 10},
                {"text": "TRADING", "x": 90, "y": 0, "w": 70, "h": 10},
            ]
        }
    ]
    boxes = find_boxes(lines, ["TESTTRADING"])
    assert len(boxes) == 2 and boxes[0][0] == 40 - redact.PAD


def test_no_names_means_not_sent():
    assert redact_png(b"not used", []) is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 기본 OCR 필요")
def test_redact_real_ocr_blacks_out_name(tmp_path):
    from PIL import Image

    redact.SAVE_DIR = tmp_path
    try:
        out = redact_png(_image(), ["Test Trading Co., Ltd."])
    finally:
        redact.SAVE_DIR = None
    if out is None:
        pytest.skip("이 PC에서 OCR을 쓸 수 없음")
    im = Image.open(BytesIO(out))
    assert im.format == "PNG"
    assert im.getpixel((340, 165)) == (0, 0, 0)  # 'TEST' 자리
    assert im.getpixel((300, 265)) != (0, 0, 0)  # 모선 줄은 그대로
    assert list(tmp_path.glob("redacted_*.png"))
    # 이름이 없는 이미지는 보내지 않는다
    assert redact_png(_image(), ["Other Name Corp"]) is None
