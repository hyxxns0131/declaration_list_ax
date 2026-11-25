from app.a0_reader.classify.service import classify, classify_by_content, classify_by_name


def test_by_name():
    assert classify_by_name("CI.xlsx") == "CI"
    assert classify_by_name("BLTEST001 Packing List.xlsx") == "PL"
    assert classify_by_name("B-L_copy.pdf") == "BL"
    assert classify_by_name("원산지증명서.pdf") == "CO"
    assert classify_by_name("photo_RC-100.jpg") == "PHOTO"


def test_short_token_needs_exact_piece():
    # 'cinema'에 ci가 들어 있어도 CI가 아니다
    assert classify_by_name("cinema.xlsx") is None


def test_by_content():
    assert classify_by_content("COMMERCIAL INVOICE\nInvoice No.") == "CI"
    assert classify_by_content("BILL OF LADING") == "BL"
    assert classify("scan001.pdf", "CERTIFICATE OF ORIGIN") == "CO"
