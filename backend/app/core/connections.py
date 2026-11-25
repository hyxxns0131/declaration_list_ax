"""외부 연결 상태와 [연결 검사]. 화면: 탭 5. 연결 설정. 담당: KHS [신규] (C-1 공통, HS 요청 11/25)

- status(): 네트워크 없이 키가 .env에 있는지만 본다 + 마지막 검사 결과(data/connection_checks.json).
- check(key): 실제로 한 번 접속해 본다. AI는 모델 목록만 받으므로 토큰을 쓰지 않는다.
- 키·토큰 값은 응답·로그·파일 어디에도 남기지 않는다. 오류 글도 종류만 남긴다.
"""

import json
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

import httpx

from app.core import llm
from app.core.config import get_settings
from app.core.fx import FX_URL, IMPORT, parse_rates
from app.core.mfds import BASE_URL as MFDS_BASE
from app.core.mfds import MAKER_PATH
from app.core.storage import drive, gmail, google_auth

KST = timezone(timedelta(hours=9))  # Windows에 tzdata가 없어도 동작
TIMEOUT = 15.0

# (key, 이름, 어디에 쓰나). 화면 순서 그대로
SERVICES: list[tuple[str, str, str]] = [
    ("openai", "OpenAI (GPT)", "서류 판독(스캔 PDF·사진), AI 재질 판단 보조"),
    ("claude", "Claude (Anthropic)", "서류 판독, AI 재질 판단 보조 (OpenAI 대신 쓸 때)"),
    ("unipass", "관세청 유니패스", "반입 상태·반입일, 관세환율(USD 가격 계산)"),
    ("mfds", "식약처 공공데이터", "해외제조업소 코드·수입신고 접수 업체 조회"),
    ("foodsafety", "식품안전나라", "기구·용기·포장 공전 자료"),
    ("law", "법제처 OPEN API", "법령·고시 개정 확인"),
    ("supabase", "Supabase", "공개 기준 자료(재질 코드·공전) 읽기"),
    ("drive", "구글 드라이브", "서류 사본 저장, 처리완료 폴더 이동"),
    ("gmail", "Gmail", "만료 알림 메일 보내기"),
]
KEYS = [k for k, _, _ in SERVICES]


def _results_path():
    return get_settings().data_path / "connection_checks.json"


def _load_results() -> dict:
    p = _results_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_result(key: str, result: dict) -> None:
    data = _load_results()
    data[key] = result
    _results_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 1. 키가 있는지만 (네트워크 없음) ─────────────────────────────


def configured(key: str) -> tuple[bool, str]:
    s = get_settings()
    if key in ("openai", "claude"):
        env = "OPENAI_API_KEY" if key == "openai" else "ANTHROPIC_API_KEY"
        if not llm.api_key(key):
            return False, f"{env} 없음 (.env에 넣고 백엔드를 다시 켜세요)"
        if not s.llm_enabled:
            return False, "LLM_ENABLED=false (AI 꺼짐)"
        return True, ""
    if key == "unipass":
        if s.unipass_mode != "live":
            return False, "가상 자료(mock) 모드 — UNIPASS_MODE=live로 바꾸면 실제 조회"
        if not (s.unipass_cargo_api_key or s.unipass_fxrt_api_key):
            return False, "UNIPASS_*_API_KEY 없음"
        return True, ""
    if key == "mfds":
        return (True, "") if s.mfds_overseas_maker_api_key else (False, "MFDS_*_API_KEY 없음")
    if key == "foodsafety":
        return (True, "") if s.foodsafety_api_key else (False, "FOODSAFETY_API_KEY 없음")
    if key == "law":
        return (True, "") if s.law_api_oc else (False, "LAW_API_OC 없음")
    if key == "supabase":
        if s.supabase_url and s.supabase_anon_key:
            return True, ""
        return False, "SUPABASE_URL 또는 SUPABASE_ANON_KEY 없음"
    if key == "drive":
        d = drive.status()
        return bool(d["ok"]), str(d.get("reason", ""))
    if key == "gmail":
        return gmail.configured()
    return False, "알 수 없는 연결"


# ── 2. 실제 접속 검사 ────────────────────────────────────────────


def _openai_models() -> list[str]:
    from openai import OpenAI

    client = OpenAI(api_key=llm.api_key("openai"), timeout=TIMEOUT, max_retries=0)
    models = sorted(client.models.list(), key=lambda m: getattr(m, "created", 0) or 0, reverse=True)
    return [m.id for m in models]  # 최신 버전이 먼저


def _claude_models() -> list[str]:
    import anthropic

    client = anthropic.Anthropic(api_key=llm.api_key("claude"), timeout=TIMEOUT, max_retries=0)
    models = sorted(
        client.models.list(limit=100), key=lambda m: str(getattr(m, "created_at", "")), reverse=True
    )
    return [m.id for m in models]  # 최신 버전이 먼저


def _ai_error(e: Exception) -> str:
    name = type(e).__name__
    if "Authentication" in name or "PermissionDenied" in name:
        return "API 키가 맞지 않습니다 (키를 다시 확인하세요)"
    if "RateLimit" in name:
        return "사용 한도 초과 또는 결제 필요 (요금·한도 확인)"
    if "Connection" in name or "Timeout" in name:
        return "인터넷 연결 실패 또는 응답 없음"
    return f"연결 실패 ({name})"


def _check_ai(key: str) -> tuple[bool, str, dict]:
    try:
        ids = _openai_models() if key == "openai" else _claude_models()
    except Exception as e:  # SDK 오류 종류가 많다 — 종류 이름만 남긴다
        return False, _ai_error(e), {}
    model = llm.current_model(key)
    extra = {"available_models": ids}
    if ids and model not in ids:
        return False, f"연결은 됐지만 고른 모델 '{model}'을 이 계정에서 쓸 수 없습니다", extra
    return True, f"연결됨 · 모델 {model}", extra


def _http_ok(r: httpx.Response) -> None:
    r.raise_for_status()


def _check_unipass() -> tuple[bool, str, dict]:
    s = get_settings()
    if not s.unipass_fxrt_api_key:
        return True, "키 있음 (환율 키가 없어 실제 조회는 건너뜀)", {}
    today = date.today().strftime("%Y%m%d")
    r = httpx.get(
        FX_URL,
        params={"crkyCn": s.unipass_fxrt_api_key, "qryYymmDd": today, "imexTp": IMPORT},
        timeout=TIMEOUT,
    )
    _http_ok(r)
    rates = parse_rates(r.content)
    if not rates:
        return False, "응답은 왔지만 결과가 비었습니다 (키 또는 등록 확인)", {}
    return True, f"연결됨 · 관세환율 {len(rates)}개 통화", {}


def _check_mfds() -> tuple[bool, str, dict]:
    r = httpx.get(
        MFDS_BASE + MAKER_PATH,
        params={
            "serviceKey": get_settings().mfds_overseas_maker_api_key,
            "pageNo": 1,
            "numOfRows": 1,
            "type": "json",
        },
        timeout=TIMEOUT,
    )
    _http_ok(r)
    try:
        d = r.json()
    except ValueError:
        return False, "응답 형식 오류 (키 등록·승인 확인)", {}
    header = d.get("header") or d.get("response", {}).get("header", {})
    code = header.get("resultCode")
    if code not in ("00", "0", None):
        return False, f"식약처 결과코드 {code}", {}
    return True, "연결됨", {}


def _check_foodsafety() -> tuple[bool, str, dict]:
    url = f"http://openapi.foodsafetykorea.go.kr/api/{get_settings().foodsafety_api_key}/I0940/json/1/1"
    r = httpx.get(url, timeout=TIMEOUT)
    _http_ok(r)
    try:
        d = r.json()
    except ValueError:
        return False, "응답 형식 오류 (키 확인)", {}
    body = d.get("I0940") or {}
    code = (body.get("RESULT") or d.get("RESULT") or {}).get("CODE", "")
    if code and code != "INFO-000":
        return False, f"식품안전나라 결과코드 {code}", {}
    return True, "연결됨", {}


def _check_law() -> tuple[bool, str, dict]:
    r = httpx.get(
        "https://www.law.go.kr/DRF/lawSearch.do",
        params={
            "OC": get_settings().law_api_oc,
            "target": "law",
            "type": "JSON",
            "query": "식품위생법",
            "display": 1,
        },
        timeout=TIMEOUT,
    )
    _http_ok(r)
    try:
        d = r.json()
    except ValueError:
        return False, "응답 형식 오류 — 이 PC의 공인 IP가 법제처에 등록됐는지 확인", {}
    if "LawSearch" not in d:
        return False, "인증 실패 — OC 값 또는 등록 IP 확인", {}
    return True, "연결됨", {}


def _check_supabase() -> tuple[bool, str, dict]:
    s = get_settings()
    r = httpx.get(
        s.supabase_url.strip().rstrip("/") + "/auth/v1/health",
        headers={"apikey": s.supabase_anon_key},
        timeout=TIMEOUT,
    )
    if r.status_code in (401, 403):
        return False, "키가 맞지 않습니다 (SUPABASE_ANON_KEY 확인)", {}
    _http_ok(r)
    return True, "연결됨", {}


def _check_drive() -> tuple[bool, str, dict]:
    h = google_auth.headers()
    if not h:
        return False, "구글 로그인 만료 — token.json을 다시 만드세요", {}
    r = httpx.get(
        f"{drive.API}/{get_settings().drive_inbox_folder_id}",
        params={"fields": "id", "supportsAllDrives": "true"},
        headers=h,
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return False, "접수 폴더를 찾을 수 없습니다 (폴더 ID·공유 권한 확인)", {}
    _http_ok(r)
    return True, "연결됨 · 접수 폴더 확인", {}


def _check_gmail() -> tuple[bool, str, dict]:
    if not google_auth.headers():
        return False, "구글 로그인 만료 — token.json을 다시 만드세요", {}
    return True, "구글 로그인 정상 (발송 가능)", {}


LIVE: dict[str, Callable[[], tuple[bool, str, dict]]] = {
    "openai": lambda: _check_ai("openai"),
    "claude": lambda: _check_ai("claude"),
    "unipass": _check_unipass,
    "mfds": _check_mfds,
    "foodsafety": _check_foodsafety,
    "law": _check_law,
    "supabase": _check_supabase,
    "drive": _check_drive,
    "gmail": _check_gmail,
}


def check(key: str) -> dict:
    """한 연결을 실제로 검사하고 결과를 저장한다."""
    started = time.monotonic()
    ok, why = configured(key)
    extra: dict = {}
    if not ok:
        state, message = "off", why
    else:
        try:
            ok, message, extra = LIVE[key]()
        except httpx.HTTPStatusError as e:
            ok, message = False, f"서버 응답 오류 (HTTP {e.response.status_code})"
        except httpx.HTTPError as e:
            ok, message = False, f"인터넷 연결 실패 ({type(e).__name__})"
        state = "ok" if ok else "fail"
    result = {
        "state": state,
        "message": message,
        "checked_at": datetime.now(KST).isoformat(timespec="seconds"),
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        **extra,
    }
    _save_result(key, result)
    return result


# ── 3. 화면에 줄 표 ──────────────────────────────────────────────


# 글 대화용이 아닌 모델(음성·이미지·임베딩 등)은 버전 목록에서 뺀다
_NOT_CHAT = (
    "audio",
    "realtime",
    "tts",
    "transcribe",
    "image",
    "embedding",
    "search",
    "moderation",
    "instruct",
    "dall-e",
    "whisper",
    "codex",
)


def _chat_model(key: str, mid: str) -> bool:
    if any(w in mid for w in _NOT_CHAT):
        return False
    if key == "openai":
        return mid.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-"))
    return mid.startswith("claude-")


def _ai_block(key: str, last: dict) -> dict:
    """버전(모델) 고르기 목록. group: recommended(추천, 비용·속도 등급) / account(이 계정에서 쓸 수 있는 전체 버전).

    account 목록은 마지막 [연결 검사]에서 받은 모델 목록(data/connection_checks.json)이라 재시작해도 남는다.
    """
    fetched = [m for m in (last.get("available_models") or []) if _chat_model(key, m)]
    available = set(fetched)
    current = llm.current_model(key)
    options = [
        {
            "id": mid,
            "tier": tier,
            "group": "recommended",
            "available": (mid in available) if available else None,
        }
        for mid, tier in llm.MODEL_OPTIONS[key]
    ]
    options += [  # 최신 버전이 먼저 (검사 때 받은 순서 그대로)
        {"id": mid, "tier": "", "group": "account", "available": True} for mid in fetched
    ]
    listed = {o["id"] for o in options}
    if current not in listed:
        options.append({"id": current, "tier": "직접 입력", "group": "custom", "available": None})
    return {
        "in_use": llm.current_provider() == key,
        "model": current,
        "models": options,
        "account_list": bool(fetched),
    }


def status() -> dict:
    last_all = _load_results()
    rows = []
    for key, label, uses in SERVICES:
        ok, why = configured(key)
        last = last_all.get(key) or {}
        row: dict = {
            "key": key,
            "label": label,
            "uses": uses,
            "configured": ok,
            "config_reason": why,
            "last": {
                k: last[k] for k in ("state", "message", "checked_at", "elapsed_ms") if k in last
            }
            or None,
        }
        if key in ("openai", "claude"):
            row["ai"] = _ai_block(key, last)
        rows.append(row)
    return {
        "provider": llm.current_provider(),
        "llm_enabled": get_settings().llm_enabled,
        "rows": rows,
    }
