"""화주 삭제: 백업으로 옮김, 기본 화주 A·B 거절, 없는 화주 404. 가상 화주만 쓴다."""

import json
import shutil

import pytest

from app.a4_settings.engine.service import RULES_DIR
from app.a4_settings.shippers import service
from app.core.errors import AppError


@pytest.fixture()
def rules(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOCAL_DB_PATH", str(tmp_path / "t.db"))
    from app.core.config import get_settings
    from app.core.storage import local_db

    get_settings.cache_clear()
    local_db.migrate()
    d = tmp_path / "rules"
    (d / "shippers").mkdir(parents=True)
    for name in ("catalog.json", "default.json", "customs_code.json"):
        shutil.copy(RULES_DIR / name, d / name)
    for sid in ("A", "B"):
        (d / "shippers" / f"{sid}.json").write_text(
            json.dumps({"shipper_id": sid, "display_name": f"{sid}사"}), encoding="utf-8"
        )
    yield d
    get_settings.cache_clear()


def test_delete_moves_to_backup(rules, tmp_path):
    sid = service.create_shipper("TEST000000003", "Z", rules)["settings"]["shipper_id"]
    out = service.delete_shipper(sid, rules)
    assert not (rules / "shippers" / f"{sid}.json").exists()
    backup = tmp_path / "data" / "deleted_shippers" / out["backup"]
    assert backup.exists() and json.loads(backup.read_text(encoding="utf-8"))["shipper_id"] == sid
    assert [s["shipper_id"] for s in service.list_shippers(rules)] == ["A", "B"]


@pytest.mark.parametrize("sid", ["A", "B", "a"])
def test_default_shippers_refused(rules, sid):
    with pytest.raises(AppError) as e:
        service.delete_shipper(sid, rules)
    assert e.value.status == 409
    assert (rules / "shippers" / f"{sid.upper()}.json").exists()


def test_unknown_404(rules):
    with pytest.raises(AppError) as e:
        service.delete_shipper("NOPE", rules)
    assert e.value.status == 404
