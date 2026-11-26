"""유일한 LLM 진입점 call_structured(). AI는 OpenAI만 쓴다(OpenAI만 사용: HS 결정 11/26). 보내기 전 masking. 담당: KHS

규칙 (AGENTS 7장)
- 다른 파일에서 openai SDK를 import하지 않는다.
- 프롬프트 원문: backend/prompts/<영역>/<이름>.v<N>.md
- 응답은 JSON → Pydantic 검증. 실패하면 1회만 다시 시도, 또 실패하면 None("확인 필요").
- LLM_ENABLED=false면 부르지 않고 None. 키는 .env의 OPENAI_API_KEY 하나.
- 호출 기록(기능·프롬프트 버전·토큰)은 logs/ai_usage.jsonl. 서류 원문은 남기지 않는다.
- 모델(버전)은 화면(탭 6. 연결 설정 › AI 모델)에서 고를 수 있다. 고른 값은 data/ai_choice.json에만 둔다.
  우선순위: 화면에서 고른 값 > .env(OPENAI_MODEL) > 아래 기본값. 예전에 저장된 claude 선택은 무시한다.
"""

import json
import threading
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import REPO_ROOT, get_settings
from app.core.masking import all_names, mask_inputs

T = TypeVar("T", bound=BaseModel)

PROMPT_DIR = REPO_ROOT / "backend" / "prompts"
USAGE_LOG = REPO_ROOT / "logs" / "ai_usage.jsonl"
PROVIDER = "openai"  # 유일한 AI 회사 (HS 결정 11/26)
PROVIDERS = (PROVIDER,)
DEFAULT_OPENAI_MODEL = "gpt-5"
# 화면에서 고르는 모델 (id, 등급). 등급은 비용·성능 안내용. 실제 쓸 수 있는지는 [연결 검사]로 확인한다.
# 계정에서 쓸 수 있는 다른 GPT 버전은 [연결 검사] 뒤 목록에 자동으로 더해진다(connections._ai_block)
MODEL_OPTIONS: dict[str, list[tuple[str, str]]] = {
    PROVIDER: [
        ("gpt-4o-mini", "저렴·빠름"),
        ("gpt-4.1-nano", "저렴·빠름"),
        ("gpt-4.1-mini", "저렴·빠름"),
        ("gpt-5-nano", "저렴·빠름"),
        ("gpt-5-mini", "보통"),
        ("gpt-4o", "보통"),
        ("gpt-4.1", "고성능"),
        ("o4-mini", "고성능(추론)"),
        ("gpt-5", "고성능·비쌈"),
    ],
}


def _choice_path() -> Path:
    return get_settings().data_path / "ai_choice.json"


def load_choice() -> dict:
    """화면에서 고른 모델 {"models": {"openai": model}}. 없으면 빈 값. 다른 회사 값은 버린다."""
    p = _choice_path()
    if not p.exists():
        return {"models": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"models": {}}
    models = data.get("models") or {}
    return {"models": {PROVIDER: models[PROVIDER]} if models.get(PROVIDER) else {}}


def save_choice(provider: str = PROVIDER, model: str | None = None) -> dict:
    """OpenAI 모델(버전)을 저장한다. 다른 회사는 받지 않는다."""
    if provider != PROVIDER:
        raise ValueError("provider")
    data = load_choice()
    if model is not None:
        data["models"][PROVIDER] = model.strip()
    _choice_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def current_provider() -> str:
    """늘 'openai' (예전 화면·기록과 맞추려고 남겨 둔 함수)."""
    return PROVIDER


def current_model(provider: str | None = None) -> str:
    return (
        load_choice()["models"].get(PROVIDER) or get_settings().openai_model or DEFAULT_OPENAI_MODEL
    )


def api_key(provider: str = PROVIDER) -> str:
    return get_settings().openai_api_key if provider == PROVIDER else ""


def load_prompt(prompt_name: str, version: int) -> str:
    path = PROMPT_DIR / f"{prompt_name}.v{version}.md"
    return path.read_text(encoding="utf-8")


def _extract_json(text: str) -> object:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=0)
    return json.loads(text[start:])


def _ask(system: str, user: str, images: list[bytes] | None = None) -> tuple[str, dict]:
    import base64

    from openai import OpenAI

    client = OpenAI(api_key=api_key())
    content: object = user
    if images:  # 스캔 PDF·사진 서류: 페이지 이미지를 함께 보낸다(멀티모달)
        content = [{"type": "text", "text": user}] + [
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64," + base64.b64encode(b).decode()},
            }
            for b in images
        ]
    r = client.chat.completions.create(
        model=current_model(),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],  # type: ignore[list-item]
        response_format={
            "type": "json_object"
        },  # 구조화 출력: JSON만 받는다(받은 뒤 Pydantic 검증)
    )
    usage = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else {}
    return r.choices[0].message.content or "", usage


_LOG_LOCK = threading.Lock()  # 여러 스레드가 동시에 써도 줄이 섞이지 않게


def _log(prompt_name: str, version: int, usage: dict, ok: bool) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "prompt": prompt_name,
        "v": version,
        "provider": current_provider(),
        "model": current_model(),
        "ok": ok,
        **usage,
    }
    with _LOG_LOCK, USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


NO_MASK_WARNING = "화주명 목록이 없어 AI로 보내지 않음 - 직접 입력"


def send_allowed() -> bool:
    """서류를 실제로 OpenAI로 보낼 수 있는지: AI가 켜져 있고 PC 전용 화주명 목록이 있다(없으면 DB에서 한 번 만들어 본다)."""
    if not ready():
        return False
    if not all_names():
        from app.core.mask_names import ensure

        ensure()
    return bool(all_names())


def ready() -> bool:
    """AI를 실제로 부를 수 있는지: LLM_ENABLED이고 OPENAI_API_KEY가 있다."""
    return get_settings().llm_enabled and bool(api_key())


def call_structured(
    prompt_name: str,
    version: int,
    inputs: dict,
    schema: type[T],
    mask_names: list[str] | None = None,
    images: list[bytes] | None = None,
) -> T | None:
    """프롬프트 + 입력 → schema로 검증된 결과. 못 얻으면 None(호출한 쪽이 '확인 필요'로 둔다)."""
    if not ready():  # 꺼짐 또는 키 없음 → 규칙만으로 (AGENTS 7-7)
        return None
    # 임시 안전 조치(11/26, HS 결정 전): PC 전용 실제 화주명 목록이 없으면 서류 글자·이미지를 보내지 않는다.
    # 목록이 있으면 모든 화주 이름 + 호출한 쪽이 넘긴 이름을 가린 뒤 보낸다(MASK_SHIPPER_NAMES와 상관없이).
    names = all_names()
    if not names:  # PC에 목록이 없으면 DB에서 한 번 만들어 본다(HS 결정 11/26)
        from app.core.mask_names import ensure

        ensure()
        names = all_names()
    if not names:
        _log(prompt_name, version, {"blocked": "no_mask_list"}, ok=False)
        return None
    inputs = mask_inputs(inputs, sorted(set(names) | set(mask_names or []), key=len, reverse=True))  # type: ignore[assignment]
    system = (
        load_prompt(prompt_name, version)
        + "\n\n반드시 아래 JSON 스키마에 맞는 JSON만 답한다.\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )
    user = json.dumps(inputs, ensure_ascii=False)
    for _ in range(2):  # 처음 + 1회 재시도
        try:
            text, usage = _ask(system, user, images)
        except Exception:  # 통신·인증 오류 — 판단은 '확인 필요'로 계속한다
            _log(prompt_name, version, {}, ok=False)
            return None
        try:
            result = schema.model_validate(_extract_json(text))
        except (ValueError, ValidationError):
            _log(prompt_name, version, usage, ok=False)
            continue
        _log(prompt_name, version, usage, ok=True)
        return result
    return None


def prompt_exists(prompt_name: str, version: int) -> bool:
    return Path(PROMPT_DIR / f"{prompt_name}.v{version}.md").exists()
