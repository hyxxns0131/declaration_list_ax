"""Supabase 읽기 전용 접근. 쓰기 함수는 만들지 않는다(쓰기는 PM 스크립트, RULES 7-2). 담당: KHS

- 공개 표(material_codes, material_aliases, law_documents, fx_rates): publishable 키로 읽음
- 고객사 자료(samc_*): 로그인 토큰(user_token)이 있어야 읽힘. 없으면 RLS 때문에 0건
"""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

PUBLIC_TABLES = {"material_codes", "material_aliases", "law_documents", "fx_rates"}
PRIVATE_TABLES = {"samc_files", "samc_texts", "samc_json", "samc_sheet_rows"}


def _headers(user_token: str | None) -> dict[str, str]:
    key = get_settings().supabase_anon_key
    return {"apikey": key, "Authorization": f"Bearer {user_token or key}"}


def select(
    table: str,
    params: dict[str, str] | None = None,
    user_token: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """PostgREST 조회. params 예: {"shipper": "eq.A기업", "select": "path,doc_kind"}"""
    s = get_settings()
    if table not in PUBLIC_TABLES | PRIVATE_TABLES:
        raise AppError("unknown_table", f"모르는 표: {table}", 400)
    if not s.supabase_url or not s.supabase_anon_key:
        raise AppError("supabase_not_set", ".env에 SUPABASE_URL·SUPABASE_ANON_KEY가 없습니다.", 503)
    q = {"limit": str(limit), **(params or {})}
    r = httpx.get(
        f"{s.supabase_url}/rest/v1/{table}", params=q, headers=_headers(user_token), timeout=30
    )
    if r.status_code >= 300:
        raise AppError("supabase_error", f"Supabase 조회 실패({r.status_code})", 502)
    return r.json()


SEED_PATTERNS = {
    "material_codes": (
        r"insert into public\.material_codes\(name, code, source, as_of\) values "
        r"\('((?:[^']|'')*)', '((?:[^']|'')*)'",
        ("name", "code"),
    ),
    "material_aliases": (
        r"insert into public\.material_aliases\(alias, name, source, as_of\) values "
        r"\('((?:[^']|'')*)', '((?:[^']|'')*)'",
        ("alias", "name"),
    ),
}


def _seed_rows(table: str) -> list[dict[str, Any]]:
    """PM PC의 data/public_seed.sql(build_public_seed.py 결과)에서 공개 표 읽기. 없으면 빈 목록."""
    import re

    pat = SEED_PATTERNS.get(table)
    path = get_settings().data_path / "public_seed.sql"
    if not pat or not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    keys = pat[1]
    return [
        {k: v.replace("''", "'") for k, v in zip(keys, m, strict=True)}
        for m in re.findall(pat[0], text)
    ]


def select_public(
    table: str, params: dict[str, str] | None = None, limit: int = 5000
) -> list[dict]:
    """공개 표 읽기: Supabase → (비었거나 못 읽으면) 로컬 public_seed.sql. 2026-11-25 Supabase 공개 표가
    비어 있는 것을 확인 → PM이 push_supabase.py를 돌리기 전까지 로컬 seed로 동작한다."""
    try:
        rows = select(table, params, limit=limit)
    except (AppError, httpx.HTTPError):
        rows = []
    return rows or _seed_rows(table)


def download_original(storage_path: str, user_token: str) -> bytes:
    """비공개 Storage(samc-originals)에서 원본 파일 받기. 로그인 토큰 필요."""
    s = get_settings()
    r = httpx.get(
        f"{s.supabase_url}/storage/v1/object/authenticated/samc-originals/{storage_path}",
        headers=_headers(user_token),
        timeout=60,
    )
    if r.status_code >= 300:
        raise AppError("supabase_error", f"원본 받기 실패({r.status_code})", 502)
    return r.content
