"""유일한 LLM 진입점 call_structured(). AI_PROVIDER로 Claude·GPT 전환, 보내기 전 masking. 담당: KHS

규칙 (AGENTS 7장)
- 다른 파일에서 anthropic·openai SDK를 import하지 않는다.
- 프롬프트 원문: backend/prompts/<영역>/<이름>.v<N>.md
- 응답은 JSON → Pydantic 검증. 실패하면 1회만 다시 시도, 또 실패하면 None("확인 필요").
- LLM_ENABLED=false면 부르지 않고 None.
- 호출 기록(기능·프롬프트 버전·토큰)은 logs/ai_usage.jsonl. 서류 원문은 남기지 않는다.
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
    s = get_settings()
    if s.ai_provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=s.openai_api_key)
        r = client.chat.completions.create(
            model=s.openai_model or DEFAULT_OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        usage = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else {}
        return r.choices[0].message.content or "", usage
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    r = client.messages.create(
        model=s.claude_model or DEFAULT_CLAUDE_MODEL,
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
        "provider": get_settings().ai_provider,
        "ok": ok,
        **usage,
    }
    with USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ready() -> bool:
    """AI를 실제로 부를 수 있는지: LLM_ENABLED이고 고른 회사의 키가 있다."""
    s = get_settings()
    key = s.openai_api_key if s.ai_provider == "openai" else s.anthropic_api_key
    return s.llm_enabled and bool(key)


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
