"""서류(ParsedDocument[]) → 검역이력 행. 같은 B/L 재업로드는 기존 행에 합친다. 순수 함수. 담당: KHS [개선] A1-1

RULES 11-2:
- 같은 행 판정: 모델 코드가 같고 완제품/부분품 구분이 같으면 같은 행. 모델이 다르면 B/L·부분품 여부·입수·카톤 수가 같을 때
- 재업로드: 사람이 고친 칸(final_value)은 덮어쓰지 않는다. 서류 값이 바뀐 칸은 이전 값을 메모에 남긴다
- 가격(수출국) = CI 금액 그대로. 가격(USD)은 계산 칸(관세환율, A1-7)
"""

import uuid

from app.a1_history.missing.service import MARK_COLUMNS, apply_missing, is_mark
from app.a3_judge.spare_parts.merge import merge_spare_lines
from app.core.schema.document import DocumentLine, ParsedDocument
from app.core.schema.fields import Evidence, Field
from app.core.schema.history import (
    C_BL,
    C_CARGO,
    C_CARTONS,
    C_CURRENCY,
    C_MAKER,
    C_NAME_EN,
    C_NET,
    C_PRICE,
    C_PRICE_USD,
    C_QTY,
    C_VESSEL,
    COLOR_COLUMN,
    OUTER_COLOR_COLUMN,
    HistoryRow,
)
from app.core.schema.shipper import ShipperSettings
from app.core.unipass.client import CargoInfo

# 모선 칸 근거 note 머리말. 서류 대조(crosscheck)가 읽어 유니패스 모선과 서류 모선을 비교한다(HS 결정 11/26)
UNIPASS_VESSEL = "유니패스 모선명: "


def _first(docs: list[ParsedDocument], doc_type: str) -> ParsedDocument | None:
    return next((d for d in docs if d.doc_type == doc_type), None)


def _ev(doc: ParsedDocument | None, note: str = "") -> list[Evidence]:
    if not doc:
        return []
    return [Evidence(source=doc.doc_type, ref=doc.doc_id, note=note)]  # type: ignore[arg-type]


def find_bl(docs: list[ParsedDocument]) -> str:
    """B/L 번호: B/L 서류 → 다른 서류 순서(RULES 11-1)."""
    for t in ("BL", "CI", "PL", "CO"):
        for d in docs:
            if d.doc_type == t and d.bl_no:
                return d.bl_no
    return ""


class _Line:
    """CI 줄 + 같은 모델의 PL 줄."""

    def __init__(self, ci: DocumentLine | None, pl: DocumentLine | None) -> None:
        self.ci, self.pl = ci, pl

    def pick(self, name: str) -> tuple[object, str]:
        for src, line in (("PL", self.pl), ("CI", self.ci)):
            v = getattr(line, name) if line else None
            if v not in (None, ""):
                return v, src
        return None, ""

    def merged(self) -> DocumentLine:
        base = self.ci or self.pl or DocumentLine()
        return DocumentLine(
            model=base.model,
            description=(self.ci.description if self.ci else "") or base.description,
            qty_per_carton=self.pick("qty_per_carton")[0],  # type: ignore[arg-type]
            quantity=self.pick("quantity")[0],  # type: ignore[arg-type]
            cartons=self.pick("cartons")[0],  # type: ignore[arg-type]
            net_kg=self.pick("net_kg")[0],  # type: ignore[arg-type]
            amount=self.ci.amount if self.ci else None,
            is_part=base.is_part,
            color=(self.ci.color if self.ci else "") or (self.pl.color if self.pl else ""),
            outer_color=(self.ci.outer_color if self.ci else "")
            or (self.pl.outer_color if self.pl else ""),
        )


def pair_lines(ci: ParsedDocument | None, pl: ParsedDocument | None) -> list[_Line]:
    pl_lines = list(pl.lines) if pl else []
    out: list[_Line] = []
    for c in ci.lines if ci else []:
        hit = next(
            (p for p in pl_lines if p.model.upper() == c.model.upper() and p.is_part == c.is_part),
            None,
        )
        if hit:
            pl_lines.remove(hit)
        out.append(_Line(c, hit))
    if not ci:
        out.extend(_Line(None, p) for p in pl_lines)
    return out


def build_rows(
    shipper_id: str,
    docs: list[ParsedDocument],
    settings: ShipperSettings,
    cargo: CargoInfo | None,
) -> list[HistoryRow]:
    ci, pl, bl, co = (_first(docs, t) for t in ("CI", "PL", "BL", "CO"))
    present = {d.doc_type for d in docs}
    bl_no = find_bl(docs)
    pairs = pair_lines(ci, pl)
    lines = [p.merged() for p in pairs]
    src_of = {id(m): p for m, p in zip(lines, pairs, strict=True)}

    merged_parts = None
    if getattr(settings, "merge_spare_parts", False):
        pair_parts = [ln for ln in lines if ln.is_part]
        lines, merged_parts = merge_spare_lines(lines)
        if merged_parts:
            # 합친 부분품 행의 입수 = 부분품 줄 전체 개수의 합(HS 결정 11/26).
            # merge.py(LSY)는 입수를 비워 두므로 여기서 채운다 — LSY 변경 요청
            part_pcs = [ln.pcs() for ln in pair_parts]
            if part_pcs and all(v is not None for v in part_pcs):
                merged_parts.line.quantity = round(sum(v for v in part_pcs if v is not None), 4)
            lines = [*lines, merged_parts.line]
    if not lines:
        lines = [DocumentLine()]  # 서류에 품목이 없어도 B/L 행 1개는 만든다

    rows: list[HistoryRow] = []
    for line in lines:
        row = HistoryRow(
            row_id=uuid.uuid4().hex[:12],
            shipper_id=shipper_id,
            model=line.model,
            is_part=line.is_part,
            source_doc_ids=[d.doc_id for d in docs],
        )
        if bl_no:
            row.set_ai(C_BL, bl_no, _ev(bl or ci, "B/L 번호"))
        else:
            row.set_ai(C_BL, None, flag="need_check", memo="B/L 번호 확인 필요")
        if bl and bl.doc_date:
            row.set_ai("선적일", bl.doc_date, _ev(bl, "선적일(on board)"))

        if cargo:
            up = [Evidence(source="UNIPASS", ref=cargo.bl_no, note="유니패스 화물진행정보")]
            # 모선명: 유니패스 값을 근거에 따로 남긴다 → 서류 모선과 대조(HS 결정 11/26 "둘이 비교해서 다르면 알려주게")
            v_ev = up + (
                [Evidence(source="UNIPASS", ref=cargo.bl_no, note=UNIPASS_VESSEL + cargo.vessel)]
                if cargo.vessel
                else []
            )
            row.set_ai(C_VESSEL, cargo.vessel or (bl.vessel if bl else "") or None, v_ev)
            for col, v in (
                ("반입지 코드", cargo.arrival_place_code),
                ("반입일", cargo.arrival_date),
                ("입항일", cargo.entry_date),
                ("도착항 코드", cargo.port_of_arrival),
                ("선적항 코드", cargo.port_of_loading),
                (C_CARGO, cargo.cargo_no),
            ):
                row.set_ai(col, v or None, up if v else [])
        else:
            vdoc = bl if bl and bl.vessel else ci
            vessel = (vdoc.vessel if vdoc else "") or None
            if vessel:
                row.set_ai(C_VESSEL, vessel, _ev(vdoc, "서류 모선명"))
            else:
                row.set_ai(
                    C_VESSEL, None, flag="need_check", memo="모선명 확인 필요 (서류에서 못 찾음)"
                )

        if co and co.manufacturer_name:
            row.set_ai(C_MAKER, co.manufacturer_name, _ev(co, "C/O 생산자"))

        pair = src_of.get(id(line))
        for col, name in ((C_CARTONS, "cartons"), (C_NET, "net_kg")):
            v = getattr(line, name)
            src = pair.pick(name)[1] if pair else "CI"
            doc = pl if src == "PL" else ci
            row.set_ai(col, v, _ev(doc) if v is not None else [])
        # 입수 = 전체 개수(PCS 합계)(HS 결정 11/26). 카톤당 수량은 근거 메모에 남긴다
        pcs = line.pcs()
        qsrc = (pair.pick("quantity")[1] or pair.pick("qty_per_carton")[1]) if pair else "CI"
        qdoc = pl if qsrc == "PL" else ci
        how = "서류 수량(PCS)" if line.quantity is not None else "카톤당 수량 x 카톤 수"
        per = f" · 카톤당 {line.qty_per_carton:g}" if line.qty_per_carton is not None else ""
        note = f"입수 = 전체 개수: {how}{per}"
        row.set_ai(C_QTY, pcs, _ev(qdoc, note) if pcs is not None else [])

        currency = (ci.currency if ci else "") or ""
        row.set_ai(C_CURRENCY, currency or None, _ev(ci))
        row.set_ai(
            C_PRICE, line.amount, _ev(ci, "CI 금액(Amount)") if line.amount is not None else []
        )
        if currency == "USD" and line.amount is not None:
            row.set_ai(
                C_PRICE_USD,
                line.amount,
                [Evidence(source="FX", ref="USD", note="CI 통화가 USD라 가격(수출국) 그대로")],
            )
        elif line.amount is not None:
            row.set_ai(C_PRICE_USD, None, flag="need_check", memo="관세환율 연결 전 (A1-7)")
        if line.description:
            row.set_ai(C_NAME_EN, line.description, _ev(ci or pl, "서류 품명"))
        if line.color:
            row.set_ai(COLOR_COLUMN, line.color, _ev(ci or pl, "서류 색상"))
        if line.outer_color:
            row.set_ai(OUTER_COLOR_COLUMN, line.outer_color, _ev(ci or pl, "서류 외색"))

        if merged_parts and line is merged_parts.line:
            row.part_lines = merged_parts.part_lines
            row.set_note(
                "부분품",
                f"{len(merged_parts.part_lines)}줄 합침 — {merged_parts.note}",
            )

        apply_missing(row, present, list(settings.required_docs))
        rows.append(row)
    return rows


def _same_row(new: HistoryRow, old: HistoryRow) -> bool:
    if new.is_part != old.is_part:
        return False
    if new.model and old.model:
        return new.model.upper() == old.model.upper()
    return new.text(C_QTY) == old.text(C_QTY) and new.text(C_CARTONS) == old.text(C_CARTONS)


def merge_with_existing(
    new_rows: list[HistoryRow], existing: list[HistoryRow]
) -> tuple[list[HistoryRow], list[str], list[str]]:
    """(저장할 행, 새로 만든 row_id, 갱신한 row_id). 승인된 행은 건드리지 않는다."""
    unused = list(existing)
    out: list[HistoryRow] = []
    created: list[str] = []
    updated: list[str] = []
    for new in new_rows:
        old = next((o for o in unused if _same_row(new, o)), None)
        if old is None:
            out.append(new)
            created.append(new.row_id)
            continue
        unused.remove(old)
        if old.locked:
            continue
        row = old.model_copy(deep=True)
        row.model, row.is_part = new.model or old.model, new.is_part
        row.part_lines, row.source_doc_ids = new.part_lines, new.source_doc_ids
        for col, cell in new.cells.items():
            prev = row.cells.get(col)
            if prev is None:
                row.cells[col] = cell
                continue
            if prev.final_value is not None:
                row.set_ai(col, cell.ai_value, cell.evidence)
                continue
            changed = prev.ai_value not in (None, "") and str(prev.ai_value) != str(cell.ai_value)
            keep_memo = changed and not is_mark(prev.ai_value) and col != "비고"
            row.cells[col] = Field(
                ai_value=cell.ai_value,
                evidence=cell.evidence,
                flag=cell.flag,
                memo=f"이전 값: {prev.ai_value}" if keep_memo else cell.memo,
            )
        # 서류가 들어와 필요 없어진 "자료 추가 필요" 표시는 지운다
        for col in MARK_COLUMNS:
            prev = row.cells.get(col)
            if (
                col not in new.cells
                and prev
                and prev.final_value is None
                and is_mark(prev.ai_value)
            ):
                row.cells[col] = Field()
        out.append(row)
        updated.append(row.row_id)
    return out, created, updated
