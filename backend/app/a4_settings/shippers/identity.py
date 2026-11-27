"""신규 화주 식별 값 검사 — 순수 함수. 담당: JUJ [신규] A4-1

- 통관고유부호·화주 별칭 정규화(앞뒤 공백 제거·대문자)와 형식 검사.
- 내부 shipper_id 자동 생성(S0003…). 통관고유부호로 ID를 만들지 않는다(파일명·로그 노출 방지).
- 형식 수치는 rules/customs_code.json 설정값(AGENTS 0-5). 실제 부호 형식은 관세청 공식 기준 확인 필요.
- 반환하는 사유 코드에는 입력값을 넣지 않는다(오류 문구·로그에 부호가 남지 않게).
"""

import re
from collections.abc import Iterable

# 사유 코드 (화면 문구는 frontend/lib/text/settings.ts)
REQUIRED = "required"
FORMAT = "format"
PROD_TEST_BLOCKED = "prod_test_blocked"  # 운영 환경에서 가상(TEST) 부호
PROD_NOT_READY = "prod_not_ready"  # 운영 환경인데 실제 부호 형식 미확정


def normalize_code(value: str | None) -> str:
    return (value or "").strip().upper()


def normalize_alias(value: str | None) -> str:
    return (value or "").strip().upper()


def is_dev(app_env: str, cfg: dict) -> bool:
    return app_env.strip().lower() in {e.lower() for e in cfg.get("dev_envs", [])}


def check_code_format(code: str, dev: bool, cfg: dict) -> str | None:
    """정규화된 부호의 형식 검사. 문제가 없으면 None."""
    if not code:
        return REQUIRED
    if dev:
        return None if re.fullmatch(cfg["dev_pattern"], code) else FORMAT
    if any(code.startswith(p) for p in cfg.get("blocked_prefixes_in_prod", [])):
        return PROD_TEST_BLOCKED
    pattern = cfg.get("prod_pattern")
    if not pattern:
        return PROD_NOT_READY
    return None if re.fullmatch(pattern, code) else FORMAT


def check_alias_format(alias: str, cfg: dict) -> str | None:
    if not alias:
        return REQUIRED
    return None if re.fullmatch(cfg["alias_pattern"], alias) else FORMAT


def display_name(alias: str) -> str:
    """화면 표시 이름. 예: C → C사 (기존 A사·B사 표기와 맞춤, PM 확인 필요 5)."""
    return f"{alias}사"


def parse_seq(shipper_id: str, prefix: str) -> int | None:
    m = re.fullmatch(rf"{re.escape(prefix)}(\d+)", shipper_id)
    return int(m.group(1)) if m else None


def next_shipper_id(seqs: Iterable[int], prefix: str = "S", digits: int = 4) -> str:
    """이미 쓴 순번(살아 있는 화주·삭제 백업·등록부) 중 가장 큰 값 + 1. 삭제된 ID는 다시 쓰지 않는다.
    A·B 다음 첫 화주는 S0003(가상 데이터 C사 = TEST000000003과 번호를 맞춤)."""
    n = max([2, *seqs]) + 1
    return f"{prefix}{n:0{digits}d}"
