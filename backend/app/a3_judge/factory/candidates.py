"""회사명 → 등록 공장 목록(식약처 API, core/mfds.py). 담당: LSY [재사용] A3-3

식약처에서 못 찾았고 samples/mfds/factories.json(가상 공장)에 같은 회사명이 있으면 그것을 쓴다(시연용).
조회 실패(키 없음·통신 오류)는 None → 호출한 쪽이 "해외제조업소 조회 실패 → 수기 확인".
"""

import json

from app.core.config import REPO_ROOT
from app.core.mfds import MfdsError, factories, norm_name

MOCK_FILE = REPO_ROOT / "samples" / "mfds" / "factories.json"


def _mock(company: str) -> list[dict]:
    if not MOCK_FILE.exists():
        return []
    data = json.loads(MOCK_FILE.read_text(encoding="utf-8"))
    return [f for f in data if norm_name(f.get("name", "")) == norm_name(company)]


def lookup(company: str) -> tuple[list[dict] | None, str]:
    """(공장 목록 또는 None, 출처 'mfds'·'mock'·'error')"""
    if not company:
        return [], "mfds"
    try:
        got = factories(company)
    except MfdsError:
        got = None
    if got:
        return got, "mfds"
    mock = _mock(company)
    if mock:
        return mock, "mock"
    return (got, "mfds") if got is not None else (None, "error")
