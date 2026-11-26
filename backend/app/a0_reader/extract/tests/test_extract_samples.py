"""가상 선적서류 추출: 규칙 추출 값·출처, 빠진 칸만 OpenAI(가짜 응답)로 보충. (검역 리스트 탭 1단계)"""

import shutil
from pathlib import Path

from openpyxl import load_workbook

from app.a0_reader.extract import service
from app.a0_reader.extract.ai_read import AiDocument
from app.a0_reader.extract.service import extract_file

SAMPLES = Path(__file__).resolve().parents[5] / "samples" / "A"


def test_excel_ci_values_and_sources():
    doc = extract_file(SAMPLES / "BL-TEST-003" / "CI.xlsx", "CI.xlsx", "A", "f1")
    assert doc.doc_type == "CI" and doc.bl_no == "BLTEST003" and doc.invoice_no == "INV-A-0003"
    assert len(doc.lines) == 4 and doc.currency == "USD"
    assert doc.sources["bl_no"] == "excel" and doc.sources["lines"] == "excel"


def test_missing_field_filled_by_ai_only(tmp_path, monkeypatch):
    f = tmp_path / "CI.xlsx"
    shutil.copy(SAMPLES / "BL-TEST-003" / "CI.xlsx", f)
    wb = load_workbook(f)
    for row in wb.active.iter_rows():
        if row[0].value and str(row[0].value).startswith("B/L No"):
            row[0].value, row[1].value = None, None  # B/L 번호 줄을 지운다
    wb.save(f)
    calls: list[str] = []

    def fake(doc_type, text, mask, images=None):
        calls.append(doc_type)
        return AiDocument(bl_no="BLTEST003", invoice_no="WRONG-FROM-AI")

    monkeypatch.setattr(service, "read_with_ai", fake)
    doc = extract_file(f, "CI.xlsx", "A", "f1")
    assert calls == ["CI"]
    assert doc.bl_no == "BLTEST003" and doc.sources["bl_no"] == "llm"
    assert (
        doc.invoice_no == "INV-A-0003" and doc.sources["invoice_no"] == "excel"
    )  # 규칙 값은 덮지 않음


def test_ai_off_leaves_check_needed(tmp_path, monkeypatch):
    f = tmp_path / "PL.xlsx"
    shutil.copy(SAMPLES / "BL-TEST-003" / "PL.xlsx", f)
    wb = load_workbook(f)
    for row in wb.active.iter_rows():
        if row[0].value and str(row[0].value).startswith("B/L No"):
            row[0].value, row[1].value = None, None
    wb.save(f)
    monkeypatch.setattr(service, "read_with_ai", lambda *a, **k: None)
    doc = extract_file(f, "PL.xlsx", "A", "f1")
    assert doc.bl_no == "" and "B/L 번호 확인 필요" in doc.warnings
