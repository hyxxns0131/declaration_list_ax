"""로그인: 프로그램 계정 1개(.env ADMIN_USERNAME), Supabase 로그인 계정과 같음 (RULES 7-4). 담당: KHS

확인 순서
1. SUPABASE_URL·키가 있으면 Supabase Auth(<username>@declaration.local)로 확인 → 그 토큰을 세션에 둔다
   (고객사 자료 samc_* 읽기에 씀).
2. Supabase를 못 쓰면(키 없음·오프라인) .env의 ADMIN_USERNAME·ADMIN_PASSWORD와 비교한다.
비밀번호·토큰 평문은 로그·audit_log에 남기지 않는다. 세션 토큰은 해시만 저장한다.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.storage import local_db

EMAIL_DOMAIN = "declaration.local"
BAD_LOGIN = "아이디 또는 비밀번호가 맞지 않습니다."


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _hash(token: str) -> str:
    key = (get_settings().auth_secret_key or "dev-only").encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def _check_lock(username: str) -> None:
    with local_db.transaction() as conn:
        row = conn.execute(
            "select locked_until from login_failures where username=?", (username,)
        ).fetchone()
    if row and row["locked_until"] and row["locked_until"] > _iso(_now()):
        minutes = get_settings().auth_lock_minutes
        raise AppError("locked", f"{minutes}분 뒤 다시 시도하세요.", 429)


def _record_failure(username: str) -> None:
    s = get_settings()
    with local_db.transaction() as conn:
        conn.execute(
            "insert into login_failures(username, count) values (?, 1) "
            "on conflict(username) do update set count = count + 1",
            (username,),
        )
        count = conn.execute(
            "select count from login_failures where username=?", (username,)
        ).fetchone()["count"]
        if count >= s.auth_max_failures:
            until = _iso(_now() + timedelta(minutes=s.auth_lock_minutes))
            conn.execute(
                "update login_failures set count=0, locked_until=? where username=?",
                (until, username),
            )


def _supabase_login(username: str, password: str) -> str | None:
    """성공하면 access_token, 틀리면 None. Supabase를 못 쓰면 예외."""
    s = get_settings()
    r = httpx.post(
        f"{s.supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": s.supabase_anon_key},
        json={"email": f"{username}@{EMAIL_DOMAIN}", "password": password},
        timeout=15,
    )
    if r.status_code == 200:
        return r.json()["access_token"]
    if r.status_code in (400, 401):
        return None
    raise httpx.HTTPError(f"supabase {r.status_code}")


def _local_login(username: str, password: str) -> bool:
    s = get_settings()
    if not s.admin_username or not s.admin_password:
        raise AppError("auth_not_set", ".env에 ADMIN_USERNAME·ADMIN_PASSWORD가 없습니다.", 503)
    return hmac.compare_digest(username, s.admin_username) and hmac.compare_digest(
        password, s.admin_password
    )


def login(username: str, password: str) -> tuple[str, str]:
    """(세션 토큰, 만료 시각)을 돌려준다."""
    s = get_settings()
    _check_lock(username)
    remote_token: str | None = None
    ok = False
    if s.supabase_url and s.supabase_anon_key:
        try:
            remote_token = _supabase_login(username, password)
            ok = remote_token is not None
        except httpx.HTTPError:
            ok = _local_login(username, password)  # 오프라인: .env로 확인
    else:
        ok = _local_login(username, password)
    if not ok:
        _record_failure(username)
        local_db.audit("login_failed", username)
        raise AppError("bad_login", BAD_LOGIN, 401)

    token = secrets.token_urlsafe(32)
    expires = _iso(_now() + timedelta(hours=s.auth_session_hours))
    with local_db.transaction() as conn:
        conn.execute("delete from login_failures where username=?", (username,))
        conn.execute(
            "insert into sessions(token_hash, remote_token, expires_at) values (?, ?, ?)",
            (_hash(token), remote_token, expires),
        )
    local_db.audit("login", username)
    return token, expires


def session(token: str) -> dict | None:
    """유효한 세션이면 {"remote_token": ...}, 아니면 None."""
    with local_db.transaction() as conn:
        row = conn.execute(
            "select remote_token, expires_at from sessions where token_hash=?", (_hash(token),)
        ).fetchone()
    if not row or row["expires_at"] <= _iso(_now()):
        return None
    return {"remote_token": row["remote_token"]}


def logout(token: str) -> None:
    with local_db.transaction() as conn:
        conn.execute("delete from sessions where token_hash=?", (_hash(token),))
    local_db.audit("logout")
