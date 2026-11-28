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


def test_fill_if_changed_runs_once_per_registry_change(tmp_path, monkeypatch):
    """등록 정보 지문이 같으면 다시 채우지 않고, 바뀌면 채운다(HS 요청 11/27)."""
    from app.a1_history.fill import service as fs
    from app.core import config

    monkeypatch.setattr(config.get_settings(), "data_dir", str(tmp_path), raising=False)
    monkeypatch.setattr(
        fs, "fill", lambda shipper_id, row_ids=None: {"judged": 3, "need_registry": 0}
    )
    fp = {"v": "a"}
    monkeypatch.setattr(fs, "registry_fingerprint", lambda sid: fp["v"])
    first = fs.fill_if_changed("A")
    assert first["changed"] and first["judged"] == 3
    assert fs.fill_if_changed("A") == {"changed": False}
    fp["v"] = "b"
    assert fs.fill_if_changed("A")["changed"]
