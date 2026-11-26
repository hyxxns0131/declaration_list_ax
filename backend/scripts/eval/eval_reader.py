"""실제 샘플(Supabase, 읽기만)로 서류 판별·추출 정확도 재기. PC 안에서만 돌리고 결과는 data/eval/(git 제외)에 둔다.
담당: KHS (검역 리스트 탭 1단계). 화주 이름·파일 경로·서류 값은 화면에 찍지 않고 칸별 일치율만 찍는다.

대상
- 선적서류: samc_files category=shipping_docs 전부 + category=intake 중 doc_kind=bl.
  shipping_docs는 doc_kind가 비어 있는 것이 많으니 doc_kind를 믿지 않고 판별 결과를 함께 적는다.
- 정답: samc_sheet_rows 중 category=sheet, doc_kind=history_sheet 파일(workbook = 파일 path)의 행.

실행: cd backend && .venv/Scripts/python scripts/eval/eval_reader.py [--ai on|off]   (로그인 계정은 .env의 관리자 계정)
- --ai off: 규칙(openpyxl·xlrd·pdfplumber)만. --ai on(기본): 규칙으로 못 채운 칸을 OpenAI(멀티모달 + JSON)로 보충.
- AI로 보낼 때 화주명은 samc_files.shipper 값으로 가린다(글자는 core/masking, 글자 있는 PDF 이미지는 검은 칸).
  글자 없는 스캔본 이미지는 위치를 몰라 가리지 못한다(HS 11/26 승인 범위에서 평가용으로만).
- 결과: data/eval/eval_reader_<ai>.json(칸별 일치율·판별·토큰), 칸별 틀린 이유 태그는 같은 파일. 서류 값·이름은 찍지 않는다.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx  # noqa: E402

from app.a0_reader.extract import redact  # noqa: E402
from app.a0_reader.extract.service import extract_documents  # noqa: E402
from app.core.auth.service import _supabase_login  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.schema.document import ParsedDocument  # noqa: E402
from app.core.storage.public_db import download_original  # noqa: E402

GOLD_TABS = "A기업,B기업"

FIELDS = {  # 정답 칸 → 추출 값 꺼내기
    "B/L Number": "bl_no",
    "모선명": "vessel",
    "카톤 수": "cartons",
    "입수": "pcs",  # 입수 = 전체 개수(PCS 합계, HS 결정 11/26)
    "순중량": "net_kg",
    "가격(수출국)": "amount",
}


def _norm(v: object) -> str:
    s = str(v or "").strip().upper()
    try:
        return f"{float(s.replace(',', '')):g}"
    except ValueError:
        return re.sub(r"\s+", "", s)


def _select(table: str, params: dict, token: str) -> list[dict]:
    s = get_settings()
    h = {"apikey": s.supabase_anon_key, "Authorization": f"Bearer {token}"}
    out, offset = [], 0
    while True:
        q = {"select": "*", "limit": "1000", "offset": str(offset), **params}
        r = httpx.get(f"{s.supabase_url}/rest/v1/{table}", params=q, headers=h, timeout=60)
        r.raise_for_status()
        rows = r.json()
        out += rows
        if len(rows) < 1000:
            return out
        offset += 1000


def _usage_since(n_before: int) -> dict:
    from app.core.llm import USAGE_LOG

    rows, broken = [], 0
    if USAGE_LOG.exists():
        for x in USAGE_LOG.read_text(encoding="utf-8").splitlines()[n_before:]:
            try:
                rows.append(json.loads(x))
            except ValueError:
                broken += 1
    return {
        "calls": len(rows),
        "failed": sum(1 for r in rows if not r.get("ok")),
        "broken_log_lines": broken,
        "in": sum(r.get("in", 0) for r in rows),
        "out": sum(r.get("out", 0) for r in rows),
        "by_prompt": dict(Counter(r["prompt"] for r in rows)),
    }


def _log_len() -> int:
    from app.core.llm import USAGE_LOG

    return len(USAGE_LOG.read_text(encoding="utf-8").splitlines()) if USAGE_LOG.exists() else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", choices=["on", "off"], default="on")
    ap.add_argument("--reuse", action="store_true", help="지난 추출 결과(cache)를 다시 쓴다")
    args = ap.parse_args()
    ai_on, reuse = args.ai == "on", args.reuse
    import app.core.llm as llm

    if not ai_on:
        llm.ready = lambda: False  # type: ignore[assignment]
    elif not llm.ready():
        print("AI를 켤 수 없습니다(LLM_ENABLED·OPENAI_API_KEY 확인). --ai off로 돌리세요.")
        return
    log_before = _log_len()
    # 가리기 확인: 보내는 글자마다 [화주] 개수만 센다(글자는 남기지 않는다)
    sent_stats = {"calls": 0, "masked_calls": 0, "masks": 0, "images": 0}
    real_ask = llm._ask

    def _counting_ask(system: str, user: str, images: list[bytes] | None = None):  # noqa: ANN202
        n = user.count("[화주]")
        sent_stats["calls"] += 1
        sent_stats["masked_calls"] += n > 0
        sent_stats["masks"] += n
        sent_stats["images"] += len(images or [])
        return real_ask(system, user, images)

    llm._ask = _counting_ask  # type: ignore[assignment]
    redact.SAVE_DIR = get_settings().data_path / "eval" / "redacted"  # 가린 PNG 예시(PC 안)
    s = get_settings()
    token = _supabase_login(s.admin_username, s.admin_password)
    if not token:
        print("Supabase 로그인 실패 — .env 관리자 계정 확인")
        return
    files = _select("samc_files", {"category": "eq.shipping_docs"}, token)
    files += _select("samc_files", {"category": "eq.intake", "doc_kind": "eq.bl"}, token)
    work = s.data_path / "eval" / "files"
    cache_dir = s.data_path / "eval" / f"cache_{args.ai}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    # 가릴 이름: 제품과 같은 PC 전용 목록 DATA_DIR/mask_names.json(커밋 안 함) + 파일 목록의 화주 표기.
    # samc_files.shipper는 'A기업' 같은 가명 표기라 서류에 적힌 실제 회사명을 가리지 못한다(11/26 확인).
    # 그래서 AI 켬 평가는 실제 이름 목록이 있을 때만 돌린다(core/llm.py도 목록이 없으면 보내지 않는다).
    from app.core.masking import all_names, mask_file

    real = all_names()
    if ai_on and not real:
        print(
            f"AI 켬 평가 중단: {mask_file()} 에 실제 화주명 목록이 없습니다. 가리지 못하면 보내지 않습니다."
        )
        return
    mask = sorted(set(real) | ({str(f.get("shipper") or "").strip() for f in files} - {""}))

    by_bl: dict[str, dict] = defaultdict(lambda: {"head": {}, "lines": {}})
    kinds: Counter = Counter()
    jobs = []
    for i, f in enumerate(files):
        ext = "." + (f.get("ext") or "bin").lstrip(".")
        if ext == ".zip":
            continue
        local = work / f"{f['sha256'][:16]}{ext}"
        if not local.exists():
            local.write_bytes(download_original(f["storage_path"], token))
        jobs.append((i, f, local, ext))

    def _run(job: tuple) -> tuple:
        i, f, local, ext = job
        # 실제 파일 이름으로 판별(이름 규칙도 평가). AI로 보낼 때는 화주명이 가려진다
        name = Path(str(f.get("path") or f"doc{i}{ext}")).name
        # 추출 결과 보관(data/eval/cache_<ai>/, PC 안). --reuse면 다시 부르지 않고 읽는다(비용 절약)
        cached = cache_dir / f"{f['sha256'][:16]}.json"
        if reuse and cached.exists():
            raw = json.loads(cached.read_text(encoding="utf-8"))
            return f, [ParsedDocument.model_validate(d) for d in raw]
        # 엑셀 한 파일에 CI·PL 시트가 같이 있으면 서류 여러 개(제품과 같은 함수)
        docs = extract_documents(local, name, "eval", f"eval{i}", mask_names=mask)
        cached.write_text(json.dumps([d.model_dump() for d in docs], ensure_ascii=False), "utf-8")
        return f, docs

    with ThreadPoolExecutor(max_workers=4) as pool:
        done = list(pool.map(_run, jobs))
    # 제품과 같게 폴더 1개 = 선적 1건: 폴더의 B/L 서류 번호(없으면 다른 서류 번호)를 폴더 전체에 쓴다.
    # CI·PL에는 B/L 번호가 없는 경우가 많아 서류 자체 번호로만 묶으면 품목 줄이 이어지지 않는다.
    folders: dict[str, list[ParsedDocument]] = defaultdict(list)
    for f, docs_in_file in done:
        for doc in docs_in_file:
            kinds[(f.get("doc_kind") or "(비어 있음)", doc.doc_type)] += 1
            folders[str(Path(str(f.get("path") or "")).parent)].append(doc)
    for docs in folders.values():
        bl_doc = next((d for d in docs if d.doc_type == "BL" and d.bl_no), None)
        bl_no = (
            bl_doc
            or next((d for d in docs if d.bl_no), None)
            or ParsedDocument(doc_id="", shipper_id="", folder_id="", doc_type="BL")
        ).bl_no
        if not bl_no:
            continue
        b = by_bl[_norm(bl_no)]
        b["head"].setdefault("bl_no", bl_no)
        for d in sorted(docs, key=lambda x: x.doc_type != "BL"):  # 모선은 B/L 서류 먼저
            if d.vessel and d.doc_type in ("BL", "CI", "PL"):
                b["head"].setdefault("vessel", d.vessel)
        # 품목 줄: PL(카톤·입수·순중량) 먼저, 금액은 CI
        for d in sorted(docs, key=lambda x: {"PL": 0, "CI": 1}.get(x.doc_type, 2)):
            if d.doc_type not in ("CI", "PL"):
                continue
            # 같은 서류 안 같은 모델 줄은 더한다(검역이력도 한 행으로 합침). 서류 사이에는 먼저 본 값
            sums: dict[str, dict] = {}
            for ln in d.lines:
                if not ln.model or ln.is_part:
                    continue
                cur = sums.setdefault(_norm(ln.model), {})
                for k in ("cartons", "quantity", "net_kg", "amount"):
                    if getattr(ln, k) is not None:
                        cur[k] = cur.get(k, 0) + getattr(ln, k)
                if ln.pcs() is not None:
                    cur["pcs"] = cur.get("pcs", 0) + (ln.pcs() or 0)
                if ln.qty_per_carton is not None:
                    cur.setdefault("qty_per_carton", ln.qty_per_carton)
            for m, vals in sums.items():
                cur = b["lines"].setdefault(m, {})
                for k, v in vals.items():
                    cur.setdefault(k, round(v, 4))

    # 정답 = 검역이력 파일의 화주 탭(A기업·B기업)만. 실적·실적DB·백업 탭은 검역이력 행이 아니다
    sheets = _select("samc_files", {"category": "eq.sheet", "doc_kind": "eq.history_sheet"}, token)
    gold = []
    for sh in sheets:
        gold += _select(
            "samc_sheet_rows", {"workbook": f"eq.{sh['path']}", "sheet": f"in.({GOLD_TABS})"}, token
        )

    stats = {f: [0, 0] for f in FIELDS}
    covered = {f: [0, 0] for f in FIELDS}  # 서류가 있는 선적 건(B/L)의 정답 행만
    why: dict[str, Counter] = {f: Counter() for f in FIELDS}  # 틀린 이유 태그
    for g in gold:
        cells = g.get("cells") or {}
        bl = _norm(cells.get("B/L Number"))
        if not bl:
            continue
        if bl not in by_bl:
            for col in FIELDS:
                if cells.get(col.split("(=")[0]) not in (None, ""):
                    stats[col][0] += 1
                    why[col]["B/L 서류 못 찾음"] += 1
            continue
        b = by_bl[bl]
        name = " ".join(
            str(cells.get(c) or "") for c in ("한글 제품명(모델넘버)", "영문 제품명")
        ).upper()
        line = next((v for m, v in b["lines"].items() if m and m in re.sub(r"\s+", "", name)), None)
        for col, key in FIELDS.items():
            want = cells.get(col.split("(=")[0])  # 비교용 이름 "입수(=…)"도 정답 칸은 "입수"
            if want in (None, ""):
                continue
            got = b["head"].get(key) if key in ("bl_no", "vessel") else (line or {}).get(key)
            stats[col][0] += 1
            ok = _norm(got) == _norm(want)
            stats[col][1] += int(ok)
            covered[col][0] += 1
            covered[col][1] += int(ok)
            if not ok:
                if key not in ("bl_no", "vessel") and line is None:
                    why[col]["품목 줄(모델) 못 짝지음"] += 1
                elif got in (None, ""):
                    why[col]["값 비어 있음"] += 1
                else:
                    why[col]["값 다름"] += 1

    result = {
        "ai": "on" if ai_on else "off",
        "model": llm.current_model() if ai_on else None,
        "usage": _usage_since(log_before),
        "masking": sent_stats,
        "files": len(jobs),
        "shipments_found": len(by_bl),
        "gold_rows": len(gold),
        "classification": [
            {"given_doc_kind": k[0], "ours": k[1], "count": n} for k, n in sorted(kinds.items())
        ],
        "fields": {
            c: {"compared": a, "matched": m, "rate": round(m / a, 3) if a else None}
            for c, (a, m) in stats.items()
        },
        "fields_covered": {
            c: {"compared": a, "matched": m, "rate": round(m / a, 3) if a else None}
            for c, (a, m) in covered.items()
        },
        "miss_reasons": {c: dict(v) for c, v in why.items()},
    }
    out = s.data_path / "eval" / f"eval_reader_{result['ai']}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"서류 {result['files']}개 · 선적 건(B/L) {result['shipments_found']}개 · 정답 행 {result['gold_rows']}개"
    )
    print("판별(주어진 doc_kind → 우리 판별):")
    for c in result["classification"]:
        print(f"  {c['given_doc_kind']:>14} → {c['ours']:<11} {c['count']}")
    print("칸별 일치율:")
    for c, v in result["fields"].items():
        rate = "-" if v["rate"] is None else f"{v['rate'] * 100:.1f}%"
        print(f"  {c:<10} {v['matched']}/{v['compared']}  {rate}  {result['miss_reasons'][c]}")
    print("서류가 있는 선적 건만:")
    for c, v in result["fields_covered"].items():
        rate = "-" if v["rate"] is None else f"{v['rate'] * 100:.1f}%"
        print(f"  {c:<10} {v['matched']}/{v['compared']}  {rate}")
    print(f"AI 호출: {result['usage']}")
    print(f"보낸 글자 가리기: {sent_stats}")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
