"""구글 시트·드라이브 시험 API. [시험] LSY-google-test. 네트워크 없이 가짜 응답만 쓴다. 가상 값만."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.storage import google_auth, sheets


@pytest.fixture()
def env(tmp_path, monkeypatch):
    token = tmp_path / "token.json"
    token.write_text(
        json.dumps(
            {
                "token": "fake-token",
                "refresh_token": "fake-refresh",
                "expiry": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    for k, v in {
        "DATA_DIR": str(tmp_path),
        "AUTH_ENABLED": "false",  # 자동 테스트에서만 (RULES 7-4)
        "GOOGLE_TOKEN_FILE": str(token),
        "GOOGLE_CREDENTIALS_FILE": str(tmp_path / "none.json"),
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "SPREADSHEET_ID": "TEST-SHEET",
        "ITEM_SPREADSHEET_ID": "",
        "DRIVE_INBOX_FOLDER_ID": "TEST-FOLDER",
        "DRIVE_LAW_FOLDER_ID": "",
    }.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def fake(monkeypatch, payload, status=200, seen=None):
    def _req(method, url, **kw):
        if seen is not None:
            seen.append((method, url, kw))
        return httpx.Response(status, json=payload, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", _req)


# --- client_config: .env 우선, 없으면 파일, 둘 다 없으면 None ---
def test_client_config_from_env(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "x.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "s")
    get_settings.cache_clear()
    cfg = google_auth.client_config()
    assert cfg["installed"]["client_id"] == "x.apps.googleusercontent.com"
    assert cfg["installed"]["redirect_uris"] == ["http://localhost:8080/"]


def test_client_config_file_fallback(env, monkeypatch):
    f = env / "cred.json"
    f.write_text(json.dumps({"installed": {"client_id": "file-id"}}), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_FILE", str(f))
    get_settings.cache_clear()
    assert google_auth.client_config()["installed"]["client_id"] == "file-id"


def test_client_config_none(env):
    assert google_auth.client_config() is None


# --- sheets ---
def test_read_values(env, monkeypatch):
    seen = []
    fake(monkeypatch, {"values": [["B/L Number", "모선명"], ["BL-DEMO-1", "VESSEL"]]}, seen=seen)
    got = sheets.read("history", "A기업!A1:B2")
    assert got[1] == ["BL-DEMO-1", "VESSEL"]
    method, url, kw = seen[0]
    assert method == "GET" and "TEST-SHEET" in url and "A%EA%B8%B0%EC%97%85" in url
    assert kw["headers"]["Authorization"] == "Bearer fake-token"


def test_write_raw(env, monkeypatch):
    seen = []
    fake(monkeypatch, {"updatedRange": "A기업!A2:B2", "updatedCells": 2}, seen=seen)
    got = sheets.write("history", "A기업!A2:B2", [["0012", "X"]])
    assert got == {"updated_range": "A기업!A2:B2", "updated_cells": 2}
    _, _, kw = seen[0]
    assert kw["params"]["valueInputOption"] == "RAW" and kw["json"]["values"] == [["0012", "X"]]


def test_sheet_not_configured(env):
    with pytest.raises(AppError) as e:
        sheets.read("item", "A1:B2")
    assert e.value.code == "sheet_not_configured"


def test_label_disabled_and_unknown(env):
    with pytest.raises(AppError) as e:
        sheets.read("label", "A1")
    assert e.value.code == "sheet_disabled"
    with pytest.raises(AppError) as e:
        sheets.read("nope", "A1")
    assert e.value.code == "unknown_sheet"


def test_google_error_message(env, monkeypatch):
    fake(monkeypatch, {"error": {"message": "Requested entity was not found."}}, status=404)
    with pytest.raises(AppError) as e:
        sheets.read("history", "A1")
    assert e.value.status == 502 and "404" in e.value.message


def test_login_required(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_FILE", str(env / "missing.json"))
    get_settings.cache_clear()
    with pytest.raises(AppError) as e:
        sheets.read("history", "A1")
    assert e.value.code == "google_login_required"


# --- API ---
def test_api_status_hides_ids(env):
    from app.main import app

    body = TestClient(app).get("/api/core/google/status").json()
    assert body["login"]["ok"] is True and body["sheets"]["history"]["ok"] is True
    assert body["sheets"]["item"]["ok"] is False and body["sheets"]["label"]["ok"] is False
    assert "TEST-SHEET" not in json.dumps(body) and "TEST-FOLDER" not in json.dumps(body)


def test_api_read_and_drive(env, monkeypatch):
    from app.main import app

    fake(monkeypatch, {"values": [["a"]]})
    c = TestClient(app)
    assert c.get("/api/core/google/sheets/history", params={"range": "A1"}).json()["values"] == [
        ["a"]
    ]

    def _get(url, **kw):
        files = [
            {"id": "f1", "name": "BL-DEMO-1", "mimeType": "application/vnd.google-apps.folder"}
        ]
        return httpx.Response(200, json={"files": files}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", _get)
    got = c.get("/api/core/google/drive/inbox").json()
    assert got["items"] == [{"name": "BL-DEMO-1", "is_folder": True}]
    assert c.get("/api/core/google/drive/law").status_code == 409
