"""SCAM_DATA의 공개 정보만 골라 Supabase 적재용 SQL을 만든다. (PM 전용, 2026-11-24)

사용: python backend/scripts/seed/build_public_seed.py <SCAM_DATA 경로> <출력 .sql 경로>
- 넣는 것: 재질 코드명·재질 코드, 재질 약어 변환, 법령자료 00·01·02·03·04·07·09 본문
- 빼는 것: 06(해외제조업소 신고 현황), 08(우리 회사 기준), 10(주간 보고), 11(검역 이력 복사본), 12(실적 기반 추가 검사),
           검역 데이터 JSON(실적·성적서·신고 공장 등), 서류 접수 폴더 전부 → 로컬 SQLite (build_local_seed.py)
- 화주 표기(A기업·B기업·COMPANY A/B·우리 신고)가 있는 줄은 지운다.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

PUBLIC_DOCS = {"00", "01", "02", "03", "04", "07", "09"}
SHIPPER_PATTERN = re.compile(r"A기업|B기업|C기업|COMPANY [A-Z]|우리 (신고|실적|회사)|신고탭|실적 탭")
CODE_PATTERN = re.compile(r"([가-힣A-Za-z0-9()\-·, ]+?)\s*\[(D\d{4}[0-9A-Z]{9})\]")


def docx_text(path: Path) -> str:
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(a, b)
    return text


def clean(text: str) -> tuple[str, int]:
    kept, dropped = [], 0
    for line in text.splitlines():
        if SHIPPER_PATTERN.search(line):
            dropped += 1
            continue
        kept.append(line)
    return "\n".join(kept), dropped


def q(value: object) -> str:
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def main(scam: Path, out: Path) -> None:
    today = date.today().isoformat()
    data_dir = next(scam.glob("검역 데이터*/검역 데이터*"))
    law_dir = next(scam.glob("법령자료*/법령자료*"))
    lines = ["-- 자동 생성: build_public_seed.py · 공개 정보만 · " + today, "begin;"]

    codes: dict[str, str | None] = {}
    cache = json.loads((data_dir / "material_codes_cache.json").read_text(encoding="utf-8"))
    as_of = cache.get("date", today)
    for name in cache.get("names", []):
        codes[name] = None
    doc03 = next(law_dir.glob("03 *.docx"))
    for m in CODE_PATTERN.finditer(docx_text(doc03)):
        name = m.group(1).strip(" ,·")
        if name in codes or len(name) <= 40:
            codes[name] = m.group(2)
    for name, code in sorted(codes.items()):
        lines.append(
            "insert into public.material_codes(name, code, source, as_of) values "
            f"({q(name)}, {q(code)}, '식약처 성분코드 API·법령자료 03', {q(as_of)}) "
            "on conflict (name) do update set code = coalesce(excluded.code, public.material_codes.code), as_of = excluded.as_of;"
        )
    for alias, name in sorted(cache.get("alias", {}).items()):
        lines.append(
            "insert into public.material_aliases(alias, name, source, as_of) values "
            f"({q(alias)}, {q(name)}, '기존 도구 재질 약어표', {q(as_of)}) "
            "on conflict (alias) do update set name = excluded.name, as_of = excluded.as_of;"
        )

    report = []
    for path in sorted(law_dir.glob("*.docx")):
        no = path.name[:2]
        if no not in PUBLIC_DOCS:
            report.append(f"제외 {path.name}")
            continue
        body, dropped = clean(docx_text(path))
        title = path.stem[3:]
        lines.append(
            "insert into public.law_documents(doc_no, title, body, source, as_of) values "
            f"({q(no)}, {q(title)}, {q(body)}, '법제처·식품안전나라·수입식품정보마루 (SAMC 법령자료 공유본)', {q(today)}) "
            "on conflict (doc_no) do update set title = excluded.title, body = excluded.body, as_of = excluded.as_of;"
        )
        report.append(f"적재 {path.name} (화주 표기 줄 {dropped}개 제거)")

    lines.append("commit;")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"재질 코드 {len(codes)}개, 약어 {len(cache.get('alias', {}))}개")
    print("\n".join(report))
    print(f"→ {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
