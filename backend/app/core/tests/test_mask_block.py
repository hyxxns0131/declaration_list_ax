"""임시 안전 조치(11/26): PC 전용 화주명 목록(DATA_DIR/mask_names.json)이 없으면 OpenAI로 보내지 않는다.
목록이 있으면 모든 화주 이름을 가린 뒤 보낸다. 가짜 이름(A기업·B기업)만 쓴다. 담당: KHS"""

import json

from pydantic import BaseModel

from app.core import llm, masking


class _Out(BaseModel):
    ok: bool = True


def _setup(monkeypatch, tmp_path, names: object | None) -> list[str]:
    f = tmp_path / "mask_names.json"
    if names is not None:
        f.write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(masking, "mask_file", lambda: f)
    monkeypatch.setattr(llm, "ready", lambda: True)
    sent: list[str] = []
    monkeypatch.setattr(
        llm, "_ask", lambda system, user, images=None: (sent.append(user) or '{"ok": true}', {})
    )
    monkeypatch.setattr(llm, "_log", lambda *a, **k: None)
    monkeypatch.setattr(llm, "load_prompt", lambda name, v: "프롬프트")
    return sent


def test_no_list_means_nothing_sent(monkeypatch, tmp_path):
    sent = _setup(monkeypatch, tmp_path, None)
    assert llm.call_structured("x", 1, {"text": "A기업 서류"}, _Out) is None
    assert sent == [] and not llm.send_allowed()


def test_empty_or_broken_list_means_nothing_sent(monkeypatch, tmp_path):
    sent = _setup(monkeypatch, tmp_path, {"A": []})
    assert llm.call_structured("x", 1, {"text": "A기업"}, _Out) is None and sent == []
    (tmp_path / "mask_names.json").write_text("{깨짐", encoding="utf-8")
    assert masking.load_names() == {} and not llm.send_allowed()


def test_list_masks_every_shipper_before_sending(monkeypatch, tmp_path):
    sent = _setup(monkeypatch, tmp_path, {"A": ["A기업", "A Trading"], "B": ["B기업"]})
    assert llm.send_allowed()
    out = llm.call_structured("x", 1, {"text": "CONSIGNEE: A TRADING / 통지: B기업"}, _Out)
    assert out is not None and len(sent) == 1
    assert "A TRADING" not in sent[0].upper() and "B기업" not in sent[0]
    assert sent[0].count("[화주]") == 2


def test_plain_array_is_common_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, ["A기업"])
    assert masking.all_names() == ["A기업"]


def test_short_name_masks_whole_word_only():
    out = masking.mask_text("QWER TRADING / QWERTY STEPPER / qwer", ["QWER"])
    assert out == "[화주] TRADING / QWERTY STEPPER / [화주]"
