"""작업 데이터 2: 서류 대조·신고건·실적·제품·알림·캐시·품목사항 파일. SQL은 core/storage 안에만. 담당: KHS

표 정의는 local_db.MIGRATIONS 3번. work_db.py가 길어져 나눴다. 기능 폴더는 work_db에서 import한다.
"""

import json

from app.core.schema.declaration import Declaration
from app.core.schema.document import ParsedDocument
from app.core.schema.record import Record
from app.core.storage.local_db import transaction


# ── 행·서류 보조 ───────────────────────────────────────
def delete_rows(row_ids: list[str]) -> None:
    if not row_ids:
        return
    marks = ",".join("?" * len(row_ids))
    with transaction() as conn:
        conn.execute(f"delete from history_rows where row_id in ({marks})", row_ids)
        conn.execute(f"delete from mismatches where row_id in ({marks})", row_ids)


def move_row(row_id: str, before_row_id: str | None) -> None:
    """행 이동(담당자가 옮긴 순서를 그대로 따른다, RULES 11-9). before가 None이면 맨 뒤."""
    with transaction() as conn:
        rows = conn.execute("select row_id from history_rows order by seq").fetchall()
        order = [r["row_id"] for r in rows if r["row_id"] != row_id]
        idx = order.index(before_row_id) if before_row_id in order else len(order)
        order.insert(idx, row_id)
        for i, rid in enumerate(order, start=1):
            conn.execute("update history_rows set seq = ? where row_id = ?", (i, rid))


def documents_for_bl(shipper_id: str, bl_no: str) -> list[ParsedDocument]:
    """같은 B/L로 올라온 서류 전부(재업로드 포함, 오래된 것 → 최근)."""
    with transaction() as conn:
        rs = conn.execute(
            "select parsed from documents where shipper_id = ? and bl_no = ? order by created_at, rowid",
            (shipper_id, bl_no),
        ).fetchall()
    return [ParsedDocument.model_validate_json(r["parsed"]) for r in rs]


def list_documents(shipper_id: str) -> list[tuple[ParsedDocument, str, str, str]]:
    """화주의 서류 전부 (판독 결과, 파일 이름, 올린 시각, 선적 건 B/L) — 오래된 것 → 최근. 선적 건 목록용.
    선적 건 B/L은 폴더 단위로 맞춘 값(set_folder_bl)이라 서류 하나의 B/L 오타와 다를 수 있다."""
    with transaction() as conn:
        rs = conn.execute(
            "select parsed, filename, created_at, bl_no from documents where shipper_id = ?"
            " order by created_at",
            (shipper_id,),
        ).fetchall()
    return [
        (
            ParsedDocument.model_validate_json(r["parsed"]),
            r["filename"],
            r["created_at"],
            r["bl_no"] or "",
        )
        for r in rs
    ]


def set_folder_bl(folder_id: str, bl_no: str) -> None:
    """폴더 단위로 B/L 번호를 맞춘다(B/L 번호는 폴더 안 서류 한 곳에만 있을 수 있다)."""
    with transaction() as conn:
        conn.execute("update documents set bl_no = ? where folder_id = ?", (bl_no, folder_id))


# ── 서류 대조 결과 ─────────────────────────────────────
def save_mismatches(row_id: str, items: list[dict]) -> None:
    with transaction() as conn:
        conn.execute("delete from mismatches where row_id = ?", (row_id,))
        for it in items:
            conn.execute(
                "insert into mismatches(row_id, item, data) values (?, ?, ?)",
                (row_id, it["item"], json.dumps(it, ensure_ascii=False)),
            )


def get_mismatches(row_id: str) -> list[dict]:
    with transaction() as conn:
        rs = conn.execute(
            "select data from mismatches where row_id = ? order by rowid", (row_id,)
        ).fetchall()
    return [json.loads(r["data"]) for r in rs]


# ── 신고건 ────────────────────────────────────────────
def save_declarations(shipper_id: str, decls: list[Declaration]) -> None:
    """화주의 신고건을 통째로 바꾼다(신고건은 행에서 다시 계산하는 값)."""
    with transaction() as conn:
        conn.execute("delete from declarations where shipper_id = ?", (shipper_id,))
        for i, d in enumerate(decls):
            conn.execute(
                "insert into declarations(declaration_id, shipper_id, seq, data) values (?, ?, ?, ?)",
                (d.declaration_id, shipper_id, i, d.model_dump_json()),
            )


def list_declarations(shipper_id: str) -> list[Declaration]:
    with transaction() as conn:
        rs = conn.execute(
            "select data from declarations where shipper_id = ? order by seq", (shipper_id,)
        ).fetchall()
    return [Declaration.model_validate_json(r["data"]) for r in rs]


# ── 실적 ──────────────────────────────────────────────
def save_record(rec: Record, shipper_id: str = "") -> None:
    with transaction() as conn:
        conn.execute(
            "insert or replace into records(record_no, shipper_id, data, updated_at)"
            " values (?, ?, ?, datetime('now'))",
            (rec.record_no, shipper_id, rec.model_dump_json()),
        )


def get_record(record_no: str) -> tuple[Record, str] | None:
    with transaction() as conn:
        r = conn.execute(
            "select data, shipper_id from records where record_no = ?", (record_no,)
        ).fetchone()
    return (Record.model_validate_json(r["data"]), r["shipper_id"]) if r else None


def list_records(shipper_id: str | None = None) -> list[tuple[Record, str]]:
    sql, args = "select data, shipper_id from records", ()
    if shipper_id:
        sql, args = sql + " where shipper_id in (?, '')", (shipper_id,)
    with transaction() as conn:
        rs = conn.execute(sql + " order by record_no", args).fetchall()
    return [(Record.model_validate_json(r["data"]), r["shipper_id"]) for r in rs]


# ── 제품(수입신고서·성적서 등록) ─────────────────────────
def save_product(product_id: str, shipper_id: str, model: str, data: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "insert or replace into products(product_id, shipper_id, model, data, updated_at)"
            " values (?, ?, ?, ?, datetime('now'))",
            (product_id, shipper_id, model.upper(), json.dumps(data, ensure_ascii=False)),
        )


def list_products(shipper_id: str | None = None, model: str | None = None) -> list[dict]:
    sql, args = "select data from products where 1=1", []
    if shipper_id:
        sql += " and shipper_id = ?"
        args.append(shipper_id)
    if model:
        sql += " and model = ?"
        args.append(model.upper())
    with transaction() as conn:
        rs = conn.execute(sql + " order by updated_at", args).fetchall()
    return [json.loads(r["data"]) for r in rs]


# ── 등록 후보(올리기 → 확인 → 등록) ──────────────────────
def save_upload(upload_id: str, shipper_id: str, data: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "insert or replace into uploads(upload_id, shipper_id, data) values (?, ?, ?)",
            (upload_id, shipper_id, json.dumps(data, ensure_ascii=False)),
        )


def get_upload(upload_id: str) -> dict | None:
    with transaction() as conn:
        r = conn.execute("select data from uploads where upload_id = ?", (upload_id,)).fetchone()
    return json.loads(r["data"]) if r else None


# ── 만료 알림 발송 기록 ──────────────────────────────────
def alert_sent(record_no: str, stage: int) -> bool:
    with transaction() as conn:
        r = conn.execute(
            "select 1 from alerts_sent where record_no = ? and stage = ?", (record_no, stage)
        ).fetchone()
    return r is not None


def mark_alert_sent(record_no: str, stage: int, recipients: str) -> None:
    with transaction() as conn:
        conn.execute(
            "insert or ignore into alerts_sent(record_no, stage, recipients) values (?, ?, ?)",
            (record_no, stage, recipients),
        )


def list_alerts_sent() -> list[dict]:
    with transaction() as conn:
        rs = conn.execute("select * from alerts_sent order by sent_at desc").fetchall()
    return [dict(r) for r in rs]


# ── 캐시(관세환율·외부 API) ──────────────────────────────
def cache_get(key: str, max_age_hours: float | None = None) -> object | None:
    sql = "select data from api_cache where key = ?"
    args: list[object] = [key]
    if max_age_hours is not None:
        sql += " and at >= datetime('now', ?)"
        args.append(f"-{max_age_hours} hours")
    with transaction() as conn:
        r = conn.execute(sql, args).fetchone()
    return json.loads(r["data"]) if r else None


def cache_put(key: str, value: object) -> None:
    with transaction() as conn:
        conn.execute(
            "insert or replace into api_cache(key, data, at) values (?, ?, datetime('now'))",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def fx_get(week_key: str) -> dict | None:
    with transaction() as conn:
        r = conn.execute("select data from fx_cache where week_key = ?", (week_key,)).fetchone()
    return json.loads(r["data"]) if r else None


def fx_put(week_key: str, rates: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "insert or replace into fx_cache(week_key, data) values (?, ?)",
            (week_key, json.dumps(rates, ensure_ascii=False)),
        )


# ── 품목사항 파일 ──────────────────────────────────────
def save_item_file(
    file_id: str, shipper_id: str, filename: str, path: str, row_ids: list[str]
) -> None:
    with transaction() as conn:
        conn.execute(
            "insert into item_files(file_id, shipper_id, filename, file_path, row_ids)"
            " values (?, ?, ?, ?, ?)",
            (file_id, shipper_id, filename, path, json.dumps(row_ids)),
        )


def get_item_file(file_id: str) -> tuple[str, str] | None:
    """(파일 이름, DATA_DIR 기준 경로)"""
    with transaction() as conn:
        r = conn.execute(
            "select filename, file_path from item_files where file_id = ?", (file_id,)
        ).fetchone()
    return (r["filename"], r["file_path"]) if r else None


# ── 해외제조업소 코드(A2-5, 표 정의는 local_db 버전 5) ──────────
FACTORY_COLUMNS = ("code", "name", "address", "registered_on", "expires_on", "status", "source")


def list_factories() -> list[dict]:
    with transaction() as conn:
        rs = conn.execute(
            f"select {', '.join(FACTORY_COLUMNS)} from factories order by code"
        ).fetchall()
    return [dict(r) for r in rs]


def get_factory(code: str) -> dict | None:
    with transaction() as conn:
        r = conn.execute(
            f"select {', '.join(FACTORY_COLUMNS)} from factories where code = ?", (code,)
        ).fetchone()
    return dict(r) if r else None


def save_factory(row: dict) -> None:
    vals = [row.get(c) for c in FACTORY_COLUMNS]
    with transaction() as conn:
        conn.execute(
            f"insert or replace into factories({', '.join(FACTORY_COLUMNS)}, updated_at)"
            f" values ({', '.join('?' * len(FACTORY_COLUMNS))}, datetime('now'))",
            vals,
        )
