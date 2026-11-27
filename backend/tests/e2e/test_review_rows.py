"""화면 ② 목록: '해결됨' 필터에 해결한 행이 보이고, 필터 숫자 = 목록 개수 (HS 요청 11/27). 가상 샘플 A. 담당: KHS"""

from tests.e2e.test_list_crosscheck import CART, _row, _up
from tests.e2e.test_p0_flow import client  # noqa: F401


def _list(client) -> dict:  # noqa: F811
    r = client.get("/api/history/review-rows", params={"shipper_id": "A"})
    assert r.status_code == 200, r.text
    return r.json()


def test_resolved_row_shows_in_done_filter_and_counts_match(client):  # noqa: F811
    _up(client, "BL-TEST-004")
    rid = _row(client, "BLTEST004", "RC-200")["row_id"]
    before = _list(client)
    assert before["counts"]["done"] == 0
    r = client.patch(
        f"/api/history/{rid}/resolve",
        json={"choices": [{"item": CART, "source": "PL", "memo": "PL이 맞음"}]},
    )
    assert r.status_code == 200, r.text
    out = _list(client)
    rows = out["rows"]
    # 필터 숫자 = 그 필터로 걸러진 목록 개수
    assert out["counts"]["open"] == sum(1 for x in rows if x["open_row"])
    assert out["counts"]["done"] == sum(1 for x in rows if x["done_row"])
    assert out["counts"]["all"] == len(rows)
    # 미해결 항목(인보이스 합계)이 같이 있어도 '해결됨' 필터에 보인다
    mine = next(x for x in rows if x["row_id"] == rid)
    assert mine["done_row"] and CART in mine["done"]
    assert out["counts"]["done"] >= 1
    # 선적 건 요약(항목 수)도 같은 결과에서
    assert out["by_bl"]["BLTEST004"]["done_items"] >= 1
    # 인보이스 합계 항목은 쉬운 말로
    assert any("인보이스 합계" in i for x in rows for i in x["open"])
    # 이름이 비는 행 없음
    assert all(x["label"] for x in rows)


def test_shipment_item_shown_once_and_resolved_for_all_rows(client):  # noqa: F811
    """시트 칸이 없는 선적 건 항목(인보이스 합계 등)은 건마다 한 번만, 고르면 그 건 모든 행에 적용 (HS 11/27)."""
    _up(client, "BL-TEST-004")
    out = _list(client)
    mine = [x for x in out["rows"] if x["bl"] == "BLTEST004"]
    hits = [x for x in mine if any("인보이스 합계" in i for i in x["open"])]
    assert len(hits) == 1
    item = "CI 금액 TOTAL (시트 칸 = 줄 합)"
    r = client.patch(
        f"/api/history/{hits[0]['row_id']}/resolve",
        json={"choices": [{"item": item, "source": "CI", "memo": "인보이스 TOTAL 기준"}]},
    )
    assert r.status_code == 200, r.text
    for x in mine:
        rv = client.get(f"/api/history/{x['row_id']}/review").json()
        st = [i["status"] for i in rv["items"] if i["item"] == item]
        assert st in ([], ["해결됨"])
