"""a3 판단 공개 함수(다른 영역은 이것만 부른다). DB·외부 API에서 판단 자료를 모은다. 담당: LSY

판단 함수(judge_row 등)는 JudgeContext만 받는 순수 함수이고, 여기서 자료를 준비한다.
"""

from datetime import date

from app.a2_registry.products.service import products_for
from app.a2_registry.records.service import valid_records
from app.a3_judge.factory.candidates import lookup
from app.a3_judge.material.codes import load_aliases, load_known_names
from app.a3_judge.pipeline.context import JudgeContext
from app.a3_judge.pipeline.judge_batch import judge_rows as _judge_rows
from app.a3_judge.pipeline.judge_row import judge_row_detail
from app.a4_settings.engine.service import get_rules
from app.core.config import get_settings
from app.core.schema.document import ParsedDocument
from app.core.schema.history import HistoryRow
from app.core.schema.shipper import ShipperSettings
from app.core.storage import work_db


def build_context(
    shipper_id: str,
    history: list[HistoryRow],
    targets: list[HistoryRow],
    today: date | None = None,
    settings: ShipperSettings | None = None,
    extra_docs: list[ParsedDocument] | None = None,
) -> JudgeContext:
    s = get_settings()
    latest: dict[str, dict] = {}
    for p in products_for(shipper_id):
        m = (p.get("model") or "").upper()
        if m and (
            m not in latest
            or (p.get("receipt_date") or "") >= (latest[m].get("receipt_date") or "")
        ):
            latest[m] = p
    doc_ids = sorted({i for r in targets for i in r.source_doc_ids})
    docs = {d.doc_id: d for d in work_db.documents_by_ids(doc_ids)}
    docs.update({d.doc_id: d for d in extra_docs or []})
    return JudgeContext(
        settings=settings or get_rules(shipper_id),
        history=history,
        aliases=load_aliases(),
        known_materials=load_known_names(),
        records=valid_records(shipper_id, today),
        products=latest,
        docs=docs,
        factory_lookup=lookup,
        today=today or date.today(),
        addr_min_score=s.factory_addr_min_score,
        addr_min_gap=s.factory_addr_min_gap,
        warn_days=s.record_warn_days,
    )


def judge_rows(
    shipper_id: str,
    targets: list[HistoryRow],
    history: list[HistoryRow],
    today: date | None = None,
    settings: ShipperSettings | None = None,
    extra_docs: list[ParsedDocument] | None = None,
) -> list[HistoryRow]:
    """재질·제품명·제조사·실적을 채운 새 행 목록(저장은 호출한 쪽). extra_docs = 저장 안 한 서류(시험 실행)."""
    ctx = build_context(shipper_id, history, targets, today, settings, extra_docs)
    return _judge_rows(targets, ctx)


def judge_detail(row: HistoryRow, history: list[HistoryRow]) -> dict:
    """화면 팝오버용: 한 행의 근거와 후보(저장하지 않는다)."""
    ctx = build_context(row.shipper_id, history, [row])
    _, detail = judge_row_detail(row, ctx)
    return detail
