"""유일한 LLM 진입점 call_structured(). AI_PROVIDER로 Claude·GPT 전환, 보내기 전 masking. 담당: KHS

규칙 (AGENTS 7장)
- 다른 파일에서 anthropic·openai SDK를 import하지 않는다.
- 프롬프트 원문: backend/prompts/<영역>/<이름>.v<N>.md
- 응답은 JSON → Pydantic 검증. 실패하면 1회만 다시 시도, 또 실패하면 None("확인 필요").
- LLM_ENABLED=false면 부르지 않고 None.
- 호출 기록(기능·프롬프트 버전·토큰)은 logs/ai_usage.jsonl. 서류 원문은 남기지 않는다.
- 사용할 AI 회사·모델은 화면(탭 5. 연결 설정)에서 고를 수 있다. 고른 값은 data/ai_choice.json에만 둔다.
  우선순위: 화면에서 고른 값 > .env(AI_PROVIDER, OPENAI_MODEL, CLAUDE_MODEL) > 아래 기본값.
"""

import json
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import REPO_ROOT, get_settings
from app.core.masking import mask_inputs

T = TypeVar("T", bound=BaseModel)

PROMPT_DIR = REPO_ROOT / "backend" / "prompts"
USAGE_LOG = REPO_ROOT / "logs" / "ai_usage.jsonl"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-5-5"
DEFAULT_OPENAI_MODEL = "gpt-5"
PROVIDERS = ("openai", "claude")
# 화면에서 고르는 모델 (id, 등급). 등급은 비용·성능 안내용. 실제 쓸 수 있는지는 [연결 검사]로 확인한다
MODEL_OPTIONS: dict[str, list[tuple[str, str]]] = {
    # 계정에서 쓸 수 있는 다른 GPT 버전은 [연결 검사] 뒤 목록에 자동으로 더해진다(connections._ai_block)
    "openai": [
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
    "claude": [
        ("claude-haiku-5-5", "저렴·빠름"),
        ("claude-sonnet-5-5", "보통"),
        ("claude-opus-5-5", "고성능·비쌈"),
    ],
}
_DEFAULT_MODEL = {"openai": DEFAULT_OPENAI_MODEL, "claude": DEFAULT_CLAUDE_MODEL}


def _choice_path() -> Path:
    return get_settings().data_path / "ai_choice.json"


def load_choice() -> dict:
    """화면에서 고른 값 {"provider": ..., "models": {provider: model}}. 없으면 빈 값."""
    p = _choice_path()
    if not p.exists():
        return {"provider": "", "models": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"provider": "", "models": {}}
    return {"provider": data.get("provider") or "", "models": data.get("models") or {}}


def save_choice(provider: str | None = None, model: str | None = None) -> dict:
    """사용할 AI 회사 또는 그 회사의 모델을 저장한다. model은 provider와 함께 준다."""
    data = load_choice()
    if provider:
        if provider not in PROVIDERS:
            raise ValueError("provider")
        if model is not None:
            data["models"][provider] = model.strip()
        else:
            data["provider"] = provider
    _choice_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def current_provider() -> str:
    p = load_choice()["provider"] or get_settings().ai_provider
    return p if p in PROVIDERS else "claude"


def current_model(provider: str | None = None) -> str:
    provider = provider or current_provider()
    s = get_settings()
    env = s.openai_model if provider == "openai" else s.claude_model
    return load_choice()["models"].get(provider) or env or _DEFAULT_MODEL[provider]


def api_key(provider: str) -> str:
    s = get_settings()
    return s.openai_api_key if provider == "openai" else s.anthropic_api_key


def load_prompt(prompt_name: str, version: int) -> str:
    path = PROMPT_DIR / f"{prompt_name}.v{version}.md"
    return path.read_text(encoding="utf-8")


def _extract_json(text: str) -> object:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=0)
    return json.loads(text[start:])


def _ask(system: str, user: str) -> tuple[str, dict]:
    provider = current_provider()
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=api_key("openai"))
        r = client.chat.completions.create(
            model=current_model("openai"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        usage = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else {}
        return r.choices[0].message.content or "", usage
    import anthropic

    client = anthropic.Anthropic(api_key=api_key("claude"))
    r = client.messages.create(
        model=current_model("claude"),
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return text, {"in": r.usage.input_tokens, "out": r.usage.output_tokens}


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
    with USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ready() -> bool:
    """AI를 실제로 부를 수 있는지: LLM_ENABLED이고 고른 회사의 키가 있다."""
    return get_settings().llm_enabled and bool(api_key(current_provider()))


def call_structured(
    prompt_name: str,
    version: int,
    inputs: dict,
    schema: type[T],
    mask_names: list[str] | None = None,
) -> T | None:
    """프롬프트 + 입력 → schema로 검증된 결과. 못 얻으면 None(호출한 쪽이 '확인 필요'로 둔다)."""
    s = get_settings()
    if not ready():  # 꺼짐 또는 키 없음 → 규칙만으로 (AGENTS 7-7)
        return None
    if s.mask_shipper_names:
        inputs = mask_inputs(inputs, mask_names or [])  # type: ignore[assignment]
    system = (
        load_prompt(prompt_name, version)
        + "\n\n반드시 아래 JSON 스키마에 맞는 JSON만 답한다.\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )
    user = json.dumps(inputs, ensure_ascii=False)
    for _ in range(2):  # 처음 + 1회 재시도
        try:
            text, usage = _ask(system, user)
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
