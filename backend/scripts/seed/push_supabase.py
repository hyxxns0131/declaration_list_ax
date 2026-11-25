"""로컬 DB(data/app.db)의 SAMC_DATA를 Supabase로 올린다. (PM 전용, 2026-11-25)

사용 (저장소 맨 위 폴더에서):
    python backend/scripts/seed/push_supabase.py

필요한 것 (.env):
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY(대시보드 Project Settings → API Keys → secret 키, PM만),
    ADMIN_USERNAME, ADMIN_PASSWORD (프로그램 계정 1개 = Supabase 로그인 계정)

하는 일:
    1. 프로그램 계정(ADMIN_USERNAME@declaration.local)을 Supabase 로그인 사용자로 만든다(이미 있으면 넘어감).
    2. 원본 파일 → 비공개 Storage 버킷 samc-originals (파일 이름은 sha256 + 확장자).
    3. samc_files / samc_texts / samc_json / samc_sheet_rows 표에 올린다(같은 키면 덮어씀).
       이 표들은 로그인한 사용자만 읽을 수 있다(RLS). 공개 키만으로는 보이지 않는다.
    4. 공개 법령자료(00·01·02·03·04·07·09) → law_documents (누구나 읽기).
표준 라이브러리만 쓴다. service_role 키는 화면·로그에 출력하지 않는다.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BATCH = 500


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip()
        env[k.strip()] = v
    return env


class Supa:
    def __init__(self, url: str, key: str) -> None:
        self.url = url.rstrip("/")
        self.key = key

    def req(self, method: str, path: str, body: bytes | None = None, headers: dict | None = None) -> tuple[int, bytes]:
        h = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
        h.update(headers or {})
        r = urllib.request.Request(self.url + path, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=300) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            code, out = self.req(
                "POST", f"/rest/v1/{table}?on_conflict={on_conflict}",
                json.dumps(chunk, ensure_ascii=False).replace("\\u0000", "").encode("utf-8"),  # Postgres는 NUL 글자를 못 받음
                {"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            if code >= 300:
                raise SystemExit(f"{table} 올리기 실패({code}): {out[:300].decode('utf-8', 'replace')}")
        print(f"  {table}: {len(rows)}행")


def ensure_user(s: Supa, env: dict[str, str]) -> None:
    user, pw = env.get("ADMIN_USERNAME"), env.get("ADMIN_PASSWORD")
    if not user or not pw:
        print("  계정: ADMIN_USERNAME/ADMIN_PASSWORD가 없어 넘어감")
        return
    email = f"{user}@declaration.local"
    body = json.dumps({"email": email, "password": pw, "email_confirm": True}).encode()
    code, out = s.req("POST", "/auth/v1/admin/users", body, {"Content-Type": "application/json"})
    if code < 300:
        print(f"  계정 만듦: {user}")
    elif b"already" in out or code == 422:
        print(f"  계정 있음: {user}")
    else:
        raise SystemExit(f"계정 만들기 실패({code}): {out[:300].decode('utf-8', 'replace')}")


def main() -> None:
    env = load_env(ROOT / ".env")
    url, key = env.get("SUPABASE_URL"), env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit(".env에 SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 넣어 주세요.")
    db = sqlite3.connect(ROOT / env.get("LOCAL_DB_PATH", "data/app.db"))
    s = Supa(url, key)

    print("1) 프로그램 계정")
    ensure_user(s, env)

    print("2) 원본 파일 → Storage(samc-originals, 비공개)")
    files = []
    rows = db.execute("select path, top, category, doc_kind, shipper, ext, size, sha256 from raw_files").fetchall()
    for n, (path, top, cat, kind, shipper, ext, size, sha) in enumerate(rows, 1):
        obj = f"{sha}{(ext or '').lower()}"
        content = db.execute("select content from raw_files where path=?", (path,)).fetchone()[0]
        code, out = s.req("POST", f"/storage/v1/object/samc-originals/{urllib.parse.quote(obj)}", content,
                          {"Content-Type": "application/octet-stream", "x-upsert": "true"})
        if code >= 300:
            raise SystemExit(f"Storage 실패({code}) {path}: {out[:200].decode('utf-8', 'replace')}")
        files.append({"path": path, "top": top, "category": cat, "doc_kind": kind, "shipper": shipper,
                      "ext": ext, "size": size, "sha256": sha, "storage_path": obj})
        if n % 25 == 0 or n == len(rows):
            print(f"  {n}/{len(rows)}")

    print("3) 표 올리기")
    s.upsert("samc_files", files, "path")
    s.upsert("samc_texts", [{"path": p, "part": part, "text": t} for p, part, t in
                            db.execute("select path, part, text from raw_text")], "path,part")
    js = []
    for p, cat, shipper, body in db.execute("select path, category, shipper, body from raw_json"):
        try:
            val = json.loads(body)
        except (TypeError, ValueError):
            val = {"raw": body}
        js.append({"path": p, "category": cat, "shipper": shipper, "body": val})
    s.upsert("samc_json", js, "path")
    s.upsert("samc_sheet_rows", [{"workbook": w, "sheet": sh, "row_no": r, "cells": json.loads(c)} for w, sh, r, c in
                                 db.execute("select workbook, sheet, row_no, cells from raw_sheet_rows")],
             "workbook,sheet,row_no")

    print("4) 공개 법령자료 → law_documents")
    seed = ROOT / "data" / "public_seed.sql"
    if seed.exists():
        sq = r"'((?:[^']|'')*)'"
        pat = re.compile(r"insert into public\.law_documents\(doc_no, title, body, source, as_of\) values \("
                         + ", ".join([sq] * 5) + r"\)", re.S)
        law = [{"doc_no": m[0], "title": m[1].replace("''", "'"), "body": m[2].replace("''", "'"),
                "source": m[3].replace("''", "'"), "as_of": m[4]} for m in pat.findall(seed.read_text(encoding="utf-8"))]
        s.upsert("law_documents", law, "doc_no")
        print("5) 공개 재질 코드·약어 → material_codes, material_aliases")
        text = seed.read_text(encoding="utf-8")
        un = lambda v: None if v == "null" else v[1:-1].replace("''", "'")  # noqa: E731
        sv = r"('(?:[^']|'')*'|null)"
        mc = re.compile(r"insert into public\.material_codes\(name, code, source, as_of\) values \("
                        + ", ".join([sv] * 4) + r"\)")
        ma = re.compile(r"insert into public\.material_aliases\(alias, name, source, as_of\) values \("
                        + ", ".join([sv] * 4) + r"\)")
        s.upsert("material_codes", [{"name": un(a), "code": un(b), "source": un(c), "as_of": un(d)}
                                    for a, b, c, d in mc.findall(text)], "name")
        s.upsert("material_aliases", [{"alias": un(a), "name": un(b), "source": un(c), "as_of": un(d)}
                                      for a, b, c, d in ma.findall(text)], "alias")
    else:
        print("  data/public_seed.sql 없음: build_public_seed.py를 먼저 실행")
    print("끝")


if __name__ == "__main__":
    sys.exit(main())
