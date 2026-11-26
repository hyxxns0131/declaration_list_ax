"""GET /core/health(로그인 없이), GET /core/shippers, GET /core/integrations,
연결 상태(GET /core/connections, POST /core/connections/check, PUT /core/ai-choice). 담당: KHS"""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core import connections, llm
from app.core.auth.deps import require_login
from app.core.config import REPO_ROOT, get_settings
from app.core.errors import AppError
from app.core.storage import drive, gmail

router = APIRouter(prefix="/core", tags=["core"])
RULES_DIR = REPO_ROOT / "backend" / "rules" / "shippers"


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "llm_enabled": llm.ready(),
        "ai_provider": llm.current_provider(),
        "unipass_mode": s.unipass_mode,
        "supabase": bool(s.supabase_url and s.supabase_anon_key),
    }


@router.get("/integrations", dependencies=[Depends(require_login)])
def integrations() -> dict:
    """외부 연동 상태(키 값은 돌려주지 않는다). 화면 상단 안내용."""
    s = get_settings()
    mail_ok, mail_why = gmail.configured()
    d = drive.status()
    return {
        "llm": {"ok": llm.ready(), "reason": "" if llm.ready() else "AI 키 없음 또는 꺼짐"},
        "unipass": {
            "ok": s.unipass_mode == "live" and bool(s.unipass_cargo_api_key),
            "mode": s.unipass_mode,
            "fx": bool(s.unipass_fxrt_api_key),
        },
        "mfds": {"ok": bool(s.mfds_overseas_maker_api_key)},
        "drive": d,
        "gmail": {"ok": mail_ok, "reason": mail_why},
        "supabase": {"ok": bool(s.supabase_url and s.supabase_anon_key)},
    }


@router.get("/shippers", dependencies=[Depends(require_login)])
def shippers() -> list[dict]:
    """화주 목록(가명). rules/shippers/*.json의 shipper_id·display_name만 돌려준다."""
    out = []
    for p in sorted(RULES_DIR.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append(
            {
                "shipper_id": data.get("shipper_id", p.stem),
                "display_name": data.get("display_name", p.stem),
            }
        )
    return out


class CheckIn(BaseModel):
    service: str = "all"  # all 또는 connections.KEYS 중 하나


class AiChoiceIn(BaseModel):
    provider: str = "openai"  # OpenAI만 (HS 결정 11/26)
    model: str | None = None  # OpenAI 모델(버전)


@router.get("/connections", dependencies=[Depends(require_login)])
def connection_status() -> dict:
    """연결 표: 키가 있는지(네트워크 없음) + 마지막 검사 결과. 키 값은 돌려주지 않는다."""
    return connections.status()


@router.post("/connections/check", dependencies=[Depends(require_login)])
def connection_check(body: CheckIn) -> dict:
    """[연결 검사]: 실제로 접속해 본다. AI는 모델 목록만 받아 토큰을 쓰지 않는다."""
    keys = connections.KEYS if body.service == "all" else [body.service]
    if any(k not in connections.KEYS for k in keys):
        raise AppError("unknown_service", "알 수 없는 연결입니다.", 404)
    for k in keys:
        connections.check(k)
    return connections.status()


@router.put("/ai-choice", dependencies=[Depends(require_login)])
def ai_choice(body: AiChoiceIn) -> dict:
    """OpenAI 모델(버전) 저장(data/ai_choice.json). .env는 바꾸지 않는다. AI는 OpenAI만(HS 결정 11/26)."""
    if body.provider not in llm.PROVIDERS:
        raise AppError("unknown_provider", "AI는 OpenAI만 씁니다.", 422)
    if body.model is not None and not body.model.strip():
        raise AppError("empty_model", "모델 이름이 비었습니다.", 422)
    llm.save_choice(body.provider, body.model)
    return connections.status()
