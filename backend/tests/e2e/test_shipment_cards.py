"""화면 ① 선적 건 정리(HS 요청 11/27): B/L을 못 읽은 건 → 상태 글자·다음 할 일, B/L 직접 입력,
같은 건에 서류 더 올리기, 건 삭제(백업). 가상 샘플 A만, 외부 API 없음. 담당: KHS"""

import io
import json

from openpyxl import Workbook, load_workbook

from tests.e2e.test_p0_flow import SAMPLES, client  # noqa: F401

SRC = SAMPLES / "A" / "BL-TEST-003"


def _no_bl(name: str) -> tuple[str, bytes, str]:
    """B/L 번호 줄을 뺀 가상 서류(엑셀)."""
    wb = Workbook()
    for row in load_workbook(SRC / name, data_only=True).active.iter_rows(values_only=True):
        if row and str(row[0] or "").startswith("B/L"):
            continue
        wb.active.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return (name, buf.getvalue(), "application/octet-stream")


def _up(client, names: list[str], folder_id: str | None = None) -> dict:  # noqa: F811
    data = {"shipper_id": "A", **({"folder_id": folder_id} if folder_id else {})}
    r = client.post("/api/reader/upload", data=data, files=[("files", _no_bl(n)) for n in names])
    assert r.status_code == 200, r.text
    return r.json()


def _cards(client) -> list[dict]:  # noqa: F811
    return client.get("/api/reader/shipments", params={"shipper_id": "A"}).json()


def test_no_bl_card_states_then_enter_bl(client):  # noqa: F811
    up = _up(client, ["CI.xlsx"])
    card = next(c for c in _cards(client) if up["folder_id"] in c["folder_ids"])
    assert card["bl_no"] == "" and card["next"] == "enter_bl"
    assert card["doc_states"]["CI"] == "check"  # 읽었지만 B/L 번호 확인 필요
    assert card["doc_states"]["PL"] == "missing"
    assert card["files"] == ["CI.xlsx"]

    # 같은 건에 서류 더 올리기: 새 카드가 생기지 않는다
    _up(client, ["PL.xlsx"], folder_id=up["folder_id"])
    mine = [c for c in _cards(client) if up["folder_id"] in c["folder_ids"]]
    assert len(mine) == 1 and mine[0]["doc_states"]["PL"] in ("ok", "check")

    # B/L 번호 직접 입력 → 그 번호로 묶이고 행에 B/L이 들어간다
    r = client.put(
        "/api/reader/shipments/bl",
        json={"shipper_id": "A", "folder_ids": [up["folder_id"]], "bl_no": " bl-test 777 "},
    )
    assert r.status_code == 200, r.text
    assert r.json()["bl_no"] == "BLTEST777"
    card = next(c for c in _cards(client) if up["folder_id"] in c["folder_ids"])
    assert card["bl_no"] == "BLTEST777" and card["next"] in (
        "upload_missing",
        "fix_docs",
        "review",
        "done",
    )
    assert card["row_ids"] and all(k.count("|") == 1 for k in card["row_ids"])  # 품목 → ② 그 행
    rows = [
        x
        for x in client.get("/api/history", params={"shipper_id": "A"}).json()
        if x["cells"].get("B/L Number", {}).get("ai_value") == "BLTEST777"
    ]
    assert rows  # 예전 B/L 없는 행은 새 번호 행으로 이어졌다
    orphan = [
        x
        for x in client.get("/api/history", params={"shipper_id": "A"}).json()
        if not x["cells"].get("B/L Number", {}).get("ai_value") and not x.get("shipment_bl")
    ]
    assert not orphan


def test_bad_bl_rejected(client):  # noqa: F811
    up = _up(client, ["CI.xlsx"])
    r = client.put(
        "/api/reader/shipments/bl",
        json={"shipper_id": "A", "folder_ids": [up["folder_id"]], "bl_no": "ab"},
    )
    assert r.status_code == 400


def test_delete_shipment_backs_up(client, tmp_path):  # noqa: F811
    up = _up(client, ["CI.xlsx", "PL.xlsx"])
    r = client.post(
        "/api/reader/shipments/delete", json={"shipper_id": "A", "folder_ids": [up["folder_id"]]}
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["deleted_documents"] == 2 and out["deleted_rows"] >= 1
    assert not [c for c in _cards(client) if up["folder_id"] in c["folder_ids"]]
    backup = tmp_path / "data" / "deleted" / out["backup"]
    data = json.loads(backup.read_text(encoding="utf-8"))
    assert len(data["documents"]) == 2 and data["rows"]


def test_reread_keeps_doc_ids_and_rows(client):  # noqa: F811
    up = _up(client, ["CI.xlsx", "PL.xlsx"])
    before = next(c for c in _cards(client) if up["folder_id"] in c["folder_ids"])
    ids = {d["doc_id"] for d in before["documents"].values()}
    r = client.post(
        "/api/reader/shipments/reread", json={"shipper_id": "A", "folder_ids": [up["folder_id"]]}
    )
    assert r.status_code == 200, r.text
    after = next(c for c in _cards(client) if up["folder_id"] in c["folder_ids"])
    assert {d["doc_id"] for d in after["documents"].values()} == ids  # 같은 서류 번호 이어 씀
    assert after["row_count"] == before["row_count"]
