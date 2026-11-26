"""입수 = 전체 개수(PCS 합계) (HS 결정 11/26). 가상 샘플 A만. 담당: KHS"""

from app.core.schema.document import DocumentLine
from tests.e2e.test_list_crosscheck import _up
from tests.e2e.test_p0_flow import client  # noqa: F401


def test_pcs_rules():
    assert DocumentLine(quantity=60, qty_per_carton=10, cartons=6).pcs() == 60  # 서류 수량 칸 우선
    assert DocumentLine(qty_per_carton=1, cartons=12).pcs() == 12  # 카톤당 x 카톤
    assert DocumentLine(cartons=12).pcs() is None  # 모르면 비움(지어내지 않음)


def test_history_qty_is_total_pieces(client):  # noqa: F811
    _up(client, "BL-TEST-003")  # RC-100: 카톤당 1 x 12카톤, RC-200: 1 x 8, 부분품 10x2 + 20x1
    rows = [
        r
        for r in client.get("/api/history", params={"shipper_id": "A"}).json()
        if r["cells"].get("B/L Number", {}).get("ai_value") == "BLTEST003"
    ]
    qty = {(r["model"], r["is_part"]): r["cells"]["입수"]["ai_value"] for r in rows}
    assert qty[("RC-100", False)] == 12
    assert qty[("RC-200", False)] == 8
    parts = [v for (m, p), v in qty.items() if p]
    assert parts and parts[0] == 40  # 합친 부분품 행 = 부분품 전체 개수 합
    note = next(r for r in rows if r["model"] == "RC-100" and not r["is_part"])["cells"]["입수"]
    assert "카톤당 1" in note["evidence"][0]["note"]
    # 서류 대조도 전체 개수로: 정상 건이라 입수 불일치 없음
    ms = client.get("/api/history/mismatches", params={"shipper_id": "A"}).json()
    assert not [m for m in ms if m["item"] == "입수" and m["bl_no"] == "BLTEST003"]
