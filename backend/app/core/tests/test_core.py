from app.core.masking import MASK, mask_inputs
from app.core.schema.fields import Evidence, Field
from app.core.schema.history import COLUMNS


def test_26_columns():
    assert len(COLUMNS) == 26
    assert COLUMNS[0] == "B/L Number" and COLUMNS[-1] == "비고"


def test_rerun_keeps_final_value():
    f: Field[str] = Field(ai_value="PP", final_value="PE")
    g = f.rerun("PS", [Evidence(source="RULE", ref="test")])
    assert g.final_value == "PE" and g.ai_value == "PS" and g.value == "PE"


def test_masking():
    out = mask_inputs({"a": ["가상화주 주식회사 서울"]}, ["가상화주"])
    assert out == {"a": [f"{MASK} 주식회사 서울"]}
