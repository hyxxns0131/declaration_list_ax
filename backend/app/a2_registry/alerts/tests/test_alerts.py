"""만료 알림 단계(3개월·1개월 전, 미팅 11/24)."""

from app.a2_registry.alerts.service import stage_for
from app.core.fx import convert_to_usd


def test_stage():
    assert stage_for(25, [90, 30]) == 30
    assert stage_for(60, [90, 30]) == 90
    assert stage_for(120, [90, 30]) is None
    assert stage_for(-1, [90, 30]) is None


def test_usd_conversion_via_krw():
    rates = {"USD": {"rate": 1400.0, "unit": 1}, "CNY": {"rate": 200.0, "unit": 1}}
    assert convert_to_usd(700, "CNY", rates) == (100.0, "")
    assert convert_to_usd(5, "USD", {}) == (5, "")
    assert convert_to_usd(5, "EUR", rates)[0] is None
