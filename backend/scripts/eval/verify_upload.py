"""올린 서류가 제대로 읽혔는지 검증 (HS 요청 11/27). PC 안에서만 돌리고 결과는 data/eval/verify_upload.json. 담당: KHS

1) 서류마다: 어떻게 읽었나(엑셀 openpyxl·xlrd / PDF pdfplumber 글자·표 / OpenAI 멀티모달·JSON), 서류 종류, 경고,
   머리 칸(B/L·모선·인보이스 번호·통화)과 품목 줄(모델·수량·카톤·순중량·금액)을 얼마나 채웠나.
2) 실제 B/L(검역이력 시트에 정답이 있는 건): 완성된 검역 리스트(③) 행을 정답 시트 행과 칸별로 대조
   (B/L·모선·카톤·입수·순중량·가격). 정답은 Supabase samc_sheet_rows의 화주 탭(A기업·B기업), 읽기만.
화면·로그에는 개수·비율만 찍는다(서류 값·화주명은 찍지 않음). 상세는 data/eval/verify_upload.json(PC 안).

실행: cd backend && .venv/Scripts/python scripts/eval/verify_upload.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core import llm  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.masking import all_names  # noqa: E402
from app.core.storage import work_db, work_db_more  # noqa: E402

HEAD = ("bl_no", "vessel", "invoice_no", "currency")
LINE = ("model", "quantity", "cartons", "net_kg", "amount")
GOLD_COLS = {
    "B/L Number": "B/L Number",
    "모선명": "모선명",
    "카톤 수": "카톤 수",
    "입수": "입수",
    "순중량": "순중량",
    "가격(수출국)": "가격(수출국)",
}


def _norm(v: object) -> str:
    s = str(v or "").strip().upper()
    try:
        return f"{float(s.replace(',', '')):g}"
    except ValueError:
        return re.sub(r"\s+", "", s)


def _method(doc) -> str:  # noqa: ANN001
    srcs = set(doc.sources.values())
    if any(s.startswith("llm:image") for s in srcs) or doc.parser == "llm" and not doc.sources:
        return "OpenAI 멀티모달(가린 PNG)·JSON"
    if any(s.startswith("llm") for s in srcs):
        return ("엑셀" if doc.parser == "excel" else "PDF 글자·표") + " + 빈 칸 OpenAI(JSON)"
    return {"excel": "엑셀(openpyxl·xlrd)", "pdf": "PDF 글자·표(pdfplumber)"}.get(
        doc.parser, doc.parser
    )


def documents_report(shippers: list[str]) -> list[dict]:
    out = []
    for sid in shippers:
        for doc, _filename, _created, ship_bl in work_db_more.list_documents(sid):
            lines = doc.lines
            out.append(
                {
                    "shipper": sid,
                    "doc_type": doc.doc_type,
                    "method": _method(doc),
                    "warnings": doc.warnings,
                    "has_folder_bl": bool(ship_bl),
                    "head_filled": {k: bool(getattr(doc, k)) for k in HEAD},
                    "lines": len(lines),
                    "line_filled": {
                        k: sum(1 for ln in lines if getattr(ln, k, None) not in (None, ""))
                        for k in LINE
                    },
                }
            )
    return out


def gold_report(shippers: list[str]) -> dict:
    """정답 시트와 ③ 행 대조. Supabase 로그인이 안 되면 건너뛴다."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("ev", Path(__file__).with_name("eval_reader.py"))
    ev = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(ev)  # type: ignore[union-attr]
    s = get_settings()
    token = ev._supabase_login(s.admin_username, s.admin_password)
    if not token:
        return {"skipped": "Supabase 로그인 불가"}
    gold = ev._select("samc_sheet_rows", {"sheet": "in.(A기업,B기업)"}, token)
    by_bl: dict[str, list[dict]] = defaultdict(list)
    for g in gold:
        by_bl[_norm((g.get("cells") or {}).get("B/L Number"))].append(g["cells"])
    stats = {c: [0, 0] for c in GOLD_COLS}
    miss: dict[str, Counter] = {c: Counter() for c in GOLD_COLS}
    matched_bls = set()
    for sid in shippers:
        for r in work_db.list_rows(sid):
            bl = _norm(r.text("B/L Number"))
            if not bl or bl not in by_bl:
                continue
            name = re.sub(r"\s+", "", r.text("한글 제품명(모델넘버)").upper() + r.model.upper())
            cand = [
                g
                for g in by_bl[bl]
                if r.model
                and r.model.upper().replace(" ", "")
                in re.sub(r"\s+", "", str(g.get("한글 제품명(모델넘버)") or "").upper())
            ]
            if not cand:
                continue
            matched_bls.add(bl)
            g = cand[0]
            for col, gcol in GOLD_COLS.items():
                want = g.get(gcol)
                if want in (None, ""):
                    continue
                got = r.val(col)
                stats[col][0] += 1
                ok = _norm(got) == _norm(want)
                stats[col][1] += int(ok)
                if not ok:
                    miss[col]["비어 있음" if got in (None, "") else "값 다름"] += 1
            _ = name
    return {
        "bls_compared": len(matched_bls),
        "fields": {
            c: {"compared": a, "matched": m, "rate": round(m / a, 3) if a else None}
            for c, (a, m) in stats.items()
        },
        "miss": {c: dict(v) for c, v in miss.items()},
    }


def main() -> None:
    shippers = ["A", "B"]
    docs = documents_report(shippers)
    gold = gold_report(shippers)
    result = {
        "ai": {
            "ready": llm.ready(),
            "send_allowed": llm.send_allowed(),
            "mask_names": len(all_names()),
        },
        "documents": docs,
        "gold": gold,
    }
    out = get_settings().data_path / "eval" / "verify_upload.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    print(
        f"AI: 켜짐={result['ai']['ready']} · 서류 보내기 허용={result['ai']['send_allowed']} · 화주명 목록 {result['ai']['mask_names']}개"
    )
    print(f"서류 {len(docs)}개 · 읽은 방법:", dict(Counter(d["method"] for d in docs)))
    print("서류 종류:", dict(Counter(d["doc_type"] for d in docs)))
    warn = Counter(w.split(" - ")[0] for d in docs for w in d["warnings"])
    print("경고:", dict(warn) or "없음")
    cipl = [d for d in docs if d["doc_type"] in ("CI", "PL")]
    if cipl:
        no_lines = sum(1 for d in cipl if d["lines"] == 0)
        tot = sum(d["lines"] for d in cipl)
        fill = {k: sum(d["line_filled"][k] for d in cipl) for k in LINE}
        print(
            f"CI·PL {len(cipl)}개: 품목 줄을 못 읽은 서류 {no_lines}개 · 품목 줄 {tot}개 중 채운 칸",
            fill,
        )
    if "skipped" in gold:
        print("정답 대조:", gold["skipped"])
    else:
        print(f"정답 대조(검역이력 시트에 있는 B/L {gold['bls_compared']}건):")
        for c, v in gold["fields"].items():
            rate = "-" if v["rate"] is None else f"{v['rate'] * 100:.0f}%"
            print(f"  {c:<10} {v['matched']}/{v['compared']} {rate} {gold['miss'][c] or ''}")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
