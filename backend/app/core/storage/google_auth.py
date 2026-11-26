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


# ─── 처음 로그인 (InstalledAppFlow) ─── [시험] LSY-google-test, PR하지 않음
# 권한 범위: 드라이브(접수 폴더 읽기·업로드·이동), 시트 읽기·쓰기, Gmail 보내기(만료 알림, 기존 gmail.py)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]


def client_config() -> dict | None:
    """OAuth 클라이언트 정보. .env(GOOGLE_CLIENT_*)가 있으면 메모리 딕셔너리로 만들고,
    없으면 기존 credentials.json 파일을 읽는다. 둘 다 없으면 None. 값은 로그에 남기지 않는다."""
    s = get_settings()
    if s.google_client_id and s.google_client_secret:
        return {
            s.google_client_type or "installed": {
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "auth_uri": s.google_auth_uri,
                "token_uri": s.google_token_uri,
                "redirect_uris": [s.google_redirect_uri],
            }
        }
    path = s.path(s.google_credentials_file)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _redirect_port() -> int:
    from urllib.parse import urlparse

    return urlparse(get_settings().google_redirect_uri).port or 8080


def login(open_browser: bool = True) -> str:
    """브라우저로 구글 로그인 → token.json 저장(기존 형식). 사람이 PC에서 한 번 실행한다.
    돌려주는 값: 저장한 token.json 경로."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    cfg = client_config()
    if cfg is None:
        raise RuntimeError(
            ".env에 GOOGLE_CLIENT_ID·GOOGLE_CLIENT_SECRET이 없고 credentials.json도 없음"
        )
    flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
    creds = flow.run_local_server(port=_redirect_port(), open_browser=open_browser)
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json(), encoding="utf-8")
    return str(path)
