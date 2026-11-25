"""엑셀(xlsx·xls) → 칸 격자(행 목록). 담당: KHS [개선] A0-1 (기존 document_loader.py)"""

from pathlib import Path

Grid = list[list[object]]


def _trim(rows: Grid) -> Grid:
    out = []
    for r in rows:
        r = list(r)
        while r and (r[-1] is None or str(r[-1]).strip() == ""):
            r.pop()
        out.append(r)
    return out


def read_excel(path: Path) -> Grid:
    """첫 번째로 내용이 있는 시트의 모든 행. 수식은 계산된 값으로 읽는다."""
    if path.suffix.lower() == ".xls":
        import xlrd

        book = xlrd.open_workbook(str(path))
        for sheet in book.sheets():
            rows = [sheet.row_values(i) for i in range(sheet.nrows)]
            if any(any(str(c).strip() for c in r) for r in rows):
                return _trim(rows)
        return []

    from openpyxl import load_workbook

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            if any(any(c is not None and str(c).strip() for c in r) for r in rows):
                return _trim(rows)
        return []
    finally:
        wb.close()
