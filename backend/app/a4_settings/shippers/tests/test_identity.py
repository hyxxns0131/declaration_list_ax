"""통관고유부호·별칭 정규화·형식 검사, 내부 id 생성 (순수 함수). 가상 TEST 부호만 쓴다."""

import json

import pytest

from app.a4_settings.engine.service import RULES_DIR
from app.a4_settings.shippers import identity as idt

CFG = json.loads((RULES_DIR / "customs_code.json").read_text(encoding="utf-8"))


def test_normalize():
    assert idt.normalize_code("  test000000004 ") == "TEST000000004"
    assert idt.normalize_alias(" d ") == "D"
    assert idt.normalize_code(None) == ""


@pytest.mark.parametrize(
    "env,dev", [("local", True), ("demo", True), ("DEMO", True), ("prod", False)]
)
def test_is_dev(env, dev):
    assert idt.is_dev(env, CFG) is dev


def test_dev_code_format():
    assert idt.check_code_format("TEST000000003", True, CFG) is None
    assert idt.check_code_format("", True, CFG) == idt.REQUIRED
    for bad in ("TEST00000003", "TEST0000000031", "ABCD000000003", "TEST00000000A"):
        assert idt.check_code_format(bad, True, CFG) == idt.FORMAT


def test_prod_blocks_test_and_unknown_format():
    assert idt.check_code_format("TEST000000003", False, CFG) == idt.PROD_TEST_BLOCKED
    assert (
        idt.check_code_format("ABCDE1234567890", False, CFG) == idt.PROD_NOT_READY
    )  # prod_pattern 미확정
    cfg = {**CFG, "prod_pattern": "^[A-Z0-9]{15}$"}
    assert idt.check_code_format("ABCDE1234567890", False, cfg) is None
    assert idt.check_code_format("ABC", False, cfg) == idt.FORMAT


def test_alias_format():
    for ok in ("C", "AA", "AB", "ZZZ"):
        assert idt.check_alias_format(ok, CFG) is None
    assert idt.check_alias_format("", CFG) == idt.REQUIRED
    for bad in ("C1", "씨", "ABCD", "C사", "A B"):
        assert idt.check_alias_format(bad, CFG) == idt.FORMAT


def test_next_id():
    assert idt.next_shipper_id([]) == "S0003"
    assert idt.next_shipper_id([3, 7]) == "S0008"
    assert idt.parse_seq("S0012", "S") == 12
    assert idt.parse_seq("A", "S") is None
    assert idt.display_name("C") == "C사"
