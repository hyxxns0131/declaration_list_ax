"""검역 리스트 탭 테스트용 가상 선적 4건을 samples/A/에 만든다(가상 자료만). 담당: KHS (검역 리스트 탭 1단계)

BL-TEST-003 정상 · BL-TEST-004 카톤·금액 틀림 · BL-TEST-005 B/L 없음 · BL-TEST-006 B/L 번호 오타(PL).
기준은 samples/A/BL-TEST-001의 양식. 다시 실행해도 같은 파일이 나온다.
실행: cd backend && .venv/Scripts/python scripts/make_list_samples.py
"""

import shutil
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2] / "samples" / "A"
BASE = ROOT / "BL-TEST-001"


def _set(path: Path, label: str, value: object) -> None:
    wb = load_workbook(path)
    ws = wb.active
    for row in ws.iter_rows():
        if row[0].value and str(row[0].value).strip().startswith(label):
            row[1].value = value
    wb.save(path)


def _set_line(path: Path, model: str, col: int, value: object) -> None:
    wb = load_workbook(path)
    ws = wb.active
    for row in ws.iter_rows():
        if row[0].value == model:
            row[col].value = value
    wb.save(path)


def make(name: str, bl: str, inv: str, files: tuple[str, ...]) -> Path:
    d = ROOT / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in files:
        shutil.copy(BASE / f, d / f)
        _set(d / f, "B/L No", bl)
        _set(d / f, "Invoice No", inv)
    return d


def main() -> None:
    make("BL-TEST-003", "BLTEST003", "INV-A-0003", ("CI.xlsx", "PL.xlsx", "BL.xlsx", "CO.xlsx"))
    d = make("BL-TEST-004", "BLTEST004", "INV-A-0004", ("CI.xlsx", "PL.xlsx", "BL.xlsx", "CO.xlsx"))
    _set_line(d / "PL.xlsx", "RC-200", 3, 9)  # 카톤: CI 8 ↔ PL 9
    _set_line(d / "CI.xlsx", "RC-100", 5, 1250)  # 금액: 줄 합 ≠ TOTAL 2510
    make("BL-TEST-005", "BLTEST005", "INV-A-0005", ("CI.xlsx", "PL.xlsx", "CO.xlsx"))
    d = make("BL-TEST-006", "BLTEST006", "INV-A-0006", ("CI.xlsx", "PL.xlsx", "BL.xlsx", "CO.xlsx"))
    _set(d / "PL.xlsx", "B/L No", "BLTEST0O6")  # 숫자 0 대신 영문 O (오타)
    print("ok")


if __name__ == "__main__":
    main()
