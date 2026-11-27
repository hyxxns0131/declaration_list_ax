"""서류 파일 1개 → ParsedDocument. 엑셀·글자 PDF는 규칙으로, 안 되면 AI. 담당: KHS [개선] A0-1

공개 함수: extract_file() — 파일 1개 → 서류 1개, extract_documents() — 엑셀 한 파일에 CI·PL 시트가 같이 있으면 서류 여러 개
"""

import uuid
from pathlib import Path

from app.a0_reader.classify.service import (
    IMAGE_EXT,
    classify,
    classify_shipping_name,
    classify_with_ai,
)
from app.a0_reader.extract.ai_read import grid_text, read_with_ai
from app.a0_reader.extract.excel import Grid, read_excel, read_excel_sheets
from app.a0_reader.extract.grid_parse import GridResult, parse_grid, to_date_text, to_float
from app.a0_reader.extract.pdf import page_images, read_pdf
from app.a0_reader.extract.redact import redact_pages
from app.a0_reader.extract.scan_local import OCR_BL_WARNING, bl_from_lines, ocr_text_lines
from app.core.schema.document import ParsedDocument

UNKNOWN_TYPE_WARNING = "서류 종류 확인 필요"
READ_FAIL_WARNING = "서류 판독 실패 - 파일 확인 필요"  # RULES 11-1 기존 문구
AI_OFF_WARNING = "AI 판독 꺼짐 - 스캔본·사진은 값 직접 입력 필요"
# 스캔본·사진은 화주명을 가린 PNG만 보낸다(HS 결정 11/26). 가리지 못하면 보내지 않는다
NOT_MASKED_WARNING = "화주명을 가리지 못해 AI로 보내지 않음 - 스캔본·사진 값 직접 입력 필요"


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


HEAD_FIELDS = (
    "bl_no",
    "invoice_no",
    "doc_date",
    "vessel",
    "manufacturer_name",
    "manufacturer_address",
    "currency",
)
# 서류 종류마다 꼭 있어야 하는 머리 칸 — 규칙 추출에서 빠지면 그 칸만 OpenAI로 보충한다
NEEDED_HEAD: dict[str, tuple[str, ...]] = {
    "CI": ("bl_no", "invoice_no", "doc_date", "currency"),
    "PL": ("bl_no", "invoice_no"),
    "BL": ("bl_no", "vessel", "doc_date"),
    "CO": ("manufacturer_name",),
}
FIELD_LABELS = {
    "bl_no": "B/L 번호",
    "invoice_no": "인보이스 번호",
    "doc_date": "서류 날짜",
    "currency": "통화",
    "vessel": "모선",
    "manufacturer_name": "제조사",
}


def _mark_sources(doc: ParsedDocument, source: str) -> None:
    for k in HEAD_FIELDS:
        if getattr(doc, k) and k not in doc.sources:
            doc.sources[k] = source
    if doc.lines and "lines" not in doc.sources:
        doc.sources["lines"] = source


def _fill_from_ai(doc: ParsedDocument, ai: object, source: str) -> list[str]:
    """비어 있는 칸만 AI 값으로 채운다(규칙 값은 덮지 않음). 채운 칸 이름 목록."""
    filled: list[str] = []
    for k, v in ai.model_dump(exclude={"lines"}).items():  # type: ignore[attr-defined]
        if v not in (None, "") and not getattr(doc, k):
            setattr(doc, k, v)
            doc.sources[k] = source
            filled.append(k)
    if merge_lines(doc, ai.lines, source):  # type: ignore[attr-defined]
        filled.append("lines")
    doc.doc_date = to_date_text(doc.doc_date)
    return filled


# 서류 종류마다 품목 줄에 있어야 하는 칸 — 규칙으로 비면 그 칸만 OpenAI로 채운다
LINE_NEEDS: dict[str, tuple[str, ...]] = {
    "CI": ("amount",),
    "PL": ("cartons", "net_kg"),  # 입수(카톤당 수량)는 서류에 칸이 있을 때만이라 기준에서 뺀다
}
LINE_FIELDS = ("qty_per_carton", "quantity", "cartons", "net_kg", "amount")


def _model_key(text: str) -> str:
    import re

    return re.sub(r"[^0-9A-Z]", "", text.upper())


def lines_incomplete(doc: ParsedDocument) -> bool:
    need = LINE_NEEDS.get(doc.doc_type, ())
    return any(getattr(ln, k) is None for ln in doc.lines for k in need)


def merge_lines(doc: ParsedDocument, ai_lines: list, source: str) -> int:
    """규칙으로 읽은 품목 줄의 빈 칸만 AI 줄 값으로 채운다(모델 코드로 짝짓기). 채운 칸 수.
    규칙 줄이 없으면 AI 줄을 그대로 쓴다. 규칙 값은 덮지 않는다."""
    if not ai_lines:
        return 0
    no_models = not any(ln.model for ln in doc.lines)
    if not doc.lines or no_models:
        # 규칙 줄이 없거나 모델 코드를 하나도 못 읽었으면 AI 줄을 통째로 쓴다.
        # 순서로 짝지으면 머리글·소계 줄 때문에 값이 밀린다(실제 서류: 부분품 줄에 본품 금액이 들어가 합계가 2배, HS 11/27)
        doc.lines = list(ai_lines)
        doc.sources["lines"] = source
        return sum(getattr(ln, k) is not None for ln in ai_lines for k in LINE_FIELDS)
    by_model: dict[str, list] = {}
    for a in ai_lines:
        by_model.setdefault(_model_key(a.model), []).append(a)
    n = 0
    for i, ln in enumerate(doc.lines):
        cands = by_model.get(_model_key(ln.model)) if ln.model else None
        # 모델 코드가 없거나 못 찾으면 줄 수가 같을 때만 같은 순서의 줄과 짝짓는다
        a = cands.pop(0) if cands else (ai_lines[i] if len(ai_lines) == len(doc.lines) else None)
        if a is None:
            continue
        if not ln.model and a.model:  # 규칙이 모델 코드를 못 읽은 줄(품명 칸에 섞인 경우)
            ln.model = a.model
            doc.sources["lines.model"] = source
        if not ln.description and a.description:
            ln.description = a.description
        for k in LINE_FIELDS:
            if getattr(ln, k) is None and getattr(a, k) is not None:
                setattr(ln, k, getattr(a, k))
                doc.sources[f"lines.{k}"] = source
                n += 1
    return n


def _note_blocked(doc: ParsedDocument) -> None:
    """AI가 켜져 있는데 화주명 목록이 없어 보내지 못했으면 그 이유를 남긴다(임시 안전 조치 11/26)."""
    from app.core.llm import NO_MASK_WARNING, ready, send_allowed

    if ready() and not send_allowed() and NO_MASK_WARNING not in doc.warnings:
        doc.warnings.append(NO_MASK_WARNING)


def _read_image_doc(path: Path, doc: ParsedDocument, mask: list[str]) -> ParsedDocument:
    """사진·스캔 이미지인 선적서류 → OpenAI 멀티모달. AI가 꺼져 있으면 '확인 필요'."""
    from app.core.llm import ready

    if not ready():
        doc.warnings.append(AI_OFF_WARNING)
        return doc
    if not mask:
        _note_blocked(doc)
        return doc
    pages = redact_pages([path.read_bytes()], mask)
    if not pages:
        doc.warnings.append(NOT_MASKED_WARNING)
        return doc
    ai = read_with_ai(doc.doc_type, "", mask, images=pages)
    if ai:
        _fill_from_ai(doc, ai, "llm:image")
        doc.parser = "llm"
    else:
        doc.warnings.append(READ_FAIL_WARNING)
    return doc


def extract_file(
    path: Path,
    filename: str,
    shipper_id: str,
    folder_id: str,
    mask_names: list[str] | None = None,
) -> ParsedDocument:
    """판별(파일 이름 → 본문 → OpenAI) → 규칙 추출(엑셀·글자 PDF) → 빠진 칸만 OpenAI 보충.
    스캔 PDF·이미지 서류는 페이지 이미지를 OpenAI로 읽는다. 칸마다 출처는 doc.sources."""
    mask = mask_names or []
    ext = path.suffix.lower()
    doc = ParsedDocument(
        doc_id=uuid.uuid4().hex[:12],
        shipper_id=shipper_id,
        folder_id=folder_id,
        doc_type="PHOTO",
    )
    if ext in IMAGE_EXT:
        shipping = classify_shipping_name(filename)
        if shipping:  # 이름이 CI·PL·B/L인 사진·스캔본 → 판독
            doc.doc_type = shipping
            return _read_image_doc(path, doc, mask)
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

    return _extract_grid(doc, grid, text, path, filename, mask)


def _extract_grid(
    doc: ParsedDocument,
    grid: Grid,
    text: str,
    path: Path,
    filename: str,
    mask: list[str],
    forced_type: str | None = None,
) -> ParsedDocument:
    """격자(엑셀 시트·PDF 표) + 글자 → 판별·규칙 추출·빈 칸 AI 보충."""
    ext = path.suffix.lower()
    res = parse_grid(grid)
    head = res.head_text or text[:300]
    doc_type = (
        forced_type
        or classify(filename, head)
        or classify_with_ai(filename, head or text[:1500], mask)
    )
    if doc_type is None and ext == ".pdf" and not text.strip():
        # 글자 없는 스캔본: AI를 쓸 수 있으면 화주명을 가린 첫 쪽 그림으로 종류를 묻는다(못 가리면 묻지 않음)
        from app.core.llm import send_allowed as _send_ok

        if _send_ok():
            first = redact_pages(page_images(path, max_pages=1), mask)
            if first:
                doc_type = classify_with_ai(filename, "", mask, images=first)
    ocr: list[str] = []
    if doc_type is None and ext == ".pdf":
        # AI로 못 보낸 스캔본도 PC 안 OCR 글자로 종류를 판별한다(밖으로 보내지 않음, HS 11/27).
        # 글자 층이 있어도 본문이 아닌 경우(도장·접수 표시만 글자)가 있어 글자 유무와 상관없이 본다
        ocr = ocr_text_lines(path)
        doc_type = classify(filename, " ".join(ocr)[:1500]) if ocr else None
    if doc_type is None:
        # 모르는 서류를 B/L·인보이스로 짐작하지 않는다 — '기타 서류'로 두고 담당자가 본다(HS 11/27)
        doc.warnings.append(UNKNOWN_TYPE_WARNING)
        doc_type = "OTHER"
    doc.doc_type = doc_type  # type: ignore[assignment]
    _from_grid(res, doc)
    _mark_sources(doc, doc.parser)

    scanned = ext == ".pdf" and not text.strip()
    needs_lines = doc_type in ("CI", "PL") and (not doc.lines or lines_incomplete(doc))
    missing_head = [k for k in NEEDED_HEAD.get(doc_type, ()) if not getattr(doc, k)]
    from app.core.llm import ready, send_allowed

    if (scanned or needs_lines or missing_head) and not send_allowed():
        # AI를 못 쓰면(꺼짐·키 없음·화주명 목록 없음) 페이지 그림·OCR을 만들지 않는다(느리고 쓸 데 없음)
        if scanned:
            doc.warnings.append(AI_OFF_WARNING)
        _note_blocked(doc)
    elif scanned or needs_lines or missing_head:
        # 엑셀은 격자를 탭 글자로, PDF는 글자 + (품목 줄이 필요하면) 이름을 가린 페이지 이미지
        ai_text = text if text.strip() else grid_text(grid)
        want_images = ext == ".pdf" and (scanned or needs_lines)
        images = page_images(path, redact=mask) if want_images else None
        if scanned and images:
            # 글자 없는 스캔본: OCR로 화주명 위치를 찾아 가린 쪽만 보낸다. 못 찾으면 보내지 않는다
            images = redact_pages(images, mask)
            if not images:
                doc.warnings.append(NOT_MASKED_WARNING)
        skip_ai = scanned and not images
        ai = None if skip_ai else read_with_ai(doc_type, ai_text, mask, images=images)
        if ai:
            _fill_from_ai(doc, ai, "llm:image" if scanned else "llm")
            doc.parser = "llm" if scanned or needs_lines else doc.parser
        elif scanned and not skip_ai:
            doc.warnings.append(AI_OFF_WARNING if not ready() else READ_FAIL_WARNING)
        _note_blocked(doc)
    if doc_type == "BL" and (scanned or ocr) and not doc.bl_no:
        # AI로 못 읽은 스캔 B/L: PC 안 OCR 글자에서 B/L 번호 후보를 넣고 '확인 필요'로 둔다
        got = bl_from_lines(ocr or ocr_text_lines(path))
        if got:
            doc.bl_no = got
            doc.sources["bl_no"] = "ocr"
            doc.warnings.append(OCR_BL_WARNING)
    if doc_type in ("CI", "PL") and not doc.lines and READ_FAIL_WARNING not in doc.warnings:
        doc.warnings.append(READ_FAIL_WARNING)
    for k in NEEDED_HEAD.get(doc_type, ()):
        if not getattr(doc, k):
            doc.warnings.append(f"{FIELD_LABELS.get(k, k)} 확인 필요")
    return doc


def _sheet_kind(name: str) -> tuple[str | None, bool]:
    """시트 이름 → (CI·PL, 부분품 시트 여부). 'CI SPARE PARTS' → (CI, True), 'SPARE PARTS' → (PL, True)."""
    from app.a0_reader.classify.service import classify_by_name, norm

    n = norm(name)
    part = any(k in n for k in ("spare", "part", "부분품", "부품"))
    t = classify_by_name(f"{name}.xlsx")
    if t not in ("CI", "PL"):
        t = "PL" if part else None
    return t, part


_LINE_NUMS = ("qty_per_carton", "quantity", "cartons", "net_kg", "amount")


def _merge_part_sheet(main: ParsedDocument, extra: list) -> None:
    """부분품 시트 줄을 본품 서류에 붙인다. 부분품 시트가 본품 시트의 줄(같은 모델·같은 수량)을 다시 적은 경우
    새 줄로 붙이지 않고 본품 쪽 빈 칸만 채운다(HS 11/27: 본품이 두 번 들어가 CI 합계가 두 배로 보이던 문제)."""
    base = list(main.lines)
    used: set[int] = set()
    for ln in extra:
        key = _model_key(ln.model)
        hit = next(
            (
                i
                for i, m in enumerate(base)
                if i not in used
                and (
                    (key and _model_key(m.model) == key)
                    # 부분품 시트가 모델 칸에 본품 모델을 적은 경우: 품명·수량·카톤이 같으면 같은 줄(HS 11/27)
                    or (
                        m.is_part
                        and _model_key(m.description) != ""
                        and _model_key(m.description) == _model_key(ln.description)
                        and m.cartons == ln.cartons
                    )
                )
                and (m.quantity is None or ln.quantity is None or m.quantity == ln.quantity)
            ),
            None,
        )
        if hit is None:
            main.lines.append(ln)
            continue
        used.add(hit)
        m = base[hit]
        for f in _LINE_NUMS:
            if getattr(m, f) is None and getattr(ln, f) is not None:
                setattr(m, f, getattr(ln, f))


def extract_documents(
    path: Path,
    filename: str,
    shipper_id: str,
    folder_id: str,
    mask_names: list[str] | None = None,
) -> list[ParsedDocument]:
    """엑셀 한 파일에 CI 시트와 PL 시트가 같이 있으면 서류 종류마다 1개씩 만든다(부분품 시트는 그 종류에 합치고
    줄을 부분품으로 표시). 아니면 extract_file() 하나. 실제 샘플에서 PL 시트를 못 읽던 문제(HS 11/26)."""
    ext = path.suffix.lower()
    if ext not in (".xlsx", ".xlsm", ".xls"):
        return [extract_file(path, filename, shipper_id, folder_id, mask_names)]
    try:
        sheets = read_excel_sheets(path)
    except Exception:
        return [extract_file(path, filename, shipper_id, folder_id, mask_names)]
    kinds = [(name, grid, *_sheet_kind(name)) for name, grid in sheets]
    types = {t for _, _, t, part in kinds if t and not part}
    if not {"CI", "PL"} <= types:
        return [extract_file(path, filename, shipper_id, folder_id, mask_names)]
    mask = mask_names or []
    out: dict[str, ParsedDocument] = {}
    for name, grid, t, part in sorted(kinds, key=lambda k: k[3]):  # 본품 시트 먼저
        if t is None:
            continue
        doc = ParsedDocument(
            doc_id=uuid.uuid4().hex[:12],
            shipper_id=shipper_id,
            folder_id=folder_id,
            doc_type=t,  # type: ignore[arg-type]
            parser="excel",
        )
        doc = _extract_grid(doc, grid, "", path, f"{filename} [{name}]", mask, forced_type=t)
        if part:
            for ln in doc.lines:
                ln.is_part = True
        main = out.get(t)
        if main is None:
            out[t] = doc
            continue
        _merge_part_sheet(
            main, doc.lines
        )  # 부분품 시트 줄은 본품 서류에 합친다(총계는 본품 시트 값)
        for k, v in doc.sources.items():
            main.sources.setdefault(k, v)
    return list(out.values())
