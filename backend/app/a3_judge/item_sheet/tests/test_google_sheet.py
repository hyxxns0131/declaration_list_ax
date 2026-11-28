"""품목사항 구글 시트 만들기 — 가짜 구글(네트워크 없음). 이름 형식·폴더·값·막힌 신고건. 가상 화주 A."""

import pytest

from app.a3_judge.item_sheet import google_sheet
from app.a3_judge.item_sheet.tests.test_bulk import _upload_a
from app.core.storage import google_auth
from tests.e2e.test_p0_flow import client  # noqa: F401


class FakeResp:
    def __init__(self, body, code=200):
        self._b, self.status_code = body, code

    def json(self):
        return self._b


@pytest.fixture()
def fake_google(monkeypatch):
    calls = []

    def req(method, url, headers=None, timeout=None, **kw):
        calls.append((method, url, kw))
        if "drive" in url:
            return FakeResp({"id": "SHEET1", "webViewLink": "https://example.invalid/s/SHEET1"})
        return FakeResp({"updatedCells": 1})

    monkeypatch.setenv(google_sheet.FOLDER_ENV, "FOLDER-TEST")
    monkeypatch.setattr(google_auth, "headers", lambda: {"Authorization": "Bearer fake"})
    monkeypatch.setattr(google_sheet.httpx, "request", req)
    return calls


def test_title_format():
    from datetime import date

    assert google_sheet.sheet_title("A", 1, date(2026, 11, 28)) == "품목사항_A사_신고건1_20261128"


def test_creates_sheet_in_folder_with_rows(client, fake_google):  # noqa: F811
    decls = _upload_a(client)
    ok = client.post("/api/judge/item-sheet/bulk", json={"shipper_id": "A"}).json()["included"]
    did = ok[0]["declaration_id"]
    r = client.post(
        "/api/judge/item-sheet/google", params={"shipper_id": "A", "declaration_id": did}
    )
    out = r.json()
    assert r.status_code == 200 and out["ok"], out
    assert out["title"].startswith("품목사항_A사_신고건")
    n_rows = len(next(d for d in decls if d["declaration_id"] == did)["row_ids"])
    assert out["rows"] == n_rows
    (m1, u1, k1), (m2, u2, k2) = fake_google
    assert m1 == "POST" and k1["json"]["parents"] == ["FOLDER-TEST"]
    assert k1["json"]["mimeType"] == google_sheet.SHEET_MIME
    assert m2 == "PUT" and "SHEET1" in u2 and k2["params"]["valueInputOption"] == "RAW"
    assert len(k2["json"]["values"]) == n_rows + 1  # 머리글 + 그 신고건 행


def test_no_folder_or_login_makes_nothing(client, monkeypatch):  # noqa: F811
    decls = _upload_a(client)
    did = decls[0]["declaration_id"]
    monkeypatch.setenv(google_sheet.FOLDER_ENV, "")
    monkeypatch.setattr(google_sheet, "folder_id", lambda: "")
    out = client.post(
        "/api/judge/item-sheet/google", params={"shipper_id": "A", "declaration_id": did}
    ).json()
    assert out["ok"] is False
