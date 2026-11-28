"""이전 신고 재질과 라벨(한글표시) 재질이 다를 때 경고 문구. 순수 함수. 담당: LSY [재사용] A3-1
(기존 도구 label_diff, photo_warning)

값은 바꾸지 않는다 — 비고 '⚠️ 라벨 재질:' 한 줄만(사진·라벨만으로 재질을 확정하지 않음, AGENTS 7-9).
같은 재질인지는 material/equiv.py로 본다(표기 차이·약어·코드명 세부).
- 라벨 표기가 정한 재질 중 어느 것과도 같지 않은 공식 재질 → "라벨에는 ○○ (신고 재질과 다름)"
- 라벨 표기가 어떤 재질인지 모름 → "라벨 '○○' 재질 확인"
- 신고 재질 중 라벨에 안 보이는 것은 경고하지 않는다(라벨에 모든 부위가 적히지는 않음).

라벨 재질 글자는 서류 판독 결과에 칸이 생기면 받는다(ParsedDocument.label_materials, KHS에 요청한 칸 — 제안).
그 칸이 없으면 label_terms_from()이 빈 목록을 돌려 경고도 없다.
"""

from app.a3_judge.material.codes import split_materials
from app.a3_judge.material.equiv import compare_sets
from app.core.schema.document import ParsedDocument

TAG_LABEL = "라벨 재질"


def label_terms_from(docs: list[ParsedDocument]) -> list[str]:
    """LABEL 서류의 라벨 재질 글자들(중복 없이). 칸이 아직 없으면 빈 목록."""
    out: list[str] = []
    for d in docs:
        if d.doc_type != "LABEL":
            continue
        raw = getattr(d, "label_materials", None) or []
        items = raw if isinstance(raw, list) else split_materials(str(raw))
        for t in items:
            t = str(t).strip()
            if t and t not in out:
                out.append(t)
    return out


def label_warning(
    decided: list[str],
    label_terms: list[str],
    aliases: dict[str, str] | None = None,
    known: set[str] | frozenset[str] | None = None,
) -> str | None:
    """decided = 지금 재질 칸의 재질 목록. 경고가 없으면 None."""
    if not decided or not label_terms:
        return None
    verdicts = compare_sets(label_terms, decided, aliases, known)
    diff = [t for t, v in verdicts.items() if v == "different"]
    unknown = [t for t, v in verdicts.items() if v == "unknown"]
    parts: list[str] = []
    if diff:
        parts.append(
            f"라벨에는 {', '.join(diff)} — 신고 재질({', '.join(decided)})과 다름, 확인 필요"
        )
    if unknown:
        parts.append(f"라벨 표기 {', '.join(repr(t) for t in unknown)}가 어떤 재질인지 확인")
    return " / ".join(parts) or None
