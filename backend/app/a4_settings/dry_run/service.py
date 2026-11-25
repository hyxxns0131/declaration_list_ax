"""시험 실행: 저장하지 않고 설정 전/후의 행·신고건 결과를 나란히. 담당: JUJ [신규] A4-2·A4-3

서류 고르는 순서: 요청한 B/L(이미 올린 서류) → 그 화주의 최근 B/L → samples/<화주>/의 첫 가상 B/L 폴더.
결과는 신고건마다 '모델 (재질)' 목록과 바뀐 규칙. DESIGN 7장 시험 실행 결과 표.
"""

from app.a0_reader.extract.service import extract_file
from app.a1_history.rows.service import simulate
from app.a3_judge.grouping.split import group_rows
from app.a4_settings.engine.service import get_rules
from app.a4_settings.shippers.service import catalog, rule_index, validate
from app.core.config import REPO_ROOT
from app.core.errors import AppError
from app.core.schema.document import ParsedDocument
from app.core.schema.history import C_MATERIAL, C_RECORD, HistoryRow
from app.core.schema.shipper import ShipperSettings
from app.core.storage import work_db, work_db_more

SAMPLES = REPO_ROOT / "samples"


def _sample_docs(shipper_id: str) -> tuple[list[ParsedDocument], str]:
    root = SAMPLES / shipper_id
    folders = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    if not folders:
        return [], ""
    folder = folders[0]
    docs = [
        extract_file(f, f.name, shipper_id, f"dry-{folder.name}")
        for f in sorted(folder.iterdir())
        if f.is_file()
    ]
    return docs, f"samples/{shipper_id}/{folder.name}"


def pick_docs(shipper_id: str, bl_no: str | None) -> tuple[list[ParsedDocument], str]:
    if bl_no:
        docs = work_db_more.documents_for_bl(shipper_id, bl_no)
        if not docs:
            raise AppError("not_found", f"B/L {bl_no}로 올린 서류가 없습니다.", 404)
        return docs, bl_no
    rows = work_db.list_rows(shipper_id)
    for r in reversed(rows):
        bl = r.text("B/L Number")
        if bl:
            docs = work_db_more.documents_for_bl(shipper_id, bl)
            if docs:
                return docs, bl
    return _sample_docs(shipper_id)


def _label(r: HistoryRow) -> str:
    name = r.model or "모델 미상"
    if r.is_part:
        name += " 부분품"
    mat = r.text(C_MATERIAL) or "재질 미정"
    return f"{name} ({mat})"


def _summary(rows: list[HistoryRow], settings: ShipperSettings) -> list[dict]:
    decls = group_rows(rows, settings)
    by_id = {r.row_id: r for r in rows}
    return [
        {
            "declaration_id": d.declaration_id,
            "key": d.key.model_dump(),
            "rows": [_label(by_id[i]) for i in d.row_ids],
            "records": [by_id[i].text(C_RECORD) for i in d.row_ids if by_id[i].text(C_RECORD)],
            "warnings": d.warnings,
        }
        for d in decls
    ]


def changed_rules(before: ShipperSettings, after: ShipperSettings) -> list[dict]:
    idx = rule_index(catalog())
    b, a = before.model_dump(), after.model_dump()
    out = []
    for key, r in idx.items():
        if b.get(key) != a.get(key):
            out.append({"key": key, "label": r["label"], "before": b.get(key), "after": a.get(key)})
    return out


def dry_run(shipper_id: str, new_values: dict, bl_no: str | None = None) -> dict:
    before = get_rules(shipper_id)
    data = {k: v for k, v in new_values.items() if k != "group_by_maker"}
    data["shipper_id"] = shipper_id
    after = validate({**before.model_dump(), **data})
    docs, source = pick_docs(shipper_id, bl_no)
    if not docs:
        raise AppError(
            "no_documents",
            "시험할 서류가 없습니다. 서류를 먼저 올리거나 samples/에 가상 B/L을 두세요.",
            404,
        )
    rows_before = simulate(shipper_id, docs, before)
    rows_after = simulate(shipper_id, docs, after)
    return {
        "source": source,
        "before": _summary(rows_before, before),
        "after": _summary(rows_after, after),
        "changed": changed_rules(before, after),
        "row_count": {"before": len(rows_before), "after": len(rows_after)},
    }
