"""판단에 필요한 자료 묶음. 판단 함수는 이것만 받는다(DB·네트워크는 service가 미리 준비). 담당: LSY"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from app.core.schema.document import ParsedDocument
from app.core.schema.history import HistoryRow
from app.core.schema.record import Record
from app.core.schema.shipper import ShipperSettings

FactoryLookup = Callable[[str], tuple[list[dict] | None, str]]


def _no_lookup(_: str) -> tuple[list[dict] | None, str]:
    return None, "off"


@dataclass
class JudgeContext:
    settings: ShipperSettings
    history: list[HistoryRow]
    aliases: dict[str, str] = field(default_factory=dict)
    known_materials: frozenset[str] = frozenset()
    records: list[Record] = field(default_factory=list)
    products: dict[str, dict] = field(default_factory=dict)  # 모델(대문자) → 최근 수입신고서
    docs: dict[str, ParsedDocument] = field(default_factory=dict)  # doc_id → 서류
    factory_lookup: FactoryLookup = _no_lookup
    today: date = field(default_factory=date.today)
    addr_min_score: float = 0.45
    addr_min_gap: float = 0.10
    warn_days: int = 90

    def docs_for(self, row: HistoryRow) -> list[ParsedDocument]:
        return [self.docs[i] for i in row.source_doc_ids if i in self.docs]

    def rule(self, key: str, fallback: object = None) -> object:
        return getattr(self.settings, key, fallback)
