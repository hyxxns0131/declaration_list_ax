"""담당자가 신고 모델을 바꿨을 때 — 판단에 쓸 모델 정하기. 순수 함수. 담당: LSY [재사용] A3-1 (기존 model_change)

부분품을 본품 한 모델로 합친 행(A사 merge_spare_parts)은 담당자가 "이 부분품은 다른 본품 모델로 신고"하고
모델을 바꾸는 일이 있다. 그런데 판단은 내부 모델 칸(row.model)으로 이력·실적을 찾아서, 바꾼 값이 반영되지 않았다.
여기서 담당자가 확정한 값으로 모델을 정한다 → 그 모델로 영문명·재질·실적을 다시 계산(pipeline/judge_row.py).
우선순위: ① '모델' 칸 확정 값 ② '한글 제품명(모델넘버)' 확정 값의 괄호 속 모델 ③ 원래 모델.
"""

from app.a3_judge.history_lookup.model_key import model_from_name
from app.core.schema.history import C_MODEL, C_NAME_KO, HistoryRow

TAG_MODEL_CHANGE = "모델 변경"
PART_NAME_EN = "SPARE PARTS FOR {model}"


def chosen_model(row: HistoryRow) -> str:
    cell = row.cells.get(C_MODEL)
    if cell and cell.final_value not in (None, ""):
        return str(cell.final_value).strip()
    name = row.cells.get(C_NAME_KO)
    if name and name.final_value not in (None, ""):
        got = model_from_name(str(name.final_value))
        if got:
            return got
    return row.model


def apply_model_change(row: HistoryRow) -> str | None:
    """row.model을 담당자 확정 모델로 맞춘다. 서류 모델과 다르면 비고 문구, 같으면 None.
    합친 부분품 행이면 영문명 프로그램 값도 'SPARE PARTS FOR {새 모델}'로(담당자 확정 값은 그대로)."""
    new = chosen_model(row)
    before = row.model
    changed = bool(new) and new.upper() != before.upper()
    if changed:
        row.model = new
        if row.is_part and row.part_lines:
            row.set_ai("영문 제품명", PART_NAME_EN.format(model=new))
    doc_models = {m.upper() for m in row.source_models.values() if m}
    if row.model and doc_models and row.model.upper() not in doc_models:
        src = ", ".join(sorted(doc_models))
        return (
            f"담당자가 신고 모델을 {row.model}로 바꿈(서류 모델 {src}) → 이 모델로 재질·실적 판단"
        )
    if changed:
        # 합친 부분품 행은 서류 모델 기록(source_models)이 없어, 바꾼 그때 비고를 남긴다
        return f"담당자가 신고 모델을 {before} → {row.model}로 바꿈 → 이 모델로 재질·실적 다시 판단"
    return None
