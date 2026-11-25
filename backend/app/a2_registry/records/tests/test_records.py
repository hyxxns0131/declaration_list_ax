from datetime import date

from app.a2_registry.records.service import expires_on, is_expired, parse_record_cell


def test_parse_record_cell():
    assert parse_record_cell("202300233982 (2023.04.25)") == ("202300233982", date(2023, 4, 25))
    assert parse_record_cell("") == ("", None)


def test_valid_until_expiry_day():
    # 승인 2023-05-05 → 만료일 2028-05-05, 그날까지 사용 가능 (RULES 11-8)
    approved = date(2023, 5, 5)
    assert expires_on(approved, 5) == date(2028, 5, 5)
    assert not is_expired(approved, date(2028, 5, 5), 5)
    assert is_expired(approved, date(2028, 5, 6), 5)
