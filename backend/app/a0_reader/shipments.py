"""선적 건 목록: 화주의 올린 서류를 B/L 번호로 묶어 서류별 추출값과 빠진 서류를 보여 준다(화면 ①).
폴더 1개 = 선적서류 1건, B/L 번호로 CI·PL·B/L을 한 선적 건으로 묶는다(RULES 11-1). 읽기만. 담당: KHS [신규]
(검역 리스트 탭 1단계, HS 요청 11/26)
"""

from app.a1_history.missing.service import MARK_BL, MARK_CI_PL
from app.core.schema.document import ParsedDocument
from app.core.storage import work_db_more

MAIN_TYPES = ("CI", "PL", "BL")
NO_BL = "(B/L 번호 없음)"


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
    out = []
    for g in groups.values():
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
        out.append(g)
    out.sort(key=lambda g: g["uploaded_at"], reverse=True)
    return out
