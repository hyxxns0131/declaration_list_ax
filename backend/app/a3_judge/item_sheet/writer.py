"""품목사항 엑셀 쓰기: templates/item_sheet.xlsx(머리글만 다시 만든 양식)에 값만 채운다. 담당: LSY [재사용] A3-5

양식 파일이 없으면 같은 머리글로 새로 만든다. 숫자 칸도 글자로 넣는다(앞자리 0 보존).
"""

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.a3_judge.item_sheet.build import HEADERS, ItemSheet
from app.core.config import REPO_ROOT

TEMPLATE = REPO_ROOT / "backend" / "templates" / "item_sheet.xlsx"


def new_template() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "품목사항"
    ws.append([h for h, _ in HEADERS])
    return wb


def write_xlsx(sheet: ItemSheet, template: Path = TEMPLATE) -> bytes:
    wb = load_workbook(template) if template.exists() else new_template()
    ws = wb.active
    for values in sheet.rows:
        ws.append(values)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
