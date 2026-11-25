"""재질 근거 ④ 현품사진·라벨. 담당: LSY

사진만으로 재질을 확정하지 않는다(미팅 11/24, AGENTS 7-9). 사진·라벨이 올라와 있으면 근거로만 적고
값은 비운 채 '확인 필요'로 둔다(담당자가 라벨을 보고 고른다).
"""

from app.core.schema.document import ParsedDocument
from app.core.schema.fields import Evidence


def from_label_photo(docs: list[ParsedDocument]) -> Evidence | None:
    pics = [d for d in docs if d.doc_type in ("PHOTO", "LABEL")]
    if not pics:
        return None
    kinds = sorted({"라벨" if d.doc_type == "LABEL" else "현품사진" for d in pics})
    return Evidence(
        source="LABEL" if "라벨" in kinds else "PHOTO",
        ref=pics[0].doc_id,
        note=f"{'·'.join(kinds)} {len(pics)}장 있음 — 사진만으로 재질을 정하지 않음, 라벨을 보고 고르세요",
    )
