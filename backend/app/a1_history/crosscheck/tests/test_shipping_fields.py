"""같은 선적의 CI·PL 모델 철자, 제조사, 금액 차이가 검수 전 표에 들어가지 않는다."""

from app.a1_history.crosscheck.service import apply_flags, crosscheck_row
from app.a1_history.rows.build import build_rows
from app.a4_settings.engine.service import get_rules
from app.core.schema.document import DocumentLine, ParsedDocument
from app.core.schema.history import C_MAKER, C_MODEL, C_PRICE


def test_conflicting_fields_keep_both_sources():
    docs = [
        ParsedDocument(
            doc_id=t,
            shipper_id="A",
            folder_id="f",
            doc_type=t,
            bl_no="BL01",
            manufacturer_name=maker,
            currency="USD",
            lines=[DocumentLine(model=model, quantity=8, cartons=2, amount=amount)],
        )
        for t, model, maker, amount in [
            ("CI", "MODEL-1", "공장1", 150),
            ("PL", "MODEL-I", "공장2", 155),
        ]
    ]
    (row,) = build_rows("A", docs, get_rules("A"), None)
    items = crosscheck_row(row, docs, [row])
    apply_flags(row, items)
    assert not row.model
    for col in (C_MAKER, C_MODEL, C_PRICE):
        assert row.val(col) is None and row.cells[col].flag == "mismatch"
    again = crosscheck_row(row, docs, [row])
    model = next(it for it in again if it["cell"] == C_MODEL)
    assert (model["CI"], model["PL"]) == ("MODEL-1", "MODEL-I")
