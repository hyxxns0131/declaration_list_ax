"""구글 OAuth 토큰(token.json) 읽기·갱신. 드라이브·Gmail이 같이 쓴다. 담당: KHS

token.json은 기존 도구와 같은 형식(google-auth의 authorized user 파일: token, refresh_token, token_uri,
client_id, client_secret, expiry). 파일이 없으면 None → 연동을 끄고 로컬 사본만 둔다.
토큰 값은 로그에 남기지 않는다.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import get_settings

DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _token_path():
    return get_settings().path(get_settings().google_token_file)


def configured() -> bool:
    return _token_path().exists()


def _expired(expiry: str | None) -> bool:
    if not expiry:
        return True
    try:
        t = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    except ValueError:
        return True
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t - timedelta(minutes=2) <= datetime.now(UTC)


def access_token() -> str | None:
    path = _token_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("token") and not _expired(data.get("expiry")):
        return data["token"]
    if not data.get("refresh_token"):
        return None
    try:
        r = httpx.post(
            data.get("token_uri") or DEFAULT_TOKEN_URI,
            data={
                "client_id": data.get("client_id", ""),
                "client_secret": data.get("client_secret", ""),
                "refresh_token": data["refresh_token"],
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        r.raise_for_status()
        got = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    data["token"] = got["access_token"]
    data["expiry"] = (
        datetime.now(UTC) + timedelta(seconds=int(got.get("expires_in", 3600)))
    ).isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")
    return data["token"]


def headers() -> dict[str, str] | None:
    tok = access_token()
    return {"Authorization": f"Bearer {tok}"} if tok else None
