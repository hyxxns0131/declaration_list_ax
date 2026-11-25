"""연결 상태·AI 모델 고르기 (탭 5. 연결 설정). 네트워크 없이 시험한다. 가상 키만 쓴다."""

import pytest

from app.core import connections, llm


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("AI_PROVIDER", "claude")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")
    monkeypatch.setenv("UNIPASS_MODE", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_choice_overrides_env(env):
    assert llm.current_provider() == "claude"
    llm.save_choice("openai")
    llm.save_choice("openai", "gpt-4o-mini")
    assert llm.current_provider() == "openai"
    assert llm.current_model() == "gpt-4o-mini"
    assert llm.ready() is True  # openai 키가 있으므로
    assert (env / "ai_choice.json").exists()


def test_bad_provider(env):
    with pytest.raises(ValueError):
        llm.save_choice("gemini")


def test_missing_key_is_off_without_network(env):
    r = connections.check("claude")
    assert r["state"] == "off" and "ANTHROPIC_API_KEY" in r["message"]
    r = connections.check("unipass")
    assert r["state"] == "off" and "mock" in r["message"]


def test_ai_check_marks_unavailable_model(env, monkeypatch):
    monkeypatch.setattr(connections, "_openai_models", lambda: ["gpt-4o-mini", "gpt-4o"])
    llm.save_choice("openai", "gpt-5")
    r = connections.check("openai")
    assert r["state"] == "fail" and "gpt-5" in r["message"]
    llm.save_choice("openai", "gpt-4o")
    assert connections.check("openai")["state"] == "ok"
    row = next(x for x in connections.status()["rows"] if x["key"] == "openai")
    avail = {m["id"]: m["available"] for m in row["ai"]["models"]}
    assert avail["gpt-4o-mini"] is True and avail["gpt-5"] is False
    assert row["last"]["state"] == "ok"


def test_ai_error_hides_details(env, monkeypatch):
    class AuthenticationError(Exception):
        pass

    def boom() -> list[str]:
        raise AuthenticationError("sk-secret-should-not-leak")

    monkeypatch.setattr(connections, "_openai_models", boom)
    r = connections.check("openai")
    assert r["state"] == "fail" and "sk-secret" not in r["message"]


def test_status_never_returns_keys(env):
    text = str(connections.status())
    assert "test-openai-key" not in text


def test_account_models_are_added_as_versions(env, monkeypatch):
    monkeypatch.setattr(
        connections,
        "_openai_models",
        lambda: [
            "gpt-4o",
            "gpt-4o-audio-preview",
            "gpt-9.9-test",
            "text-embedding-3-small",
            "dall-e-3",
            "whisper-1",
            "omni-moderation-latest",
            "gpt-4o-search-preview",
            "tts-1",
        ],
    )
    llm.save_choice("openai", "gpt-4o")
    connections.check("openai")
    row = next(x for x in connections.status()["rows"] if x["key"] == "openai")
    account = [m["id"] for m in row["ai"]["models"] if m["group"] == "account"]
    assert account == ["gpt-4o", "gpt-9.9-test"]  # 받은 순서(최신 먼저) 그대로, 글 대화 모델만
    assert row["ai"]["account_list"] is True


def test_no_key_shows_recommended_only(env):
    row = next(x for x in connections.status()["rows"] if x["key"] == "claude")
    groups = {m["group"] for m in row["ai"]["models"]}
    assert groups == {"recommended"} and row["ai"]["account_list"] is False


def test_custom_model_listed(env):
    llm.save_choice("openai", "gpt-custom-test")
    row = next(x for x in connections.status()["rows"] if x["key"] == "openai")
    assert {
        "id": "gpt-custom-test",
        "tier": "직접 입력",
        "group": "custom",
        "available": None,
    } in row["ai"]["models"]


class _M:
    def __init__(self, id: str, created: int) -> None:
        self.id, self.created = id, created


def test_openai_list_newest_first(env, monkeypatch):
    class FakeModels:
        def list(self):
            return [_M("gpt-4o", 1), _M("gpt-5", 3), _M("gpt-4.1", 2)]

    class FakeClient:
        def __init__(self, **_: object) -> None:
            self.models = FakeModels()

    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    assert connections._openai_models() == ["gpt-5", "gpt-4.1", "gpt-4o"]
