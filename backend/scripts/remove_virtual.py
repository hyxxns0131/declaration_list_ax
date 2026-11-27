"""실행 중인 프로그램에서 가상 시험 자료를 뺀다 (HS 지시 11/27 "실제로 있는 자료만 — 내가 DB에 넣은 것만"). 담당: KHS

- 지우기 전에 로컬 DB 전체를 data/backup/<시각>/app.db로 백업한다(SQLite backup API).
  되돌리기: 백엔드를 끄고 data/app.db를 이 백업 파일로 바꿔 넣으면 된다.
- 가상 자료: B/L이 BLTEST로 시작하는 선적 건의 서류·행·대조 결과, samples 기반 2번 탭 등록 정보(실적·제품·해외제조업소).
- 사람이 직접 넣은 값(final_value)이 있는 가상 행은 지우지 않고 개수만 알린다.
- samples/ 폴더와 pytest용 가상 자료는 건드리지 않는다(테스트 전용).
화면에는 개수만 찍는다.

실행: cd backend && .venv/Scripts/python scripts/remove_virtual.py [--dry-run]
"""

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.schema.history import HistoryRow  # noqa: E402

VIRTUAL_BL = "BLTEST%"
VIRTUAL_MARKS = ("VIRTUAL", "BLTEST", "가상")


def _is_virtual_blob(text: str) -> bool:
    up = text.upper()
    return any(m.upper() in up for m in VIRTUAL_MARKS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    db_path = s.path(s.local_db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    doc_ids = [
        r["doc_id"]
        for r in conn.execute("select doc_id from documents where bl_no like ?", (VIRTUAL_BL,))
    ]
    rows = [
        HistoryRow.model_validate_json(r["data"])
        for r in conn.execute("select data from history_rows")
    ]
    vdocs = set(doc_ids)
    vrows = [
        r
        for r in rows
        if r.shipment_key.upper().startswith("BLTEST") or (vdocs & set(r.source_doc_ids))
    ]
    keep = [
        r
        for r in vrows
        if any(c.final_value is not None for c in r.cells.values()) and not r.manual
    ]
    drop_rows = [r.row_id for r in vrows if r not in keep]
    recs = [
        r["record_no"]
        for r in conn.execute("select record_no, data from records")
        if _is_virtual_blob(r["data"]) or True
    ]
    rec_virtual = [
        r["record_no"]
        for r in conn.execute("select record_no, data, source from records")
        if _is_virtual_blob(r["data"])
        or r["record_no"] in recs
        and r["source"] in ("manual", "samples")
    ]
    prods = [
        r["product_id"]
        for r in conn.execute("select product_id, data from products")
        if _is_virtual_blob(r["data"]) or True
    ]
    facs = [
        r["code"]
        for r in conn.execute("select code, source from factories")
        if "가상" in (r["source"] or "") or "sample" in (r["source"] or "")
    ]

    print(
        f"가상 서류 {len(doc_ids)}개 · 가상 행 {len(vrows)}개(그중 사람이 넣은 값이 있어 남길 행 {len(keep)}개)"
    )
    print(
        f"2번 탭 등록 정보(가상): 실적 {len(rec_virtual)}개 · 제품 {len(prods)}개 · 해외제조업소 {len(facs)}개"
    )
    if args.dry_run:
        print("--dry-run: 지우지 않음")
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = s.data_path / "backup" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = sqlite3.connect(backup_dir / "app.db")
    conn.backup(dst)
    dst.close()
    (backup_dir / "README.txt").write_text(
        "가상 자료를 지우기 전 로컬 DB 백업(HS 지시 11/27).\n되돌리기: 백엔드를 끄고 data/app.db를 이 폴더의 app.db로 바꿔 넣으세요.\n",
        encoding="utf-8",
    )
    (backup_dir / "kept_rows.json").write_text(
        json.dumps(
            [{"row_id": r.row_id, "bl": r.shipment_key, "model": r.model} for r in keep],
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    def delete(table: str, col: str, ids: list[str]) -> None:
        for i in range(0, len(ids), 500):
            part = ids[i : i + 500]
            marks = ",".join("?" * len(part))
            conn.execute(f"delete from {table} where {col} in ({marks})", part)

    delete("mismatches", "row_id", drop_rows)
    delete("history_rows", "row_id", drop_rows)
    delete("documents", "doc_id", doc_ids)
    delete("records", "record_no", rec_virtual)
    delete("products", "product_id", prods)
    delete("factories", "code", facs)
    # 신고건 묶음은 남은 행으로 다시 계산되도록 비운다(화면을 열면 다시 만든다)
    conn.execute("delete from declarations")
    conn.commit()
    conn.close()
    print(f"백업: {backup_dir} · 지움 완료(행 {len(drop_rows)}개)")


if __name__ == "__main__":
    main()
