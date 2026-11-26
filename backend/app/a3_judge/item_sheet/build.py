"""행 → 품목사항 칸. AI 없음. 순수 함수. 담당: LSY [재사용] A3-5 (기존 item_sheet.py)

RULES 11-10: 수량 = 카톤 수, 과세가격 = 가격(USD), 대표품목 = 첫 행만 Y, 화물관리번호 1·2·3(11·4·4).
괄호 안 숫자는 유니패스 양식 칸 최대 길이.
"""

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.schema.history import (
    C_ARRIVAL,
    C_BL,
    C_CARGO,
    C_CARTONS,
    C_NAME_EN,
    C_NAME_KO,
    C_NET,
    C_PRICE_USD,
    C_RECORD,
    HistoryRow,
)

# (머리글, 최대 길이) — 유니패스 지정 양식 15칸 (기존 양식 기준, 최신본 확인 필요)
HEADERS: tuple[tuple[str, int], ...] = (
    ("제품명", 100),
    ("한글명", 100),
    ("대표품목여부", 1),
    ("수량", 10),
    ("순중량", 10),
    ("과세가격", 22),
    ("화물관리번호1", 11),
    ("화물관리번호2", 4),
    ("화물관리번호3", 4),
    ("가공기간시작일", 8),
    ("가공기간종료일", 8),
    ("소비기한시작일", 8),
    ("소비기한종료일", 8),
    ("도축기간시작일", 8),
    ("도축기간종료일", 8),
)


# 담당자가 영문 제품명 뒤에 붙이는 수기 표시. 품목사항 제품명에서는 뗀다(11/25 결정, 기존 MANUAL_MARKS)
MANUAL_MARKS: tuple[str, ...] = ("정밀검사",)


def clean_name_en(name: str) -> str:
    out = (name or "").strip()
    changed = True
    while changed:
        changed = False
        for mark in MANUAL_MARKS:
            if out.endswith(mark):
                out, changed = out[: -len(mark)].rstrip(), True
    return out


class ItemSheet(BaseModel):
    rows: list[list[str]] = PField(default_factory=list)
    warnings: list[str] = PField(default_factory=list)


def _num(v: object) -> str:
    if v is None or v == "":
        return ""
    try:
        f = float(str(v).replace(",", ""))
    except ValueError:
        return str(v)
    return f"{f:g}" if f == int(f) else f"{f:.2f}".rstrip("0").rstrip(".")


def split_cargo(cargo: str) -> tuple[str, str, str]:
    c = cargo.replace("-", "").strip()
    return c[:11], c[11:15], c[15:19]


def build_item_sheet(rows: list[HistoryRow]) -> ItemSheet:
    out = ItemSheet()
    for i, r in enumerate(rows):
        label = f"{r.text(C_BL)} {r.model}".strip()
        c1, c2, c3 = split_cargo(r.text(C_CARGO))
        values = [
            clean_name_en(r.text(C_NAME_EN)),
            r.text(C_NAME_KO),
            "Y" if i == 0 else "N",
            _num(r.val(C_CARTONS)),
            _num(r.val(C_NET)),
            _num(r.val(C_PRICE_USD)),
            c1,
            c2,
            c3,
        ] + [""] * 6
        for (name, limit), v in zip(HEADERS, values, strict=True):
            if len(v) > limit:
                out.warnings.append(f"{label}: {name} {len(v)}자 (최대 {limit}자)")
        if not values[5]:
            out.warnings.append(f"{label}: 가격(USD)이 비어 있음")
        if not c1:
            out.warnings.append(f"{label}: 화물관리번호가 비어 있음")
        if not r.text(C_RECORD):
            out.warnings.append(f"{label}: 실적접수번호가 비어 있음")
        out.rows.append(values)
    if rows and not any(r.text(C_ARRIVAL) for r in rows):
        out.warnings.append("반입일이 없습니다.")
    return out
