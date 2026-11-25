"""Evidence 만들기 공통 함수 (RULES 10장 형식). 담당: LSY"""

from app.core.schema.fields import Evidence, EvidenceSource


def ev(source: EvidenceSource, ref: str, note: str = "") -> Evidence:
    return Evidence(source=source, ref=ref, note=note)
