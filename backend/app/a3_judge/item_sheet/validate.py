"""고른 행이 한 신고건인지 검사. 아니면 이유를 B/L·모델로. 순수 함수. 담당: LSY [재사용] A3-5

기존 item_sheet.check_one_declaration과 같은 역할.
"""

from app.a3_judge.grouping.keys import key_tuple, material_key, row_key
from app.core.schema.history import C_BL, HistoryRow
from app.core.schema.shipper import ShipperSettings

KEY_LABELS = ("모선", "제조사", "재질", "색상")


def check_one_declaration(rows: list[HistoryRow], settings: ShipperSettings) -> list[str]:
    """빈 목록이면 한 신고건. 아니면 사람이 읽을 이유 목록."""
    if not rows:
        return ["고른 행이 없습니다."]
    reasons: list[str] = []
    first = key_tuple(row_key(rows[0], settings))
    for r in rows[1:]:
        k = key_tuple(row_key(r, settings))
        diff = [KEY_LABELS[i] for i in range(4) if k[i] != first[i]]
        if diff:
            reasons.append(
                f"{r.text(C_BL)} {r.model}: 첫 행({rows[0].text(C_BL)} {rows[0].model})과 "
                f"{'·'.join(diff)}이(가) 다릅니다"
            )
    no_mat = [f"{r.text(C_BL)} {r.model}".strip() for r in rows if not material_key(r)]
    if no_mat:
        # 재질이 정해지지 않은 행은 신고할 수 없다(신고 묶음에서도 따로 둔다, 11/26 LSY)
        reasons.append(f"재질이 정해지지 않은 행: {', '.join(no_mat)}")
    max_rows = settings.max_rows_per_declaration
    if max_rows and len(rows) > max_rows:
        reasons.append(f"신고당 최대 {max_rows}행입니다 (고른 행 {len(rows)}개)")
    return reasons
