"""작업 데이터(서류 판독 결과, 검역이력 행) 읽기·쓰기. SQL은 core/storage 안에만 둔다(RULES 5-1). 담당: KHS

기능 폴더는 이 함수만 부른다. 표 정의는 local_db.MIGRATIONS 2번. 나머지 표는 work_db_more.py.
"""

from app.core.schema.document import ParsedDocument
from app.core.schema.history import HistoryRow
from app.core.storage.local_db import transaction


# ── 서류 ──────────────────────────────────────────────
def save_document(doc: ParsedDocument, filename: str, file_path: str) -> None:
    with transaction() as conn:
        conn.execute(
            "insert or replace into documents"
            "(doc_id, shipper_id, folder_id, bl_no, doc_type, filename, file_path, parsed)"
            " values (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                doc.doc_id,
                doc.shipper_id,
                doc.folder_id,
                doc.bl_no,
                doc.doc_type,
                filename,
                file_path,
                doc.model_dump_json(),
            ),
        )


def get_document(doc_id: str) -> tuple[ParsedDocument, str, str] | None:
    """(판독 결과, 파일 이름, 파일 경로)"""
    with transaction() as conn:
        r = conn.execute(
            "select parsed, filename, file_path from documents where doc_id = ?", (doc_id,)
        ).fetchone()
    if not r:
        return None
    return ParsedDocument.model_validate_json(r["parsed"]), r["filename"], r["file_path"]


def documents_by_ids(doc_ids: list[str]) -> list[ParsedDocument]:
    if not doc_ids:
        return []
    marks = ",".join("?" * len(doc_ids))
    with transaction() as conn:
        rs = conn.execute(
            f"select parsed from documents where doc_id in ({marks})", doc_ids
        ).fetchall()
    return [ParsedDocument.model_validate_json(r["parsed"]) for r in rs]


# ── 검역이력 행 ────────────────────────────────────────
def _bl(row: HistoryRow) -> str:
    cell = row.cells.get("B/L Number")
    v = cell.value if cell else None
    return str(v or "")


def save_rows(rows: list[HistoryRow]) -> None:
    """행 저장(있으면 교체). 새 행은 표 맨 뒤에 붙는다."""
    if not rows:
        return
    with transaction() as conn:
        (next_seq,) = conn.execute("select coalesce(max(seq), 0) + 1 from history_rows").fetchone()
        for row in rows:
            old = conn.execute(
                "select seq from history_rows where row_id = ?", (row.row_id,)
            ).fetchone()
            seq = old["seq"] if old else next_seq
            if not old:
                next_seq += 1
            conn.execute(
                "insert or replace into history_rows(row_id, shipper_id, bl_no, seq, data, updated_at)"
                " values (?, ?, ?, ?, ?, datetime('now'))",
                (row.row_id, row.shipper_id, _bl(row), seq, row.model_dump_json()),
            )


def list_rows(shipper_id: str | None = None) -> list[HistoryRow]:
    sql = "select data from history_rows"
    args: tuple[str, ...] = ()
    if shipper_id:
        sql += " where shipper_id = ?"
        args = (shipper_id,)
    with transaction() as conn:
        rs = conn.execute(sql + " order by seq", args).fetchall()
    return [HistoryRow.model_validate_json(r["data"]) for r in rs]


def rows_by_bl(shipper_id: str, bl_no: str) -> list[HistoryRow]:
    with transaction() as conn:
        rs = conn.execute(
            "select data from history_rows where shipper_id = ? and bl_no = ? order by seq",
            (shipper_id, bl_no),
        ).fetchall()
    return [HistoryRow.model_validate_json(r["data"]) for r in rs]


def get_row(row_id: str) -> HistoryRow | None:
    with transaction() as conn:
        r = conn.execute("select data from history_rows where row_id = ?", (row_id,)).fetchone()
    return HistoryRow.model_validate_json(r["data"]) if r else None


def get_rows(row_ids: list[str]) -> list[HistoryRow]:
    """요청한 순서 그대로. 없는 id는 빠진다."""
    found = {r.row_id: r for r in (get_row(i) for i in row_ids) if r}
    return [found[i] for i in row_ids if i in found]
