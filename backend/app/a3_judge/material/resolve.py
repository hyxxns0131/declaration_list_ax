"""재질 판단: ① 이력 → ② 이전 수입신고서 → ③ 시험성적서 → ④ 현품사진·라벨. 담당: LSY [재사용] A3-1

- 순서는 화주 설정 material_source_order(기본 HISTORY·IMPORT_DECL·TEST_REPORT·PHOTO, RULES 11-4).
- 첫 근거로 값을 정하고, 다른 근거가 다른 재질을 말하면 후보로 함께 보여 주고 '확인 필요'(DESIGN 1장 7번).
- ④ 사진·라벨은 단독 확정 금지. 모두 없으면 "현품사진·한글표시 자료 추가 필요 ({모델})"(RULES 11-2).
"""

from pydantic import BaseModel
from pydantic import Field as PField

from app.a3_judge.material.codes import normalize
from app.a3_judge.material.sources.from_history import from_history
from app.a3_judge.material.sources.from_import_decl import from_import_decl
from app.a3_judge.material.sources.from_label_photo import from_label_photo
from app.a3_judge.material.sources.from_test_report import from_test_report
from app.core.schema.document import ParsedDocument
from app.core.schema.fields import Evidence, Flag
from app.core.schema.history import HistoryRow
from app.core.schema.record import Record

MISSING_TEXT = "현품사진·한글표시 자료 추가 필요 ({model})"
DEFAULT_ORDER = ["HISTORY", "IMPORT_DECL", "TEST_REPORT", "PHOTO"]


class MaterialResult(BaseModel):
    value: str | None
    evidence: list[Evidence] = PField(default_factory=list)
    flag: Flag = "ok"
    memo: str = ""
    candidates: list[str] = PField(default_factory=list)  # 다른 근거가 말한 재질(담당자가 고른다)


def resolve_material(
    model: str,
    past: HistoryRow | None,
    aliases: dict[str, str],
    product: dict | None = None,
    records: list[Record] | None = None,
    docs: list[ParsedDocument] | None = None,
    order: list[str] | None = None,
    known: set[str] | frozenset[str] | None = None,
) -> MaterialResult:
    found: list[tuple[str, Evidence]] = []
    photo: Evidence | None = None
    for src in order or DEFAULT_ORDER:
        if src == "HISTORY":
            hit = from_history(past)
        elif src == "IMPORT_DECL":
            hit = from_import_decl(product)
        elif src == "TEST_REPORT":
            hit = from_test_report(model, records or [])
        else:
            photo = from_label_photo(docs or [])
            hit = None
        if hit:
            found.append(hit)

    if not found:
        evs = [
            Evidence(
                source="RULE", ref="material_source_order", note="이력·신고서·성적서 근거 없음"
            )
        ]
        if photo:
            return MaterialResult(
                value=None,
                evidence=[photo, *evs],
                flag="need_check",
                memo="확인 필요: 라벨로 재질 선택",
            )
        return MaterialResult(
            value=MISSING_TEXT.format(model=model or "모델 미상"), evidence=evs, flag="need_input"
        )

    norm = [(normalize(raw, aliases, set(known) if known else None), ev) for raw, ev in found]
    (value, uncertain), _ = norm[0]
    evidence = [ev for _, ev in norm]
    others = []
    for (v, _), _ev in norm[1:]:
        if v != value and v not in others:
            others.append(v)
    flag: Flag = "ok"
    memo = ""
    if uncertain:
        flag, memo = "need_check", "재질 코드명 확인 필요"
    if others:
        flag = "need_check"
        memo = (memo + " / " if memo else "") + "근거마다 재질이 다름: 후보에서 고르세요"
    if photo:
        evidence.append(photo)
    return MaterialResult(
        value=value, evidence=evidence, flag=flag, memo=memo, candidates=[value, *others]
    )
