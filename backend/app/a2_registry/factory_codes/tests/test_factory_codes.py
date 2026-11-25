"""해외제조업소 코드 갱신 (A2-5, RULES 11-8-1). 가상 코드만 쓴다."""

from datetime import date

import pytest

from app.a2_registry.factory_codes.service import expires_on, status_for

STAGES = [90, 30]


def test_expires_two_years_after_registration():
    assert expires_on(date(2025, 1, 10), 2) == date(2027, 1, 10)
    assert expires_on(date(2024, 2, 29), 2) == date(2026, 2, 28)


def test_status_stages():
    reg = date(2025, 1, 10)  # 만료 2027-01-10
    assert status_for(reg, date(2026, 6, 1), STAGES)[0] == "유효"
    s, exp, days = status_for(reg, date(2026, 11, 1), STAGES)  # 70일 전 → 3개월 단계
    assert (s, exp, days) == ("만료 임박", date(2027, 1, 10), 70)
    assert status_for(reg, date(2026, 12, 20), STAGES)[2] == 21  # 1개월 단계
    assert status_for(reg, date(2027, 1, 10), STAGES)[0] == "만료 임박"  # 만료일 당일까지 유효
    assert status_for(reg, date(2027, 1, 11), STAGES)[0] == "만료"


def test_unknown_registration_is_check_needed():
    assert status_for(None, date(2026, 11, 25), STAGES) == ("확인 필요", None, None)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ALERT_DAYS_BEFORE", "90,30")
    monkeypatch.setenv("FACTORY_CODE_VALID_YEARS", "2")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.core.storage import local_db

    local_db.migrate()
    yield
    get_settings.cache_clear()


def test_list_marks_unknown_and_alert_sent_once(db, monkeypatch):
    from app.a2_registry.alerts import service as alerts
    from app.a2_registry.factory_codes import service
    from app.core.storage import gmail

    today = date(2026, 11, 25)
    rows = {f.code: f for f in service.list_factories(today=today)}
    assert rows, "samples/mfds/factories.json 가상 코드가 보여야 한다"
    code = sorted(rows)[0]
    assert rows[code].status == "확인 필요" and rows[code].expires_on is None

    # 등록일 2024-12-20 → 만료 2026-12-20, 25일 남음 → 1개월 단계
    got = service.update_registered_on(code, "2024-12-20", today=today)
    assert (got.expires_on, got.status, got.days_left) == ("2026-12-20", "만료 임박", 25)

    items = [a for a in alerts.expiring(None, today=today) if a.kind == "factory_code"]
    assert [(a.record_no, a.stage, a.sent) for a in items] == [(code, 30, False)]

    sent_mail: list[str] = []
    monkeypatch.setattr(gmail, "configured", lambda: (True, ""))
    monkeypatch.setattr(gmail, "send", lambda subject, body: (sent_mail.append(body) or True, ""))
    monkeypatch.setattr(gmail, "recipients", lambda: ["test@example.com"])
    assert alerts.send(None, "전체", today=today)["sent"] >= 1
    assert "[해외제조업소 코드]" in sent_mail[0]
    # 같은 코드·같은 단계는 다시 보내지 않는다
    assert alerts.send(None, "전체", today=today)["sent"] == 0
