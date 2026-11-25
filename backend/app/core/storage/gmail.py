"""Gmail: 실적 만료 알림 메일 발송 (A2-3이 사용). 담당: KHS

token.json(구글 로그인)과 GMAIL_SENDER·ALERT_EMAIL_TO가 모두 있어야 보낸다. 하나라도 없으면
configured()가 이유를 돌려주고 화면의 [알림 메일 보내기]가 비활성 + "메일 계정을 설정하세요"(DESIGN 6장).
같은 실적·같은 단계 1번만은 호출하는 쪽(a2_registry/alerts)이 alerts_sent로 지킨다.
"""

import base64
from email.message import EmailMessage

import httpx

from app.core.config import get_settings
from app.core.storage import google_auth

SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def recipients() -> list[str]:
    return [a.strip() for a in get_settings().alert_email_to.split(",") if a.strip()]


def configured() -> tuple[bool, str]:
    s = get_settings()
    if not s.gmail_sender:
        return False, "GMAIL_SENDER 없음"
    if not recipients():
        return False, "ALERT_EMAIL_TO 없음"
    if not google_auth.configured():
        return False, "token.json 없음(구글 로그인 필요)"
    return True, ""


def send(subject: str, body: str) -> tuple[bool, str]:
    ok, why = configured()
    if not ok:
        return False, why
    h = google_auth.headers()
    if not h:
        return False, "구글 토큰 갱신 실패"
    msg = EmailMessage()
    msg["From"] = get_settings().gmail_sender
    msg["To"] = ", ".join(recipients())
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        r = httpx.post(SEND_URL, json={"raw": raw}, headers=h, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return False, f"메일 발송 실패({type(e).__name__})"
    return True, ""
