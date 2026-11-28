"""③ 직접 입력·행 직접 추가 (HS 요청 11/27). 가상 값만. 담당: KHS"""

from tests.e2e.test_list_crosscheck import CART, _row, _up
from tests.e2e.test_p0_flow import client  # noqa: F401

NAME = "한글 제품명(모델넘버)"


def test_manual_row_add_delete_restore_and_survives_reupload(client):  # noqa: F811
    _up(client, "BL-TEST-004")
    r = client.post(
        "/api/history/rows",
        json={
            "shipper_id": "A",
            "bl_no": "BLTEST004",
            "values": {NAME: "전기포트(KT-900)", "입수": 5, "카톤 수": 1, "순중량": 3.2},
        },
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["manual"] and row["model"] == "KT-900"
    cell = row["cells"]["카톤 수"]
    assert cell["final_value"] == 1 and cell["evidence"][0]["source"] == "MANUAL"

    # 같은 B/L 서류를 다시 올려도 직접 추가한 행은 그대로
    _up(client, "BL-TEST-004")
    again = client.get(f"/api/history/{row['row_id']}").json()
    assert again["manual"] and again["cells"]["카톤 수"]["final_value"] == 1

    # 지우고 되돌리기
    d = client.delete(f"/api/history/{row['row_id']}")
    assert d.status_code == 200
    assert client.get(f"/api/history/{row['row_id']}").status_code == 404
    back = client.post("/api/history/rows/restore", json=d.json()["row"])
    assert back.status_code == 200
    assert client.get(f"/api/history/{row['row_id']}").json()["manual"]


def test_typing_into_blocked_cell_resolves_mismatch(client):  # noqa: F811
    _up(client, "BL-TEST-004")
    rid = _row(client, "BLTEST004", "RC-200")["row_id"]
    r = client.patch(f"/api/history/{rid}", json={"column": CART, "value": 9})
    assert r.status_code == 200, r.text
    assert r.json()["cells"][CART]["final_value"] == 9
    ms = client.get("/api/history/mismatches", params={"shipper_id": "A"}).json()
    mine = [m for m in ms if m["row_id"] == rid and m["item"] == CART]
    assert mine and mine[0]["status"] == "해결됨"
    # 다시 대조해도 사람 값 유지
    client.post("/api/history/crosscheck", params={"shipper_id": "A"})
    assert _row(client, "BLTEST004", "RC-200")["cells"][CART]["final_value"] == 9
