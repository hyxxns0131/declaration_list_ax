"""연결 상태·AI 모델 고르기 (탭 6. 연결 설정). AI는 OpenAI만(HS 결정 11/26). 네트워크 없이 시험한다. 가상 키만 쓴다."""

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


def test_openai_only_even_if_env_says_claude(env):
    # 예전 .env의 AI_PROVIDER=claude는 무시된다
    assert llm.current_provider() == "openai"
    assert llm.current_model() == llm.DEFAULT_OPENAI_MODEL
    llm.save_choice("openai", "gpt-4o-mini")
    assert llm.current_model() == "gpt-4o-mini"
    assert llm.ready() is True  # OPENAI_API_KEY가 있으므로
    assert (env / "ai_choice.json").exists()


def test_old_claude_choice_is_ignored(env):
    (env / "ai_choice.json").write_text(
        '{"provider": "claude", "models": {"claude": "claude-x", "openai": "gpt-4o"}}',
        encoding="utf-8",
    )
    assert llm.current_provider() == "openai" and llm.current_model() == "gpt-4o"


@pytest.mark.parametrize("provider", ["claude", "gemini"])
def test_other_provider_refused(env, provider):
    with pytest.raises(ValueError):
        llm.save_choice(provider, "x")


def test_no_claude_connection(env):
    keys = [r["key"] for r in connections.status()["rows"]]
    assert "claude" not in keys and keys[0] == "openai"


def test_missing_key_is_off_without_network(env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    r = connections.check("openai")
    assert r["state"] == "off" and "OPENAI_API_KEY" in r["message"]
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


def test_no_check_yet_shows_recommended_only(env):
    row = next(x for x in connections.status()["rows"] if x["key"] == "openai")
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
