"""드라이브 접수 폴더 자동 처리(inbox): 끄면 안 함, 드라이브 미연결이면 이유, 켜고 연결되면 B/L 폴더를 가져온다.
드라이브는 가짜 함수로 바꿔 시험한다(실제 접속 없음)."""

from app.a1_history.rows import service
from app.a4_settings.engine.service import merge_rules


def _rules(on: bool):
    return lambda _sid: merge_rules({"required_docs": ["CI"]}, {"inbox": on}, "T")


def test_off_does_nothing(monkeypatch):
    monkeypatch.setattr(service, "get_rules", _rules(False))
    out = service.scan_inbox("T")
    assert out["enabled"] is False and not out["imported"]


def test_drive_not_connected(monkeypatch):
    monkeypatch.setattr(service, "get_rules", _rules(True))
    monkeypatch.setattr(
        service.drive, "inbox_folders", lambda _sid: ([], "드라이브 미연결: token.json 없음")
    )
    out = service.scan_inbox("T")
    assert out["ok"] is False and "드라이브 미연결" in out["reason"]


def test_imports_folders(monkeypatch):
    monkeypatch.setattr(service, "get_rules", _rules(True))
    monkeypatch.setattr(
        service.drive, "inbox_folders", lambda _sid: ([("BL-X", [("ci.xlsx", b"x")])], "")
    )
    moved: list = []
    monkeypatch.setattr(
        service.drive, "move_folder", lambda a, b: moved.append((a, b)) or {"ok": True}
    )
    monkeypatch.setattr(
        service,
        "process_upload",
        lambda sid, files: {"bl_no": "BLX", "created": ["r1"], "updated": []},
    )
    monkeypatch.setattr(service.local_db, "audit", lambda *a, **k: None)
    out = service.scan_inbox("T")
    assert out["ok"] and out["imported"] == [{"folder": "BL-X", "bl_no": "BLX", "rows": 1}]
    assert moved == [(["T", "새 서류", "BL-X"], ["T", "가져옴"])]
