"""서류 대조: CI·PL·B/L의 카톤 수·금액·포장 수·중량·번호. 순수 함수. 담당: KHS [개선] A1-3 (기존 ci_check, doc_check)

- 서류끼리 값이 다르면 그 항목 different=True → 시트 칸 flag='mismatch'(빨강) + 검수 패널.
- 시트(사람 값)와 서류가 다른 것은 주황(edited)으로 따로 표시한다(빨강 아님, DESIGN 1장 5번).
- 서류가 없는 칸은 None("자료 없음").
- 유니패스 반입신고 수량 ↔ B/L 총 포장 수. CI·PL 순중량은 반입과 대조하지 않는다(RULES 11-3).

검역 리스트 탭 2단계(HS 요청 11/26, PM 결정: 서류 대조에 OpenAI 분석 사용 — AGENTS 7-5의 예외):
- 코드 대조(code_different) + OpenAI 분석(ai, crosscheck/ai_check.py) → 하나라도 다르면 '불일치'(보수적).
- 불일치 칸은 완성된 검역 리스트에 값을 넣지 않는다(ai_value 비움 + flag=mismatch, '불일치 · 검수 필요').
  선적 건 조회에는 표시 칸과 독립된 shipment_bl을 쓴다.
- 담당자가 고른 값(final_value)이 있으면 그 항목은 '해결됨'. 재실행은 final_value를 덮지 않는다.
"""

import re

from app.a1_history.rows.build import UNIPASS_VESSEL
from app.core.schema.document import DocumentLine, ParsedDocument
from app.core.schema.fields import Field
from app.core.schema.history import (
    C_BL,
    C_CARTONS,
    C_CURRENCY,
    C_MAKER,
    C_MATERIAL,
    C_MODEL,
    C_NAME_KO,
    C_NET,
    C_PRICE,
    C_QTY,
    C_RECORD,
    C_SPEC,
    C_VESSEL,
    HistoryRow,
)

DOC_COLS = ("CI", "PL", "BL")
UNIPASS = "UNIPASS"  # 서류 밖 값: 유니패스 모선명(모선 항목에만)
PICK_COLS = (*DOC_COLS, UNIPASS)  # 담당자가 고를 수 있는 값의 출처
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
        if ln.model.upper() == row.source_models.get(doc.doc_type, row.model).upper()
        and ln.is_part == row.is_part
    ]


def _sum(lines: list[DocumentLine], name: str) -> float | None:
    vals = [getattr(ln, name) for ln in lines if getattr(ln, name) is not None]
    return round(sum(vals), 3) if vals and len(vals) == len(lines) else None


def _pcs(lines: list[DocumentLine]) -> float | None:
    """줄들의 전체 개수 합. 한 줄이라도 모르면 None(자료 없음)."""
    vals = [ln.pcs() for ln in lines]
    if not vals or any(v is None for v in vals):
        return None
    return round(sum(v for v in vals if v is not None), 3)


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


def vessel_name(v: object) -> str:
    """모선명에서 배 이름만: '/' 뒤 항차·'V.' 항차·끝의 항차 번호(2612N, 101E)를 뺀다. 공백·기호 무시."""
    t = str(v or "").upper().split("/")[0]
    t = re.sub(r"\bV(OY)?\.?\s*\d+\w*", " ", t)
    t = re.sub(r"\b\d{2,4}[A-Z]?\b", " ", t)
    return re.sub(r"[^0-9A-Z가-힣]", "", t)


def unipass_vessel(row: HistoryRow) -> str | None:
    """행 모선 칸 근거에 남은 유니패스 모선명(칸 값이 막혀 비어도 남아 있다)."""
    cell = row.cells.get(C_VESSEL)
    for e in cell.evidence if cell else []:
        if e.source == "UNIPASS" and e.note.startswith(UNIPASS_VESSEL):
            return e.note[len(UNIPASS_VESSEL) :].strip() or None
    return None


def vessel_item(ci: object, pl: object, bl: object, up: str | None, sheet: object) -> dict:
    """모선(HS 결정 11/27, 기존 도구 merger.check_against_unipass 11/11 실무 확인과 같음):
    - 유니패스 모선이 있으면 그 값을 쓴다. 서류(B/L 등)와 배 이름이 달라도(환적 등) 막지 않고 '참고'로만 보인다.
    - 유니패스 값이 없으면(키 없음·조회 실패) 서류끼리 대조한다. 서류끼리 다르면 불일치 → 담당자가 고른다."""
    it = item("모선", ci, pl, bl, sheet, C_VESSEL)
    docs = [str(v) for v in (ci, pl, bl) if v not in (None, "")]
    if up:
        it[UNIPASS] = up
        ref = any(vessel_name(d) != vessel_name(up) for d in docs)
        it["code_different"] = it["different"] = False
        it["status"] = STATUS_REF if ref else STATUS_OK
        return it
    keys = {re.sub(r"\s+", "", d.upper()) for d in docs}
    diff = len(keys) > 1
    it["code_different"] = it["different"] = diff
    it["status"] = "불일치" if diff else "일치"
    return it


def item(name: str, ci: object, pl: object, bl: object, sheet: object, cell: str = "") -> dict:
    diff = _different([ci, pl, bl])
    return {
        "item": name,
        "CI": ci,
        "PL": pl,
        "BL": bl,
        "sheet": sheet,
        "cell": cell,  # 빨강을 칠할 시트 칸(없으면 B/L 단위 항목)
        "code_different": diff,  # 코드 대조 결과
        "ai": None,  # OpenAI 분석(ai_check.analyze). None = 분석 안 함(꺼짐·키 없음)
        "different": diff,  # 최종: 코드와 AI 중 하나라도 다르면 True
        "status": "불일치" if diff else "일치",  # 일치 / 불일치 / 해결됨
    }


STATUS_OK, STATUS_BAD, STATUS_DONE = "일치", "불일치", "해결됨"
# 대조할 값이 서류에 없음: 막지 않고 '비어 있음'만 보인다(CI 금액 TOTAL, HS 11/26)
STATUS_EMPTY = "비어 있음"
# 다른 값이 있지만 기준 값(유니패스 모선)을 쓰므로 막지 않고 알려만 준다(HS 결정 11/27)
STATUS_REF = "참고"
CI_TOTAL_ITEM = "CI 금액 TOTAL (시트 칸 = 줄 합)"


def merge_ai(items: list[dict], ai: dict[str, dict] | None) -> None:
    """AI 판단을 항목에 붙이고 최종 판정(코드 OR AI)을 정한다. ai = {item 이름: {same, what, ...}}."""
    for it in items:
        a = (ai or {}).get(it["item"])
        it["ai"] = a
        if it.get("status") == STATUS_EMPTY:  # 대조할 값이 없으면 AI 판단도 붙이지 않는다
            it["ai"] = None
            continue
        if it.get(UNIPASS):  # 유니패스 기준 값이 있는 항목은 AI가 다르다 해도 막지 않는다(참고만)
            continue
        ai_diff = bool(a) and a.get("same") is False
        it["different"] = bool(it["code_different"] or ai_diff)
        it["status"] = STATUS_BAD if it["different"] else STATUS_OK


def mark_resolved(row: HistoryRow, items: list[dict], previous: list[dict] | None = None) -> None:
    """칸에 담당자 값(final_value)이 있는 불일치는 '해결됨'. 칸이 없는 항목(합계·번호)은 서류 값이 그대로면
    지난번 담당자 선택(chosen)을 이어받아 '해결됨'으로 둔다(재실행이 사람 결정을 지우지 않게)."""
    prev = {p["item"]: p for p in previous or []}
    for it in items:
        p = prev.get(it["item"])
        if p and p.get("chosen") and all(p.get(d) == it.get(d) for d in PICK_COLS):
            it["chosen"] = p["chosen"]
        cell = row.cells.get(it.get("cell") or "")
        if not it["different"]:
            continue
        if (cell is not None and cell.final_value is not None) or (
            cell is None and it.get("chosen")
        ):
            it["status"] = STATUS_DONE


def crosscheck_row(
    row: HistoryRow, docs: list[ParsedDocument], bl_rows: list[HistoryRow]
) -> list[dict]:
    ci, pl, bl = (_first(docs, t) for t in DOC_COLS)
    ci_l, pl_l, bl_l = (_lines_for(row, doc) for doc in (ci, pl, bl))
    # B/L에도 한 품목만 있고 CI·PL 쪽도 한 품목일 때에는 모델 철자 자체를 비교한다.
    if bl and len(bl.lines) == 1 and len(bl_rows) == 1 and not row.part_lines:
        bl_l = bl.lines
    cur = (ci.currency if ci else "") or ""
    model_item = item(
        "모델",
        ci_l[0].model if ci_l else None,
        pl_l[0].model if pl_l else None,
        bl_l[0].model if bl_l else None,
        row.model or None,
        C_MODEL,
    )
    if (
        ci
        and pl
        and not row.part_lines
        and bool(ci_l) != bool(pl_l)
        and any(ln.model for ln in ci.lines)
        and any(ln.model for ln in pl.lines)
    ):
        # 품목표가 양쪽에 있는데 모델이 한쪽에서만 발견됨. 짝을 임의로 정하지 않는다.
        model_item.update(code_different=True, different=True, status=STATUS_BAD)
    out = [
        model_item,
        item(
            "제조사",
            *((doc.manufacturer_name or None) if doc else None for doc in (ci, pl, bl)),
            row.val(C_MAKER),
            C_MAKER,
        ),
        vessel_item(
            (ci.vessel or None) if ci else None,
            (pl.vessel or None) if pl else None,
            (bl.vessel or None) if bl else None,
            unipass_vessel(row),
            row.text(C_VESSEL) or None,
        ),
        item(
            "카톤 수",
            _sum(ci_l, "cartons"),
            _sum(pl_l, "cartons"),
            _sum(bl_l, "cartons"),
            _num(row.val(C_CARTONS)),
            C_CARTONS,
        ),
        item(
            "입수",  # 전체 개수(PCS 합계)로 비교(HS 결정 11/26)
            _pcs(ci_l),
            _pcs(pl_l),
            _pcs(bl_l),
            _num(row.val(C_QTY)),
            C_QTY,
        ),
        item(
            "순중량",
            _sum(ci_l, "net_kg"),
            _sum(pl_l, "net_kg"),
            _sum(bl_l, "net_kg"),
            _num(row.val(C_NET)),
            C_NET,
        ),
        item(
            f"금액({cur})" if cur else "금액",
            _sum(ci_l, "amount"),
            _sum(pl_l, "amount"),
            _sum(bl_l, "amount"),
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
            ci.total_gross_kg if ci else None,
            pl.total_gross_kg if pl else None,
            bl.total_gross_kg if bl else None,
            None,
        )
    )
    if ci:
        # 시트에 대응 칸이 없어 비고 경고로만 보인다. TOTAL이나 줄 금액이 없으면 '비어 있음'(HS 11/26)
        line_sum = _sum(ci.lines, "amount")
        it = item(CI_TOTAL_ITEM, ci.total_amount, None, None, line_sum)
        if ci.total_amount is None or line_sum is None:
            it["code_different"] = it["different"] = False
            it["status"] = STATUS_EMPTY
        else:
            diff = abs(ci.total_amount - line_sum) > TOLERANCE
            it["code_different"] = it["different"] = diff
            it["status"] = STATUS_BAD if diff else STATUS_OK
        out.append(it)
    out.append(
        item(
            "B/L 번호",
            (ci.bl_no or None) if ci else None,
            (pl.bl_no or None) if pl else None,
            (bl.bl_no or None) if bl else None,
            row.text(C_BL) or None,
            C_BL,
        )
    )
    if ci and pl and ci.invoice_no and pl.invoice_no:
        out.append(item("인보이스 번호", ci.invoice_no, pl.invoice_no, None, None))
    if ci and pl and ci.doc_date and pl.doc_date:
        out.append(item("서류 날짜", ci.doc_date, pl.doc_date, None, None))
    if ci and ci.currency:
        out.append(
            item(
                "통화",
                ci.currency,
                (pl.currency or None) if pl else None,
                (bl.currency or None) if bl else None,
                row.val(C_CURRENCY),
                C_CURRENCY,
            )
        )
    return out


def _agreed(it: dict) -> object:
    if it.get(UNIPASS):  # 기준 값(유니패스)이 있으면 그 값
        return it[UNIPASS]
    return next((it[d] for d in DOC_COLS if it[d] not in (None, "")), None)


def apply_flags(row: HistoryRow, items: list[dict]) -> None:
    """불일치 항목의 칸은 값을 막는다(ai_value 비움 + flag=mismatch, '불일치 · 검수 필요').
    담당자 값(final_value)이 있는 칸·다른 경고가 있는 칸은 그대로. 다시 일치하면 서류 값으로 되돌린다."""
    for it in items:
        col = it.get("cell")
        if not col:
            continue
        cell = row.cells.setdefault(col, Field())
        if cell.final_value is not None:
            continue
        if it["different"]:
            cell.ai_value = None
            if col == C_MODEL:
                if not row.source_models:
                    row.source_models = {d: str(it[d]) for d in DOC_COLS if it.get(d)}
                row.model = ""
                for dep in (C_NAME_KO, C_MATERIAL, C_SPEC, C_RECORD):
                    if dep not in row.cells or row.cells[dep].final_value is None:
                        row.set_ai(
                            dep, None, flag="need_check", memo="모델 확정 후 등록 정보 재확인"
                        )
            if col == C_MAKER and row.val(C_RECORD) and row.cells[C_RECORD].final_value is None:
                row.set_ai(C_RECORD, None, flag="need_check", memo="제조사 확정 후 실적 재확인")
            cell.flag = "mismatch"
            who = (it.get("ai") or {}).get("what") or ""
            vals = ", ".join(
                f"{'유니패스' if d == UNIPASS else d} {it[d]}"
                for d in PICK_COLS
                if it.get(d) not in (None, "")
            )
            cell.memo = f"불일치 · 검수 필요: {it['item']} ({vals}){' — ' + who if who else ''}"
        elif not it["different"] and cell.flag == "mismatch":
            if cell.ai_value in (None, "") and _agreed(it) is not None:
                cell.ai_value = _agreed(it)
            cell.flag, cell.memo = "ok", ""
            if col == C_MODEL:
                row.model = str(cell.value or "")
    bl_level = [
        it["item"]
        for it in items
        if not it.get("cell") and it["different"] and it.get("status") != STATUS_DONE
    ]
    empty = [it["item"] for it in items if it.get("status") == STATUS_EMPTY]
    parts = ([f"{', '.join(bl_level)} 서류끼리 다름"] if bl_level else []) + (
        [f"{', '.join(empty)} 비어 있음"] if empty else []
    )
    row.set_note("서류 대조", " · ".join(parts) if parts else None)
    # 참고(막지 않음): 모선은 유니패스 값을 쓰고, 서류 모선과 다르면 비고에 알려만 준다(HS 결정 11/27)
    refs = [
        f"{it['item']}: 유니패스 값 사용, 서류 "
        + ", ".join(f"{d} {it[d]}" for d in DOC_COLS if it.get(d) not in (None, ""))
        for it in items
        if it.get("status") == STATUS_REF
    ]
    row.set_note("참고", " · ".join(refs) if refs else None)


def arrival_check(row: HistoryRow, bl: ParsedDocument | None, arrival_packages: str) -> None:
    """반입신고 수량 ↔ B/L 총 포장 수(RULES 11-3)."""
    got = _num(arrival_packages)
    if bl is None or bl.total_cartons is None or got is None:
        row.set_note("반입 수량", None)
        return
    row.set_note("반입 수량", None if abs(got - bl.total_cartons) < TOLERANCE else "B/L과 다름")
