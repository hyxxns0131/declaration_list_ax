"""부품별 실적 분리(split_record_by_part): 켜면 본체 + 뚜껑 실적으로 나눠 쓰고, 끄면 정밀검사 대상. 가상 실적."""

from datetime import date

from app.a3_judge.record_pick.multi_record import choose_split, part_label
from app.a3_judge.record_pick.rank import choose_record
from app.core.schema.record import Record, SamplePart

ON = date(2026, 11, 25)
BODY = Record(
    record_no="202400000001",
    factory_code="CN900000001",
    materials=["스테인리스강"],
    approved_on="2024-05-01",
    sample_parts=[SamplePart(material="스테인리스강", part="본체")],
)
LID = Record(
    record_no="202400000002",
    factory_code="CN900000001",
    materials=["폴리프로필렌"],
    approved_on="2024-06-01",
    sample_parts=[SamplePart(material="폴리프로필렌", part="뚜껑")],
)
MATS = ["스테인리스강", "폴리프로필렌"]


def test_off_means_precise_needed():
    c = choose_record([BODY, LID], MATS, "CN900000001", "", "냄비", ON)
    assert c.value is None and c.precise_needed


def test_on_splits_body_and_lid():
    assert part_label(LID) == "뚜껑" and part_label(BODY) == ""
    c = choose_split([BODY, LID], MATS, "CN900000001", "", "냄비", ON)
    assert c is not None
    assert c.value == "202400000001 (2024.05.01) / 뚜껑: 202400000002 (2024.06.01)"


def test_no_part_record_no_split():
    assert choose_split([BODY], MATS, "CN900000001", "", "냄비", ON) is None
