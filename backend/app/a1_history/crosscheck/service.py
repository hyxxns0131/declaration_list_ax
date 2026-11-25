"""서류 대조: CI·PL·B/L의 카톤 수·금액·포장 수·중량·번호. 순수 함수. 담당: KHS [개선] A1-3 (기존 ci_check, doc_check)

- 서류끼리 값이 다르면 그 항목 different=True → 시트 칸 flag='mismatch'(빨강) + 검수 패널.
- 시트(사람 값)와 서류가 다른 것은 주황(edited)으로 따로 표시한다(빨강 아님, DESIGN 1장 5번).
- 서류가 없는 칸은 None("자료 없음").
- 유니패스 반입신고 수량 ↔ B/L 총 포장 수. CI·PL 순중량은 반입과 대조하지 않는다(RULES 11-3).
"""

from app.core.schema.document import DocumentLine, ParsedDocument
from app.core.schema.history import C_BL, C_CARTONS, C_NET, C_PRICE, C_QTY, HistoryRow

DOC_COLS = ("CI", "PL", "BL")
TOLERANCE = 0.005  # 소수 둘째 자리 반올림 차이는 같은 값


def _first(docs: list[ParsedDocument], t: str) -> ParsedDocument | None:
    return next((d for d in reversed(docs) if d.doc_type == t), None)  # 가장 최근 서류


def _lines_for(row: HistoryRow, doc: ParsedDocument | None) -> list[DocumentLine]:
    if not doc:
        return []
    if row.is_part and row.part_lines:  # 합친 부분품 행 = 부분품 줄 전부
        return [ln for ln in doc.lines if ln.is_part]
    return [
        ln
        for ln in doc.lines
        if ln.model.upper() == row.model.upper() and ln.is_part == row.is_part
    ]


def _sum(lines: list[DocumentLine], name: str) -> float | None:
    vals = [getattr(ln, name) for ln in lines if getattr(ln, name) is not None]
    return round(sum(vals), 3) if vals else None


def _num(v: object) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _different(values: list[object]) -> bool:
    nums = [v for v in values if isinstance(v, int | float)]
    texts = [str(v).strip().upper() for v in values if isinstance(v, str) and v.strip()]
    if nums and max(nums) - min(nums) > TOLERANCE:
        return True
    return len(set(texts)) > 1


def item(name: str, ci: object, pl: object, bl: object, sheet: object, cell: str = "") -> dict:
    return {
        "item": name,
        "CI": ci,
        "PL": pl,
        "BL": bl,
        "sheet": sheet,
        "cell": cell,  # 빨강을 칠할 시트 칸(없으면 B/L 단위 항목)
        "different": _different([ci, pl, bl]),
    }


def crosscheck_row(
    row: HistoryRow, docs: list[ParsedDocument], bl_rows: list[HistoryRow]
) -> list[dict]:
    ci, pl, bl = (_first(docs, t) for t in DOC_COLS)
    ci_l, pl_l = _lines_for(row, ci), _lines_for(row, pl)
    cur = (ci.currency if ci else "") or ""
    out = [
        item(
            "카톤 수",
            _sum(ci_l, "cartons"),
            _sum(pl_l, "cartons"),
            None,
            _num(row.val(C_CARTONS)),
            C_CARTONS,
        ),
        item(
            "입수",
            _sum(ci_l, "qty_per_carton"),
            _sum(pl_l, "qty_per_carton"),
            None,
            _num(row.val(C_QTY)),
            C_QTY,
        ),
        item(
            "순중량", _sum(ci_l, "net_kg"), _sum(pl_l, "net_kg"), None, _num(row.val(C_NET)), C_NET
        ),
        item(
            f"금액({cur})" if cur else "금액",
            _sum(ci_l, "amount"),
            None,
            None,
            _num(row.val(C_PRICE)),
            C_PRICE,
        ),
    ]
    sheet_total = sum(_num(r.val(C_CARTONS)) or 0 for r in bl_rows) or None
    out.append(
        item(
            "총 포장 수",
            ci.total_cartons if ci else None,
            pl.total_cartons if pl else None,
            bl.total_cartons if bl else None,
            sheet_total,
        )
    )
    out.append(
        item(
            "총중량",
            None,
            pl.total_gross_kg if pl else None,
            bl.total_gross_kg if bl else None,
            None,
        )
    )
    if ci and ci.total_amount is not None:
        line_sum = _sum(ci.lines, "amount")
        it = item("CI 금액 TOTAL (시트 칸 = 줄 합)", ci.total_amount, None, None, line_sum)
        it["different"] = line_sum is not None and abs(ci.total_amount - line_sum) > TOLERANCE
        out.append(it)
    out.append(
        item(
            "B/L 번호",
            (ci.bl_no or None) if ci else None,
            (pl.bl_no or None) if pl else None,
            (bl.bl_no or None) if bl else None,
            row.text(C_BL) or None,
        )
    )
    if ci and pl and ci.invoice_no and pl.invoice_no:
        out.append(item("인보이스 번호", ci.invoice_no, pl.invoice_no, None, None))
    return out


def apply_flags(row: HistoryRow, items: list[dict]) -> None:
    """서류끼리 다른 항목의 시트 칸을 빨강(mismatch)으로. 사람이 고친 칸·다른 경고가 있는 칸은 그대로."""
    for it in items:
        col = it.get("cell")
        cell = row.cells.get(col) if col else None
        if not cell:
            continue
        if it["different"] and cell.final_value is None and cell.flag == "ok":
            cell.flag = "mismatch"
            cell.memo = f"서류와 다름: {it['item']} (CI {it['CI']}, PL {it['PL']})"
        elif not it["different"] and cell.flag == "mismatch":
            cell.flag, cell.memo = "ok", ""
    bl_level = [it["item"] for it in items if not it.get("cell") and it["different"]]
    row.set_note("서류 대조", f"{', '.join(bl_level)} 서류끼리 다름" if bl_level else None)


def arrival_check(row: HistoryRow, bl: ParsedDocument | None, arrival_packages: str) -> None:
    """반입신고 수량 ↔ B/L 총 포장 수(RULES 11-3)."""
    got = _num(arrival_packages)
    if bl is None or bl.total_cartons is None or got is None:
        row.set_note("반입 수량", None)
        return
    row.set_note("반입 수량", None if abs(got - bl.total_cartons) < TOLERANCE else "B/L과 다름")
