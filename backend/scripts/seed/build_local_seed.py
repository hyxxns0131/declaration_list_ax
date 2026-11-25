"""SCAM_DATA 전체를 PM PC의 로컬 SQLite에 적재한다. (PM 전용, 2026-11-25 v2)

사용: python backend/scripts/seed/build_local_seed.py <SCAM_DATA 경로> [data/app.db]

- SAMC_DATA(옛 이름 SCAM_DATA) 안의 **모든 파일**을 넣는다: 서류 접수(선적서류·성적서·수입신고서·사진), 검역 데이터 JSON,
  검역 이력·품목사항 엑셀, 법령자료(00~12 전부), 회사 기존 프로그램(SAMC_CUSTOMS_share, 참고용).
- 외부로 보내지 않는다. data/ 는 .gitignore 대상이다. Supabase에는 push_supabase.py로 따로 올린다(PM만, 원본은 비공개 Storage).
- 테이블
  raw_files      파일 1개 = 1행. 원본 바이트(content)와 sha256, 분류, 화주(가명)
  raw_text       파일에서 읽은 글자. PDF는 쪽마다, 엑셀은 시트마다, docx는 문서 전체, 텍스트·코드는 그대로
  raw_json       JSON 파일 원문
  raw_sheet_rows 모든 엑셀(xlsx·xls)의 행을 {열 이름: 값} JSON으로
- 기능별 테이블(documents, history_rows, records ...)은 AGENTS.md 5장 확정 후 이 원본에서 옮긴다.
- 의존성: openpyxl, xlrd, python-docx, pdfplumber(또는 poppler pdftotext)
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCHEMA = """
drop table if exists raw_files;
drop table if exists raw_text;
drop table if exists raw_json;
drop table if exists raw_sheet_rows;
create table raw_files (
  path text primary key,      -- SCAM_DATA 기준 상대 경로
  top text not null,          -- 맨 위 폴더(또는 파일) 이름
  category text not null,     -- intake | shipping_docs | inspection_data | sheet | law | company_program
  doc_kind text,              -- invoice | packing | bl | co | test_report | import_decl | photo | label | intake_list | ...
  shipper text,               -- A기업 / B기업 (가명) 또는 null
  ext text,
  size integer,
  sha256 text,
  public_candidate integer default 0,  -- 1 = Supabase 공개 정보 후보(법령자료 00·01·02·03·04·07·09)
  content blob,               -- 원본 바이트
  loaded_at text not null
);
create table raw_text (
  path text not null,
  part text not null,         -- 'p1'(PDF 쪽), 시트 이름, 'all'
  text text not null,
  primary key (path, part)
);
create table raw_json (
  path text primary key,
  category text not null,
  shipper text,
  body text not null,
  loaded_at text not null
);
create table raw_sheet_rows (
  workbook text not null,     -- SCAM_DATA 기준 상대 경로
  sheet text not null,
  row_no integer not null,    -- 1 = 머리글 다음 첫 행이 아니라 엑셀 실제 행 번호
  cells text not null,        -- {열 이름: 값} JSON
  loaded_at text not null,
  primary key (workbook, sheet, row_no)
);
"""

SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}
PUBLIC_LAW = {"00", "01", "02", "03", "04", "07", "09"}
TEXT_EXT = {".md", ".py", ".txt", ".ps1", ".cmd", ".example", ".gitignore", ".gcloudignore",
            ".dockerignore", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".csv", ""}


def shipper_of(rel: str) -> str | None:
    for name in ("A기업", "B기업"):
        if name in rel:
            return name
    return None


def category_of(rel: str) -> str:
    if rel.startswith("SAMC_CUSTOMS_share"):
        return "company_program"
    if rel.startswith("법령자료"):
        return "law"
    if rel.startswith("검역 데이터"):
        return "inspection_data"
    if rel.startswith("서류 접수"):
        return "intake"
    if rel.startswith("선적서류"):
        return "shipping_docs"     # 2026-11-25 추가: 화주별 B/L 폴더(1, 2, 3…) 선적서류 묶음
    return "sheet"


def doc_kind_of(rel: str, ext: str) -> str | None:
    s = rel.lower()
    rules = [
        ("수입신고서", "import_decl"), ("시험성적서", "test_report"), ("검사성적서", "test_report"),
        ("성적서", "test_report"), ("입고", "intake_list"), ("invoice", "invoice"), ("ci", None),
        ("packing", "packing"), ("b_l", "bl"), ("b/l", "bl"), ("bl", "bl"), ("원산지", "co"),
        ("c_o", "co"), ("한글표시", "label"), ("라벨", "label"), ("품목사항", "item_sheet"),
        ("검역 이력", "history_sheet"),
    ]
    for key, kind in rules:
        if kind and key in s:
            return kind
    if ext in (".jpg", ".jpeg", ".png"):
        return "photo"
    return None


def pdf_pages(p: Path) -> list[str]:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, timeout=120)
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace").split("\f")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    import pdfplumber
    with pdfplumber.open(p) as pdf:
        return [(pg.extract_text() or "") for pg in pdf.pages]


def sheet_rows(p: Path):
    """(sheet, row_no, [값...]) 를 낸다."""
    if p.suffix.lower() == ".xls":
        import xlrd
        wb = xlrd.open_workbook(p)
        for sh in wb.sheets():
            for r in range(sh.nrows):
                yield sh.name, r + 1, [sh.cell_value(r, c) for c in range(sh.ncols)]
    else:
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        for ws in wb.worksheets:
            for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
                yield ws.title, i, list(row)


def load_sheet(con, rel: str, p: Path, now: str) -> int:
    n = 0
    header: dict[str, list[str]] = {}
    texts: dict[str, list[str]] = {}
    for sheet, row_no, row in sheet_rows(p):
        vals = ["" if c is None else str(c) for c in row]
        if not any(v.strip() for v in vals):
            continue
        texts.setdefault(sheet, []).append("\t".join(vals))
        if sheet not in header:
            header[sheet] = [v or f"col{j}" for j, v in enumerate(vals, 1)]
            continue
        h = header[sheet]
        cells = {(h[j] if j < len(h) else f"col{j+1}"): (v or None) for j, v in enumerate(vals)}
        con.execute("insert or replace into raw_sheet_rows values (?,?,?,?,?)",
                    (rel, sheet, row_no, json.dumps(cells, ensure_ascii=False), now))
        n += 1
    for sheet, lines in texts.items():
        con.execute("insert or replace into raw_text values (?,?,?)", (rel, sheet, "\n".join(lines)))
    return n


def main(scam: Path, db_path: Path) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    count = {"files": 0, "bytes": 0, "json": 0, "sheet_rows": 0, "text_parts": 0, "text_fail": 0}

    for p in sorted(scam.rglob("*")):
        if not p.is_file() or SKIP_DIRS & set(p.parts):
            continue
        rel = p.relative_to(scam).as_posix()
        ext = p.suffix.lower()
        data = p.read_bytes()
        cat = category_of(rel)
        law_no = p.name[:2] if cat == "law" else ""
        con.execute(
            "insert into raw_files values (?,?,?,?,?,?,?,?,?,?,?)",
            (rel, rel.split("/")[0], cat, doc_kind_of(rel, ext), shipper_of(rel), ext, len(data),
             hashlib.sha256(data).hexdigest(), int(law_no in PUBLIC_LAW), data, now))
        count["files"] += 1
        count["bytes"] += len(data)

        try:
            if ext == ".json":
                body = data.decode("utf-8")
                json.loads(body)
                con.execute("insert into raw_json values (?,?,?,?,?)",
                            (rel, cat, shipper_of(rel), body, now))
                con.execute("insert or replace into raw_text values (?,?,?)", (rel, "all", body))
                count["json"] += 1
            elif ext in (".xlsx", ".xlsm", ".xls"):
                count["sheet_rows"] += load_sheet(con, rel, p, now)
            elif ext == ".pdf":
                for i, t in enumerate(pdf_pages(p), start=1):
                    if t.strip():
                        con.execute("insert or replace into raw_text values (?,?,?)", (rel, f"p{i}", t))
            elif ext == ".docx":
                import docx
                d = docx.Document(str(p))
                parts = [para.text for para in d.paragraphs]
                for tb in d.tables:
                    for r in tb.rows:
                        parts.append("\t".join(c.text for c in r.cells))
                con.execute("insert or replace into raw_text values (?,?,?)", (rel, "all", "\n".join(parts)))
            elif ext in TEXT_EXT or p.name in ("Dockerfile",):
                con.execute("insert or replace into raw_text values (?,?,?)",
                            (rel, "all", data.decode("utf-8", "replace")))
            # 사진(jpg·png)은 글자를 읽지 않는다(원본 바이트만). 판독은 프로그램 기능(A0)에서 한다.
        except Exception as e:  # 한 파일 실패가 전체 적재를 멈추지 않게
            count["text_fail"] += 1
            print(f"[글자 읽기 실패] {rel}: {type(e).__name__}", file=sys.stderr)

    count["text_parts"] = con.execute("select count(*) from raw_text").fetchone()[0]
    con.commit()
    con.close()
    print(json.dumps(count, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else "data/app.db"))
