"""로그인 규칙 (RULES 7-4). Supabase 없이 .env 값으로 확인하는 경로를 시험한다."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("ADMIN_USERNAME", "test_admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_health_without_login(client):
    assert client.get("/api/core/health").json()["ok"] is True


def test_other_api_needs_login(client):
    r = client.get("/api/core/shippers")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_login_logout(client):
    r = client.post(
        "/api/core/auth/login", json={"username": "test_admin", "password": "test-password-123"}
    )
    assert r.status_code == 200
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/core/auth/me", headers=h).json()["logged_in"] is True
    assert client.get("/api/core/shippers", headers=h).status_code == 200
    client.post("/api/core/auth/logout", headers=h)
    assert client.get("/api/core/auth/me", headers=h).json()["logged_in"] is False


def test_wrong_password_does_not_say_which(client):
    r = client.post("/api/core/auth/login", json={"username": "test_admin", "password": "x"})
    assert r.status_code == 401
    assert r.json()["error"]["message"] == "아이디 또는 비밀번호가 맞지 않습니다."


def test_lock_after_five_failures(client):
    for _ in range(5):
        client.post("/api/core/auth/login", json={"username": "test_admin", "password": "x"})
    r = client.post(
        "/api/core/auth/login", json={"username": "test_admin", "password": "test-password-123"}
    )
    assert r.status_code == 429
