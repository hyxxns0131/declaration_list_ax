"""수입신고서·시험성적서 → 등록 후보 → 저장. 담당: YHS [개선] A2-1 (기존 declarations.py, test_report.py)

- 판독 JSON(기존 도구 형식, kind=수입신고서|시험성적서)은 그대로 읽는다. AI에 넘기지 않는다.
- PDF는 글자를 뽑아 core/llm.py로 판독. AI가 꺼져 있으면 후보에 "AI 판독 꺼짐 - 값 직접 입력"을 남긴다.
- 수입신고서 재질: 코드와 이름이 다른 재질을 가리키면 이름 기준 + "코드 판독 확인 필요"(RULES 11-1).
- 등록(commit):
  수입신고서 → 제품(products). 검사종류가 '정밀'이면 실적(records)도: 실적번호 = 접수번호, 승인일 = 신고수리일.
  시험성적서 → 실적의 검체(재질·부위·색상)·승인일.
  실적 재질 = 그 실적으로 승인된 재질만(RULES 11-8).
"""

import json
import re
import uuid
from pathlib import Path

from app.a2_registry.products.service import latest_for_model, save_product
from app.a2_registry.records import service as records
from app.a2_registry.upload.models import Candidate, ImportDecl, TestReport
from app.a3_judge.history_lookup.model_key import model_from_name, product_base
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.llm import call_structured
from app.core.schema.fields import Evidence
from app.core.schema.record import Record, SamplePart
from app.core.storage import work_db_more as store

PROMPT_DECL = "a2_registry/read_import_decl"
PROMPT_REPORT = "a2_registry/read_test_report"
MAX_CHARS = 20000
W_AI_OFF = "AI 판독 꺼짐 - 값을 직접 입력하세요"
W_READ_FAIL = "서류 판독 실패 - 파일 확인 필요"


def _kind_by_name(filename: str) -> str | None:
    n = re.sub(r"\s", "", filename)
    if "시험성적서" in n or "검사성적서" in n or "testreport" in n.lower():
        return "시험성적서"
    if "수입신고서" in n or "importdeclaration" in n.lower():
        return "수입신고서"
    return None


def _pdf_text(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def read_file(
    path: Path, filename: str
) -> tuple[str, ImportDecl | TestReport | None, str, list[str]]:
    """(종류, 판독 값, parser, 경고)"""
    warnings: list[str] = []
    kind = _kind_by_name(filename)
    if path.suffix.lower() == ".json":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            return kind or "수입신고서", None, "none", [W_READ_FAIL]
        kind = raw.get("kind") or kind or ("시험성적서" if "samples" in raw else "수입신고서")
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        if kind == "시험성적서":
            return kind, TestReport.model_validate(data), "json", warnings
        return "수입신고서", ImportDecl.model_validate(data), "json", warnings
    if path.suffix.lower() != ".pdf":
        return kind or "수입신고서", None, "none", [f"지원하지 않는 파일 형식: {path.suffix}"]
    try:
        text = _pdf_text(path)
    except Exception:
        return kind or "수입신고서", None, "none", [W_READ_FAIL]
    if not kind:
        kind = "시험성적서" if ("시험성적서" in text or "검사성적서" in text) else "수입신고서"
    schema = TestReport if kind == "시험성적서" else ImportDecl
    prompt = PROMPT_REPORT if kind == "시험성적서" else PROMPT_DECL
    got = call_structured(prompt, 1, {"text": text[:MAX_CHARS]}, schema)  # type: ignore[type-var]
    if got is None:
        return kind, None, "none", [W_AI_OFF if text.strip() else W_READ_FAIL]
    return kind, got, "llm", warnings


def _norm_mat(materials: list, known: set[str]) -> tuple[list[str], list[str], list[str]]:
    """(이름 목록, 코드 목록, 경고). 이름은 가나다 순."""
    names, codes, warns = [], [], []
    for m in materials:
        name = (m.name if hasattr(m, "name") else str(m)).strip()
        code = (m.code if hasattr(m, "code") else "").strip()
        if not name:
            continue
        if known and name not in known:
            warns.append(f"재질 코드명 확인 필요: {name}")
        if name not in names:
            names.append(name)
            codes.append(code)
    order = sorted(range(len(names)), key=lambda i: names[i])
    return [names[i] for i in order], [codes[i] for i in order], warns


def _date(value: str | None) -> str:
    d = records.to_date(value)
    return d.isoformat() if d else ""


def make_candidate(
    shipper_id: str,
    kind: str,
    data: ImportDecl | TestReport | None,
    filename: str,
    doc_id: str,
    parser: str,
    warnings: list[str],
    known_materials: set[str],
) -> Candidate:
    c = Candidate(
        cand_id=uuid.uuid4().hex[:10],
        kind=kind,  # type: ignore[arg-type]
        filename=filename,
        doc_id=doc_id,
        parser=parser,  # type: ignore[arg-type]
        warnings=list(warnings),
    )
    if data is None:
        c.status = {"receipt_no": "need_check", "materials": "need_check"}
        return c
    if isinstance(data, ImportDecl):
        c.receipt_no = data.receipt_no
        c.product_en = data.product_en or ""
        c.product_ko = data.product_ko or ""
        c.model = model_from_name(c.product_en) or model_from_name(c.product_ko)
        c.materials, c.material_codes, w = _norm_mat(data.materials, known_materials)
        c.warnings += w
        c.maker_code = (data.maker_code or "").upper()
        c.maker_name = data.maker_name or ""
        c.maker_address = data.maker_address or ""
        it = data.inspection_type or ""
        c.inspection_type = "정밀" if "정밀" in it else ("서류" if "서류" in it else it)
        c.applied_on = _date(data.receipt_date)
        c.approved_on = _date(data.accepted_date)
        prev = latest_for_model(shipper_id, c.model)
        if prev and prev.get("receipt_no") != c.receipt_no:
            for key, label in (("materials", "재질"), ("maker_code", "제조업소")):
                old = prev.get(key)
                new = getattr(c, key)
                if old and old != new:
                    c.status[key] = "different"
                    c.previous[key] = ", ".join(old) if isinstance(old, list) else str(old)
                    c.warnings.append(f"이전 신고({prev.get('receipt_no')})와 {label}이(가) 다름")
    else:
        c.receipt_no = data.receipt_no
        c.sample_parts = data.samples
        mats = [s.material for s in data.samples if s.material]
        c.materials, c.material_codes, w = _norm_mat(mats, known_materials)
        c.warnings += w
        c.approved_on = _date(data.approval_date)
        c.applied_on = _date(data.applied_date)
        c.maker_code = (data.maker_code or "").upper()
        c.maker_name = data.maker_name or ""
        c.inspection_type = "정밀"
        if data.models:
            c.model = data.models[0].upper()
    for key in ("receipt_no", "materials", "maker_code"):
        if not getattr(c, key):
            c.status.setdefault(key, "need_check")
        else:
            c.status.setdefault(key, "ok")
    if any(w.startswith("재질 코드명 확인 필요") for w in c.warnings):
        c.status["materials"] = "need_check"
    if not re.fullmatch(r"\d{12}", c.receipt_no or ""):
        c.status["receipt_no"] = "need_check"
    return c


def save_original(shipper_id: str, data: bytes, filename: str) -> tuple[str, Path]:
    doc_id = uuid.uuid4().hex[:12]
    folder = get_settings().data_path / "registry" / shipper_id
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[\\/:*?\"<>|]", "_", filename)
    path = folder / f"{doc_id}_{safe}"
    path.write_bytes(data)
    return doc_id, path


def create_upload(shipper_id: str, files: list[tuple[str, bytes]], known: set[str]) -> dict:
    cands: list[Candidate] = []
    for filename, data in files:
        doc_id, path = save_original(shipper_id, data, filename)
        kind, parsed, parser, warns = read_file(path, filename)
        cands.append(
            make_candidate(shipper_id, kind, parsed, filename, doc_id, parser, warns, known)
        )
    upload_id = uuid.uuid4().hex[:12]
    body = {
        "upload_id": upload_id,
        "shipper_id": shipper_id,
        "candidates": [c.model_dump() for c in cands],
    }
    store.save_upload(upload_id, shipper_id, body)
    return body


def _merge_record(rec: Record | None, c: Candidate) -> Record:
    rec = rec or Record(record_no=c.receipt_no)
    ev = Evidence(
        source="IMPORT_DECL" if c.kind == "수입신고서" else "TEST_REPORT",
        ref=c.doc_id or c.receipt_no,
        note=f"{c.kind} {c.filename}",
    )
    rec.factory_code = rec.factory_code or c.maker_code
    rec.factory_name = rec.factory_name or c.maker_name
    rec.factory_address = rec.factory_address or c.maker_address
    if c.kind == "시험성적서":
        rec.sample_parts = [
            SamplePart(material=s.material, part=s.part, color=s.color) for s in c.sample_parts
        ]
        rec.materials = rec.materials or c.materials
        rec.approved_on = c.approved_on or rec.approved_on
        rec.applied_on = c.applied_on or rec.applied_on
    else:
        rec.materials = sorted(set(rec.materials) | set(c.materials))
        rec.approved_on = rec.approved_on or c.approved_on or None
        rec.applied_on = rec.applied_on or c.applied_on or None
    if c.model and c.model not in rec.products:
        rec.products.append(c.model)
    base = product_base(c.product_ko)
    if base and base not in rec.product_names:
        rec.product_names.append(base)
    if all(e.ref != ev.ref for e in rec.evidence):
        rec.evidence.append(ev)
    if not rec.approved_on:
        rec.memo = "승인일 확인 필요(유니패스 검사검역내역 조회)"
    return rec


def commit_upload(upload_id: str, edits: list[dict]) -> dict:
    """담당자가 확인·수정한 후보를 저장. edits = 고친 후보(cand_id 기준, 빠지면 원래 값)."""
    body = store.get_upload(upload_id)
    if not body:
        raise AppError("not_found", "등록 후보가 없습니다. 다시 올려 주세요.", 404)
    shipper_id = body["shipper_id"]
    by_id = {e.get("cand_id"): e for e in edits}
    saved_products, saved_records, skipped = 0, [], []
    for raw in body["candidates"]:
        c = Candidate.model_validate({**raw, **by_id.get(raw["cand_id"], {})})
        if by_id.get(c.cand_id, {}).get("skip"):
            continue
        if not c.receipt_no:
            skipped.append(f"{c.filename}: 접수번호 없음")
            continue
        if c.kind == "수입신고서":
            save_product(
                shipper_id,
                {
                    "model": c.model,
                    "product_ko": c.product_ko,
                    "product_en": c.product_en,
                    "materials": c.materials,
                    "material_codes": c.material_codes,
                    "maker_code": c.maker_code,
                    "maker_name": c.maker_name,
                    "maker_address": c.maker_address,
                    "receipt_no": c.receipt_no,
                    "receipt_date": c.applied_on,
                    "accepted_date": c.approved_on,
                    "inspection_type": c.inspection_type,
                    "source": c.doc_id,
                },
            )
            saved_products += 1
            if c.inspection_type != "정밀":
                continue
        got = store.get_record(c.receipt_no)
        rec = _merge_record(got[0] if got else None, c)
        records.save(rec, shipper_id)
        saved_records.append(rec.record_no)
    return {
        "shipper_id": shipper_id,
        "products": saved_products,
        "records": saved_records,
        "skipped": skipped,
    }
