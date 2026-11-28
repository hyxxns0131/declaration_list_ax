"""선적 건 목록: 화주의 올린 서류를 B/L 번호로 묶어 서류별 추출값과 빠진 서류를 보여 준다(화면 ①).
폴더 1개 = 선적서류 1건, B/L 번호로 CI·PL·B/L을 한 선적 건으로 묶는다(RULES 11-1). 읽기만. 담당: KHS [신규]
(검역 리스트 탭 1단계, HS 요청 11/26)
"""

from app.a1_history.missing.service import MARK_BL, MARK_CI_PL
from app.core.schema.document import ParsedDocument
from app.core.storage import work_db, work_db_more

MAIN_TYPES = ("CI", "PL", "BL")
NO_BL = "(B/L 번호 없음)"

# 서류 상태(화면에 글자로 보인다, HS 요청 11/27 "'?' 대신 말로"). 문구는 frontend lib/text/reader.ts
UNREADABLE = ("서류 판독 실패", "AI 판독 꺼짐", "화주명을 가리지 못해", "화주명 목록이 없어")
UNKNOWN = "서류 종류 확인 필요"
# 다음 할 일(카드의 버튼 하나): 위에서부터 먼저
NEXT_ORDER = ("enter_bl", "upload_missing", "fix_docs", "review", "done")


def doc_state(doc: dict | None) -> str:
    """ok(읽음) / missing(없음) / unreadable(값을 못 읽음) / unknown(종류를 모름) / check(일부 확인 필요)."""
    if doc is None:
        return "missing"
    warns = doc["warnings"]
    if any(w.startswith(UNREADABLE) for w in warns):
        return "unreadable"
    if UNKNOWN in warns:
        return "unknown"
    return "check" if warns else "ok"


def _next(g: dict) -> str:
    states = g["doc_states"]
    if not g["bl_no"]:
        return "enter_bl"
    if any(states[t] == "missing" for t in MAIN_TYPES):
        return "upload_missing"
    if any(s in ("unreadable", "unknown") for s in states.values()):
        return "fix_docs"
    if g["attention_rows"]:
        return "review"
    return "done"


def _doc_summary(doc: ParsedDocument, filename: str) -> dict:
    return {
        "doc_id": doc.doc_id,
        "doc_type": doc.doc_type,
        "filename": filename,
        "parser": doc.parser,
        "warnings": doc.warnings,
        "sources": doc.sources,
        "values": {
            "bl_no": doc.bl_no,
            "invoice_no": doc.invoice_no,
            "doc_date": doc.doc_date,
            "vessel": doc.vessel,
            "manufacturer_name": doc.manufacturer_name,
            "currency": doc.currency,
            "total_amount": doc.total_amount,
            "total_cartons": doc.total_cartons,
            "total_gross_kg": doc.total_gross_kg,
            "line_count": len(doc.lines),
        },
        "lines": [ln.model_dump() for ln in doc.lines],
    }


def list_shipments(shipper_id: str) -> list[dict]:
    """[{bl_no, folder_ids, documents: {CI|PL|BL|CO: 최신 서류 요약}, missing: [...], missing_marks, status}]"""
    groups: dict[str, dict] = {}
    for doc, filename, created, ship_bl in work_db_more.list_documents(shipper_id):
        if doc.doc_type in ("PHOTO", "LABEL"):
            continue
        key = (
            ship_bl or f"{NO_BL}:{doc.folder_id}"
        )  # 폴더 단위 B/L (서류 하나의 오타로 갈리지 않게)
        g = groups.setdefault(
            key,
            {
                "bl_no": ship_bl,
                "folder_ids": [],
                "documents": {},
                "uploaded_at": created,
            },
        )
        if doc.folder_id not in g["folder_ids"]:
            g["folder_ids"].append(doc.folder_id)
        g["documents"][doc.doc_type] = _doc_summary(doc, filename)  # 같은 종류는 최근 것
        g["uploaded_at"] = max(g["uploaded_at"], created)
    all_rows = work_db.list_rows(shipper_id)
    files_of: dict[str, list[str]] = {}
    for doc, filename, _created, ship_bl in work_db_more.list_documents(shipper_id):
        key = ship_bl or f"{NO_BL}:{doc.folder_id}"
        if filename not in files_of.setdefault(key, []):
            files_of[key].append(filename)
    out = []
    for key, g in groups.items():
        have = set(g["documents"])
        missing = [t for t in MAIN_TYPES if t not in have]
        marks = []
        if "CI" in missing or "PL" in missing:
            marks.append(MARK_CI_PL)
        if "BL" in missing:
            marks.append(MARK_BL)
        warns = sum(len(d["warnings"]) for d in g["documents"].values())
        g.update(
            missing=missing,
            missing_marks=marks,
            status="자료 추가 필요"
            if missing
            else ("확인 필요" if warns or not g["bl_no"] else "추출 완료"),
        )
        ids = {d["doc_id"] for d in g["documents"].values()}
        rows = [r for r in all_rows if ids & set(r.source_doc_ids)]
        g["files"] = files_of.get(key, [])
        g["row_count"] = len(rows)
        g["attention_rows"] = sum(1 for r in rows if r.status in ("자료 추가 필요", "확인 필요"))
        g["locked"] = any(r.locked for r in rows)
        # 품목(모델) → 검역 리스트 행(② 그 행으로 가기). 키: "모델|부분품 여부(0·1)"
        g["row_ids"] = {f"{r.model.upper()}|{int(r.is_part)}": r.row_id for r in rows if r.model}
        g["doc_states"] = {
            t: doc_state(g["documents"].get(t)) for t in g["documents"].keys() | set(MAIN_TYPES)
        }
        g["next"] = _next(g)
        out.append(g)
    # 할 일이 있는 건이 위, 끝난 건이 아래. 같은 단계 안에서는 최근 것 먼저
    out.sort(key=lambda g: g["uploaded_at"], reverse=True)
    out.sort(key=lambda g: NEXT_ORDER.index(g["next"]))
    return out
