"""GET /core/health(로그인 없이), GET /core/shippers, GET /core/integrations. 담당: KHS"""

import json

from fastapi import APIRouter, Depends

from app.core import llm
from app.core.auth.deps import require_login
from app.core.config import REPO_ROOT, get_settings
from app.core.storage import drive, gmail

router = APIRouter(prefix="/core", tags=["core"])
RULES_DIR = REPO_ROOT / "backend" / "rules" / "shippers"


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "llm_enabled": llm.ready(),
        "ai_provider": s.ai_provider,
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
