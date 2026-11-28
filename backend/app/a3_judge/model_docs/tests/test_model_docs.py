"""모델 자료 찾기 — 가짜 드라이브(네트워크 없음). 폴더를 만들지 않고 읽기만 하는지도 확인. 가상 값."""

import pytest

from app.a3_judge.model_docs import service
from app.core.config import get_settings
from app.core.storage import drive, google_auth

DIR = drive.FOLDER_MIME
TREE = {
    "ROOT": [
        {"id": "a", "name": "A기업", "mimeType": DIR},
        {"id": "x", "name": "A", "mimeType": DIR},
        {"id": "done", "name": "처리완료", "mimeType": DIR},
    ],
    "a": [{"id": "docs", "name": "현품사진 및 한글표시 사항", "mimeType": DIR}],
    "x": [],
    "docs": [
        {"id": "m1", "name": "DEMO-M01", "mimeType": DIR},
        {"id": "m1f", "name": "DEMO-M01F", "mimeType": DIR},
    ],
    "m1": [
        {"id": "f1", "name": "DEMO-M01 현품사진.xlsx", "mimeType": "application/vnd.ms-excel"},
        {"id": "f2", "name": "수입신고서.json", "mimeType": "application/json"},
        {"id": "f3", "name": "정밀실적 202600000101", "mimeType": DIR},
        {"id": "f4", "name": "시험성적서.json", "mimeType": "application/json"},
        {"id": "f5", "name": "DEMO-M01 라벨.pdf", "mimeType": "application/pdf"},
    ],
}


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("DRIVE_INBOX_FOLDER_ID", "ROOT")
    get_settings.cache_clear()
    monkeypatch.setattr(drive, "status", lambda: {"ok": True, "reason": ""})
    monkeypatch.setattr(google_auth, "headers", lambda: {"Authorization": "Bearer fake"})
    monkeypatch.setattr(drive, "list_children", lambda fid, h: TREE.get(fid, []))
    monkeypatch.setattr(drive, "download", lambda fid, h: b"DATA-" + fid.encode())

    def no_create(*a, **k):
        raise AssertionError("폴더를 만들면 안 된다")

    monkeypatch.setattr(drive, "folder_path", no_create)
    yield
    get_settings.cache_clear()


def test_finds_model_folder_and_kinds(fake):
    out = service.find_model_docs("A", "demo-m01")
    assert out["ok"] and out["path"] == "A기업/현품사진 및 한글표시 사항/DEMO-M01"
    kinds = {f["name"]: f["kind"] for f in out["files"]}
    assert kinds == {
        "DEMO-M01 현품사진.xlsx": "excel",
        "수입신고서.json": "import_decl",
        "정밀실적 202600000101": "precise",
        "시험성적서.json": "test_report",
        "DEMO-M01 라벨.pdf": "image",
    }


def test_exact_model_only(fake):
    out = service.find_model_docs("A", "DEMO-M0")
    assert not out["ok"] and out["reason"] == "이 모델의 자료 폴더 없음"


def test_shipper_folder_fallback_and_missing(fake):
    """'B기업'도 'B'도 없으면 이유만 돌려준다(새로 만들지 않음)."""
    out = service.find_model_docs("B", "DEMO-M01")
    assert not out["ok"] and "B기업 또는 B" in out["reason"]


def test_download_only_listed_files(fake):
    service.find_model_docs("A", "DEMO-M01")
    assert service.download_model_doc("f1") == ("DEMO-M01 현품사진.xlsx", b"DATA-f1")
    assert service.download_model_doc("not-listed") is None


def test_not_connected(monkeypatch):
    monkeypatch.setattr(drive, "status", lambda: {"ok": False, "reason": "token.json 없음"})
    out = service.find_model_docs("A", "DEMO-M01")
    assert not out["ok"] and out["reason"] == "드라이브 미연결: token.json 없음"


def test_no_model_code():
    assert service.find_model_docs("A", "")["reason"].startswith("모델 코드가 없어")
