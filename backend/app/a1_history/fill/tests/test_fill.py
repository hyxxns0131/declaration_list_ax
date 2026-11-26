"""등록 정보 표시(서류 등록 필요)와 만료 실적 미선택. 가상 값만. (검역 리스트 탭 4단계)"""

from datetime import date

from app.a1_history.fill.service import NEED, mark_unregistered
from app.a3_judge.record_pick.rank import choose_record
from app.core.schema.history import HistoryRow
from app.core.schema.record import Record


def test_unregistered_model_marked_and_cleared():
    r = HistoryRow(row_id="r1", shipper_id="T", model="ZZ-1")
    assert mark_unregistered([r], set()) == [r] and NEED in r.text("비고")
    assert mark_unregistered([r], {"ZZ-1"}) == [r] and NEED not in r.text("비고")


def test_expired_record_not_chosen():
    old = Record(
        record_no="201900000001",
        factory_code="CN900000001",
        materials=["폴리프로필렌"],
        approved_on="2019-01-01",
    )
    c = choose_record([old], ["폴리프로필렌"], "CN900000001", "", "냄비", date(2026, 11, 26))
    assert c.value is None and c.precise_needed
