"""한 행 판단: 이력 조회 → 제품명 → 재질 → 재질 구분 → 제조사 → 실적. 담당: LSY [재사용] A3-1·A3-2·A3-3

- final_value가 있는 칸은 프로그램 값만 바꾸고 화면 값은 그대로(HistoryRow.set_ai).
- 승인된 행은 건너뛴다.
- 판단마다 evidence를 남긴다. 근거가 없으면 비우고 '확인 필요'(AGENTS 0-5).
- judge_row_detail은 화면 팝오버(DESIGN 5장 JudgeEvidence)용 후보·근거도 돌려준다.
"""

from app.a2_registry.records.service import expires_on, is_expired, parse_record_cell, to_date
from app.a3_judge.factory.choose import choose_factory
from app.a3_judge.history_lookup.lookup import find_past
from app.a3_judge.history_lookup.model_key import join_maker, norm_company, split_maker
from app.a3_judge.material.codes import material_list
from app.a3_judge.material.resolve import DEFAULT_ORDER, resolve_material
from app.a3_judge.pipeline.context import JudgeContext
from app.a3_judge.pipeline.evidence import ev
from app.a3_judge.record_pick import no_record
from app.a3_judge.record_pick.multi_record import choose_split
from app.a3_judge.record_pick.rank import choose_record, expiry_warning
from app.a3_judge.rule_check.maker_rule import check_maker
from app.a3_judge.rule_check.material_rule import check_material
from app.a3_judge.rule_check.record_rule import check_record
from app.a3_judge.spec_class.classify import judge_spec
from app.a3_judge.spec_class.tables import RULE_KEY as RULE_KEY_SPEC
from app.core.schema.fields import Evidence
from app.core.schema.history import (
    C_BL,
    C_MAKER,
    C_MATERIAL,
    C_NAME_EN,
    C_NAME_KO,
    C_RECORD,
    C_SPEC,
    COLOR_COLUMN,
    HistoryRow,
)

TAG_RECORD = "실적"
TAG_MAKER = "제조사"
TAG_SPEC = "재질 구분"
TAG_MATERIAL_RULE = "재질 규칙"
TAG_RECORD_RULE = "실적 규칙"
TAG_MAKER_RULE = "제조사 규칙"


def _is_doc_missing_mark(row: HistoryRow, col: str) -> bool:
    cell = row.cells.get(col)
    return bool(cell and cell.flag == "need_input" and cell.final_value is None)


def _names(row: HistoryRow, past: HistoryRow | None, from_main: bool, product: dict | None) -> None:
    if _is_doc_missing_mark(row, C_NAME_KO):
        return
    if past:
        e = ev("HISTORY", past.row_id, f"이력 {past.text(C_BL)} 같은 모델 제품명")
        ko = past.text(C_NAME_KO)
        row.set_ai(C_NAME_KO, f"{ko} 부분품" if from_main and ko else ko or None, [e])
        if past.text(C_NAME_EN):
            en = past.text(C_NAME_EN)
            row.set_ai(C_NAME_EN, f"SPARE PARTS FOR {en}" if from_main else en, [e])
        return
    if product and product.get("product_ko"):
        e = ev("IMPORT_DECL", product.get("receipt_no", ""), "이전 수입신고서 한글명")
        # 합친 부분품 행은 본품 모델 신고서를 쓰므로 '부분품'을 붙인다
        merged_part = row.is_part and bool(row.part_lines)
        ko = product["product_ko"]
        row.set_ai(C_NAME_KO, f"{ko} 부분품" if merged_part else ko, [e])
        return
    if not row.text(C_NAME_KO):
        row.set_ai(C_NAME_KO, None, flag="need_check", memo="이력 없음: 한글 제품명 입력 필요")


def _doc_maker(row: HistoryRow, ctx: JudgeContext) -> tuple[str, str, str]:
    """(회사명, 주소, 서류 doc_id) — C/O 생산자 우선(RULES 11-7)."""
    docs = ctx.docs_for(row)
    for t in ("CO", "CI", "PL", "BL"):
        for d in docs:
            if d.doc_type == t and d.manufacturer_name:
                return d.manufacturer_name, d.manufacturer_address, d.doc_id
    return "", "", ""


def _maker(
    row: HistoryRow, past: HistoryRow | None, ctx: JudgeContext, product: dict | None
) -> dict:
    """제조사 칸. 돌려주는 값: 팝오버용 {"candidates": [...], "notes": [...], "address": str}"""
    detail: dict = {"candidates": [], "notes": [], "address": ""}
    cell = row.cells.get(C_MAKER)
    if cell and cell.final_value:
        detail["notes"].append("담당자가 정한 값")
        detail["address"] = _doc_maker(row, ctx)[1]
        # 담당자가 고른 코드가 규칙에 맞는지 — 값은 그대로, 비고에만(RULES 11-7·11-9)
        name, code = split_maker(row.text(C_MAKER))
        facs, _src = ctx.factory_lookup(name) if code else (None, "")
        past_codes = {
            c
            for c in (
                split_maker(past.text(C_MAKER))[1] if past else "",
                (product or {}).get("maker_code", ""),
            )
            if c
        }
        problems = check_maker(
            code,
            facs,
            detail["address"],
            past_codes,
            bool(ctx.rule("prefer_past_factory_code", False)),
            ctx.addr_min_score,
        )
        row.set_note(TAG_MAKER_RULE, " / ".join(problems) or None)
        return detail
    row.set_note(TAG_MAKER_RULE, None)  # 사람 값이 없으면 규칙 경고도 없음
    doc_name, doc_addr, doc_id = _doc_maker(row, ctx)
    detail["address"] = doc_addr
    past_val = past.text(C_MAKER) if past else ""
    past_name, past_code = split_maker(past_val)
    past_codes = {c for c in (past_code, (product or {}).get("maker_code", "")) if c}
    prefer_past = bool(ctx.rule("prefer_past_factory_code", False))

    if not doc_name:
        # C/O 없음 → 이전 신고 제조사(확인 필요)
        if past_val or (product and product.get("maker_name")):
            src_val = past_val or join_maker(product["maker_name"], product.get("maker_code", ""))  # type: ignore[index]
            src = (
                ev("HISTORY", past.row_id, "이전 신고 제조사")
                if past
                else ev(
                    "IMPORT_DECL",
                    (product or {}).get("receipt_no", ""),
                    "이전 수입신고서 해외제조업소",
                )
            )
            row.set_ai(
                C_MAKER,
                src_val,
                [src],
                flag="need_check",
                memo="확인 필요: C/O 없음, 이전 신고 제조사 사용",
            )
        else:
            row.set_ai(C_MAKER, None, flag="need_input", memo="C/O 자료 추가 필요")
        row.set_note(TAG_MAKER, None)
        return detail

    co_ev = Evidence(source="CO", ref=doc_id, note=f"C/O 생산자 {doc_name}")
    facs, src = ctx.factory_lookup(doc_name)
    if facs is None:
        # 식약처 조회 실패 → 같은 회사의 이전 신고 코드, 없으면 회사명만
        if past_code and norm_company(past_name) == norm_company(doc_name):
            row.set_ai(
                C_MAKER,
                join_maker(doc_name, past_code),
                [co_ev, ev("HISTORY", past.row_id, "같은 회사 이전 신고 공장 코드")],  # type: ignore[union-attr]
                flag="need_check",
                memo="해외제조업소 조회 실패 → 이전 신고 코드 사용, 확인 필요",
            )
        else:
            row.set_ai(
                C_MAKER,
                doc_name,
                [co_ev],
                flag="need_check",
                memo="해외제조업소 조회 실패 → 업소코드 수기 확인",
            )
        detail["notes"].append("식약처 해외제조업소 조회 실패")
        return detail

    choice = choose_factory(
        doc_name, doc_addr, facs, past_codes, prefer_past, ctx.addr_min_score, ctx.addr_min_gap
    )
    detail["candidates"] = choice.candidates
    detail["notes"] = choice.notes
    note = " / ".join(choice.notes)
    source_note = "식약처 등록 공장" if src == "mfds" else "가상 공장 목록(samples)"
    rule_ev = Evidence(source="RULE", ref="factory.choose", note=f"{source_note}: {note}")
    if choice.code:
        row.set_ai(
            C_MAKER,
            join_maker(doc_name, choice.code),
            [co_ev, rule_ev],
            flag="need_check" if choice.need_check else "ok",
            memo=note if choice.need_check else "",
        )
    else:
        row.set_ai(C_MAKER, doc_name, [co_ev, rule_ev], flag="need_check", memo=note)
    row.set_note(TAG_MAKER, None)
    return detail


def _spec(row: HistoryRow, ctx: JudgeContext | None = None) -> None:
    """재질 구분(RULES 11-5). 칸이 비면 자동 값 또는 '칸 입력 필요', 담당자가 적었으면 바꾸지 않고 모자란 입력만 비고에."""
    mats = material_list(row.text(C_MATERIAL))
    cell = row.cells.get(C_SPEC)
    table = ctx.rule(RULE_KEY_SPEC) if ctx else None
    j = judge_spec(mats, row.text(C_SPEC), table if isinstance(table, dict) else None)
    if not j.families:
        row.set_note(TAG_SPEC, None)
        return
    if j.ai_value:
        row.set_ai(C_SPEC, j.ai_value, [ev("RULE", "spec_class", j.evidence)])
        row.set_note(TAG_SPEC, None)
        return
    if not (cell and cell.value):
        row.set_ai(
            C_SPEC,
            None,
            [ev("RULE", "spec_class", j.evidence)],
            flag="need_check",
            memo="칸 입력 필요",
        )
    row.set_note(TAG_SPEC, j.note or None)


def _record_from_history(row: HistoryRow, past: HistoryRow | None, ctx: JudgeContext) -> None:
    raw = past.text(C_RECORD) if past else ""
    no, approved = parse_record_cell(raw)
    if not no:
        row.set_ai(C_RECORD, None, flag="need_check", memo="등록된 실적·이력 없음")
        row.set_note(TAG_RECORD, no_record.NO_DATA)
        return
    if approved and is_expired(approved, ctx.today):
        exp = expires_on(approved).strftime("%Y.%m.%d")
        row.set_ai(C_RECORD, None, flag="need_check", memo=f"실적 만료 ({no}, {exp})")
        row.set_note(TAG_RECORD, no_record.expired(no, exp))
        return
    e = ev("HISTORY", past.row_id, f"이력 {past.text(C_BL)} 실적 (유효)")  # type: ignore[union-attr]
    row.set_ai(C_RECORD, raw, [e])
    row.set_note(TAG_RECORD, None)


def _record(row: HistoryRow, past: HistoryRow | None, ctx: JudgeContext, address: str) -> dict:
    detail: dict = {"candidates": [], "basis_date": ctx.today.isoformat()}
    if not ctx.records:
        _record_from_history(row, past, ctx)
        return detail
    _, code = split_maker(row.text(C_MAKER))
    mats = material_list(row.text(C_MATERIAL))
    name_ko = row.text(C_NAME_KO)
    choice = choose_record(
        ctx.records,
        mats,
        code,
        address,
        name_ko,
        ctx.today,
        spec=row.text(C_SPEC),
        same_spec=bool(ctx.rule("same_record_same_spec", True)),
        color=row.text(COLOR_COLUMN),
        color_check=bool(ctx.rule("color_check", False)),
    )
    detail["candidates"] = choice.candidates
    if not choice.value and choice.precise_needed and ctx.rule("split_record_by_part", False):
        # 부품별 실적 분리(로직 점검 반영 11/25): 본체 + 뚜껑 등 부품 실적으로 재질을 모두 덮으면 그것을 쓴다
        split = choose_split(ctx.records, mats, code, address, name_ko, ctx.today)
        if split:
            split.candidates = choice.candidates
            choice = split
    if choice.value:
        rec = next(r for r in ctx.records if r.record_no == choice.record_no)
        e = Evidence(source="RULE", ref=choice.record_no, note=f"정밀검사 면제: {choice.note}")
        row.set_ai(
            C_RECORD,
            choice.value,
            [e],
            flag="need_check" if choice.need_check else "ok",
            memo=choice.note if choice.need_check else "",
        )
        warn = expiry_warning(rec, ctx.today, ctx.warn_days)
        row.set_note(TAG_RECORD, warn or None)
        return detail
    if past and not choice.precise_needed:
        _record_from_history(row, past, ctx)
        return detail
    row.set_ai(
        C_RECORD,
        None,
        [Evidence(source="RULE", ref="record_pick", note=choice.note)],
        flag="need_check",
        memo=choice.note,
    )
    row.set_note(TAG_RECORD, choice.note)
    return detail


def _edited(row: HistoryRow, col: str) -> bool:
    cell = row.cells.get(col)
    return bool(cell and cell.final_value)


def _rule_check(row: HistoryRow, ctx: JudgeContext, address: str) -> None:
    """담당자가 직접 고친 재질·실적이 규칙에 맞는지 — 값은 바꾸지 않고 비고에만 표시(RULES 11-9)."""
    mat_problems = (
        check_material(row.text(C_MATERIAL), ctx.known_materials)
        if _edited(row, C_MATERIAL)
        else []
    )
    row.set_note(TAG_MATERIAL_RULE, " / ".join(mat_problems) or None)
    rec_problems: list[str] = []
    if _edited(row, C_RECORD):
        _, code = split_maker(row.text(C_MAKER))
        rec_problems = check_record(
            row.text(C_RECORD),
            material_list(row.text(C_MATERIAL)),
            code,
            address,
            row.text(C_NAME_KO),
            ctx.records,
            ctx.today,
        )
    row.set_note(TAG_RECORD_RULE, " / ".join(rec_problems) or None)


def judge_row_detail(row: HistoryRow, ctx: JudgeContext) -> tuple[HistoryRow, dict]:
    if row.locked:
        return row, {"locked": True}
    row = row.model_copy(deep=True)

    past = find_past(ctx.history, row.model, row.is_part, row.row_id)
    from_main = False
    if row.is_part and ctx.rule("spare_same_as_model", False):
        # 부분품은 본품과 같은 재질·실적으로 신고(spare_same_as_model)
        main = find_past(ctx.history, row.model, False, row.row_id)
        if main:
            from_main = past is None
            past = past or main
    # 부분품 행: spare_same_as_model이면 본품(같은 모델) 수입신고서를 그대로 쓰고,
    # 아니면 부분품 자체 모델의 신고서만 본다(합친 부분품 행은 모델이 본품과 같아 쓰지 않음)
    spare_same = bool(ctx.rule("spare_same_as_model", False))
    use_product = bool(row.model) and (not row.is_part or spare_same or not row.part_lines)
    product = ctx.products.get(row.model.upper()) if use_product else None

    _names(row, past, from_main, product)

    order = list(ctx.rule("material_source_order", []) or []) or None  # type: ignore[call-overload]
    m = resolve_material(
        row.model,
        past,
        ctx.aliases,
        product=product,
        records=ctx.records,
        docs=ctx.docs_for(row),
        order=order,
        known=ctx.known_materials,
    )
    if from_main:
        for e in m.evidence:
            e.note += " — 부분품은 본품과 같은 재질(spare_same_as_model)"
    row.set_ai(C_MATERIAL, m.value, m.evidence, flag=m.flag, memo=m.memo)

    _spec(row, ctx)
    maker_detail = _maker(row, past, ctx, product)
    record_detail = _record(row, past, ctx, maker_detail.get("address", ""))
    _rule_check(row, ctx, maker_detail.get("address", ""))
    row.refresh_status()
    detail = {
        "material": {
            "candidates": m.candidates,
            "evidence": [e.model_dump() for e in m.evidence],
            # 실제로 쓴 근거 순서(화주 설정 material_source_order) — 화면 재질 카드 4개를 이 순서로 보인다
            "order": order or list(DEFAULT_ORDER),
        },
        "maker": maker_detail,
        "record": record_detail,
        "past_row_id": past.row_id if past else None,
    }
    return row, detail


def judge_row(row: HistoryRow, ctx: JudgeContext) -> HistoryRow:
    return judge_row_detail(row, ctx)[0]


__all__ = ["judge_row", "judge_row_detail", "to_date"]
