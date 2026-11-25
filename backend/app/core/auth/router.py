"""POST /core/auth/login, POST /core/auth/logout, GET /core/auth/me. 담당: KHS"""

from fastapi import APIRouter, Header

from app.core.auth import service
from app.core.auth.deps import bearer
from app.core.auth.models import LoginIn, LoginOut, MeOut
from app.core.config import get_settings

router = APIRouter(prefix="/core/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn) -> LoginOut:
    token, expires = service.login(body.username.strip(), body.password)
    return LoginOut(token=token, expires_at=expires, display_name=get_settings().admin_display_name)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    token = bearer(authorization)
    if token:
        service.logout(token)
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(authorization: str | None = Header(default=None)) -> MeOut:
    token = bearer(authorization)
    sess = service.session(token) if token else None
    if not sess:
        return MeOut(logged_in=False)
    return MeOut(
        logged_in=True,
        display_name=get_settings().admin_display_name,
        remote_data=bool(sess.get("remote_token")),
    )
