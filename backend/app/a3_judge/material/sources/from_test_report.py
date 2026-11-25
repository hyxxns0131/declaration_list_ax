"""재질 근거 ③ 시험성적서 검체 재질. 순수 함수. 담당: LSY [재사용] A3-1

같은 모델이 실적 인정 모델로 들어 있는 실적의 검체 재질을 쓴다.
"""

from app.core.schema.fields import Evidence
from app.core.schema.record import Record


def from_test_report(model: str, records: list[Record]) -> tuple[str, Evidence] | None:
    if not model:
        return None
    hits = [
        r for r in records if model.upper() in (p.upper() for p in r.products) and r.sample_parts
    ]
    if not hits:
        return None
    rec = max(hits, key=lambda r: r.approved_on or "")
    mats = sorted({s.material for s in rec.sample_parts if s.material})
    if not mats:
        return None
    ev = Evidence(
        source="TEST_REPORT",
        ref=rec.record_no,
        note=f"시험성적서 {rec.record_no} 검체 재질 (모델 {model})",
    )
    return ", ".join(mats), ev
