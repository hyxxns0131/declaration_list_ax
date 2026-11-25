"""require_login: main.py가 기능 라우터에 한 번에 건다. 기능 폴더에서 따로 확인하지 않는다. 담당: KHS"""

from fastapi import Header, Request

from app.core.auth import service
from app.core.config import get_settings
from app.core.errors import AppError


def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def require_login(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """로그인 세션을 확인하고 request.state.session에 둔다. 없으면 401 → 화면은 /login."""
    if not get_settings().auth_enabled:  # 자동 테스트에서만 (RULES 7-4)
        request.state.session = {"remote_token": None}
        return request.state.session
    token = bearer(authorization)
    sess = service.session(token) if token else None
    if not sess:
        raise AppError("unauthorized", "로그인이 필요합니다.", 401)
    request.state.session = sess
    return sess
