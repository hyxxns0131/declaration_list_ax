"""서류 파일 1개 → ParsedDocument. 엑셀·글자 PDF는 규칙으로, 안 되면 AI. 담당: KHS [개선] A0-1

공개 함수: extract_file()
"""

import uuid
from pathlib import Path

from app.a0_reader.classify.service import IMAGE_EXT, classify
from app.a0_reader.extract.ai_read import read_with_ai
from app.a0_reader.extract.excel import read_excel
from app.a0_reader.extract.grid_parse import GridResult, parse_grid, to_date_text, to_float
from app.a0_reader.extract.pdf import read_pdf
from app.core.schema.document import ParsedDocument

UNKNOWN_TYPE_WARNING = "서류 종류 확인 필요"
READ_FAIL_WARNING = "서류 판독 실패 - 파일 확인 필요"  # RULES 11-1 기존 문구


def _from_grid(res: GridResult, doc: ParsedDocument) -> None:
    h = res.head
    doc.bl_no = h.get("bl_no", "").replace(" ", "")
    doc.invoice_no = h.get("invoice_no", "")
    # B/L의 날짜는 선적일(on board)이 우선
    doc.doc_date = h.get("on_board_date") or h.get("doc_date", "")
    doc.vessel = h.get("vessel", "")
    doc.manufacturer_name = h.get("manufacturer_name", "")
    doc.manufacturer_address = h.get("manufacturer_address", "")
    doc.currency = h.get("currency", "").upper()
    doc.lines = res.lines
    amounts = [ln.amount for ln in res.lines if ln.amount is not None]
    cartons = [ln.cartons for ln in res.lines if ln.cartons is not None]
    sum_amount = sum(amounts) if amounts else None
    sum_cartons = sum(cartons) if cartons else None
    doc.total_amount = res.totals.get("amount", sum_amount)
    doc.total_cartons = to_float(h.get("total_cartons")) or res.totals.get("cartons", sum_cartons)
    doc.total_gross_kg = to_float(h.get("total_gross_kg")) or res.totals.get("gross_kg")


def extract_file(
    path: Path,
    filename: str,
    shipper_id: str,
    folder_id: str,
    mask_names: list[str] | None = None,
) -> ParsedDocument:
    ext = path.suffix.lower()
    doc = ParsedDocument(
        doc_id=uuid.uuid4().hex[:12],
        shipper_id=shipper_id,
        folder_id=folder_id,
        doc_type="PHOTO",
    )
    if ext in IMAGE_EXT:
        doc.doc_type = classify(filename) or "PHOTO"
        doc.parser = "excel"
        return doc  # 사진·라벨은 판독하지 않는다(사진만으로 재질 확정 금지, AGENTS 7-9)

    text = ""
    try:
        if ext in (".xlsx", ".xlsm", ".xls"):
            grid = read_excel(path)
            doc.parser = "excel"
        elif ext == ".pdf":
            grid, text = read_pdf(path)
            doc.parser = "pdf"
        else:
            doc.warnings.append(f"지원하지 않는 파일 형식: {ext}")
            return doc
    except Exception:  # 손상 파일 등. 원문은 남기지 않는다
        doc.warnings.append(READ_FAIL_WARNING)
        return doc

    res = parse_grid(grid)
    doc_type = classify(filename, res.head_text or text[:300])
    if doc_type is None:
        doc.warnings.append(UNKNOWN_TYPE_WARNING)
        doc_type = "CI" if res.header_found else "BL"
    doc.doc_type = doc_type
    _from_grid(res, doc)

    # 품목 표가 필요한 서류(CI·PL)인데 못 읽었으면 AI
    needs_lines = doc_type in ("CI", "PL") and not doc.lines
    needs_head = doc_type in ("BL", "CO") and not (doc.bl_no or doc.manufacturer_name)
    if (needs_lines or needs_head) and text:
        ai = read_with_ai(doc_type, text, mask_names or [])
        if ai:
            for k, v in ai.model_dump(exclude={"lines"}).items():
                if v not in (None, "") and not getattr(doc, k):
                    setattr(doc, k, v)
            doc.lines = doc.lines or ai.lines
            doc.doc_date = to_date_text(doc.doc_date)
            doc.parser = "llm"
    if needs_lines and not doc.lines:
        doc.warnings.append(READ_FAIL_WARNING)
    return doc
