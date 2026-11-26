"""화주명 목록 자동 만들기(HS 결정 11/26: DB에서 끌고 오기). 가짜 Supabase 응답·가짜 이름만. 담당: KHS"""

import json

import pytest

from app.core import llm, mask_names, masking

FILES = [
    {"path": "a/1/BL.pdf", "shipper": "A기업", "category": "shipping_docs"},
    {"path": "b/1/BL.pdf", "shipper": "B기업", "category": "shipping_docs"},
]
TEXTS = [
    {
        "path": "a/1/BL.pdf",
        "text": "SHIPPER: ZETA FACTORY CO., LTD.\nCONSIGNEE: QWERTY HOLDINGS CO., LTD.\nPORT OF LOADING: NINGBO",
    },
    {"path": "b/1/BL.pdf", "text": "CONSIGNEE: YUIOP MART INC.\nNOTIFY PARTY: SAME AS CONSIGNEE"},
]


@pytest.fixture
def fake_db(monkeypatch, tmp_path):
    f = tmp_path / "mask_names.json"
    monkeypatch.setattr(masking, "mask_file", lambda: f)
    monkeypatch.setattr(mask_names, "mask_file", lambda: f)
    monkeypatch.setattr(mask_names, "_auto_enabled", lambda: True)
    monkeypatch.setattr(mask_names, "_login", lambda: "tok")
    monkeypatch.setattr(mask_names, "_state", {"last_try": 0.0, "last_error": ""})

    def select(table, params, token):
        return {"samc_files": FILES, "samc_texts": TEXTS, "samc_sheet_rows": []}[table]

    monkeypatch.setattr(mask_names, "_select", select)
    return f


def test_builds_file_from_db_without_returning_names(fake_db):
    n = mask_names.ensure()
    data = json.loads(fake_db.read_text(encoding="utf-8"))
    assert set(data) == {"A", "B"}
    assert "QWERTY HOLDINGS CO" in data["A"] and "QWERTY HOLDINGS" in data["A"]
    assert "YUIOP MART" in data["B"]  # 회사 형태(INC.)를 뺀 이름도 들어간다
    assert not any("ZETA" in x for v in data.values() for x in v)  # 수출자는 빼기
    assert n == sum(len(v) for v in data.values())
    st = mask_names.status()
    assert st["exists"] and st["count"] == n and st["shippers"] == 2
    assert "QWERTY" not in json.dumps(st)  # 상태에는 이름이 없다


def test_login_failure_keeps_ai_blocked(fake_db, monkeypatch):
    monkeypatch.setattr(mask_names, "_login", lambda: None)
    assert mask_names.ensure() == 0 and not fake_db.exists()
    assert "로그인" in mask_names.status()["last_error"]
    monkeypatch.setattr(llm, "ready", lambda: True)
    assert not llm.send_allowed()


def test_network_error_keeps_ai_blocked(fake_db, monkeypatch):
    def boom(*a, **k):
        raise OSError("network")

    monkeypatch.setattr(mask_names, "_select", boom)
    assert mask_names.ensure() == 0 and not fake_db.exists()


def test_llm_builds_list_once_then_sends_masked(fake_db, monkeypatch):
    monkeypatch.setattr(llm, "ready", lambda: True)
    sent: list[str] = []
    monkeypatch.setattr(
        llm, "_ask", lambda s, u, images=None: (sent.append(u) or '{"ok": true}', {})
    )
    monkeypatch.setattr(llm, "_log", lambda *a, **k: None)
    monkeypatch.setattr(llm, "load_prompt", lambda n, v: "프롬프트")
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool = True

    assert (
        llm.call_structured("x", 1, {"text": "CONSIGNEE: QWERTY HOLDINGS CO., LTD."}, Out)
        is not None
    )
    assert fake_db.exists() and "QWERTY" not in sent[0]
