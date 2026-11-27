"""검역 리스트 탭 2·3·4단계: 서류 3종 대조(코드 + 가짜 AI), 불일치 칸 막기, 값 고르기(final_value·MANUAL),
다시 대조해도 final_value 유지, 등록 정보 채우기. 가상 샘플 A만, 외부 API 없음."""

from app.a1_history.crosscheck import ai_check
from tests.e2e.test_p0_flow import SAMPLES, _files, _register, client  # noqa: F401

CART = "카톤 수"


def _up(client, name: str) -> dict:  # noqa: F811
    r = client.post(
        "/api/reader/upload", data={"shipper_id": "A"}, files=_files(SAMPLES / "A" / name)
    )
    assert r.status_code == 200, r.text
    return r.json()


def _row(client, bl: str, model: str) -> dict:  # noqa: F811
    rows = client.get("/api/history", params={"shipper_id": "A"}).json()
    return next(
        x
        for x in rows
        if x["cells"].get("B/L Number", {}).get("ai_value") == bl
        and x["model"] == model
        and not x["is_part"]
    )


def test_carton_mismatch_blocks_cell(client):  # noqa: F811
    _up(client, "BL-TEST-004")
    ms = client.get("/api/history/mismatches", params={"shipper_id": "A"}).json()
    bad = [m for m in ms if m["status"] == "불일치"]
    assert any(
        m["item"] == CART and m["model"] == "RC-200" and m["CI"] == 8 and m["PL"] == 9 for m in bad
    )
    assert any(m["item"].startswith("CI 금액 TOTAL") for m in bad)
    cell = _row(client, "BLTEST004", "RC-200")["cells"][CART]
    assert (
        cell["ai_value"] is None and cell["flag"] == "mismatch"
    )  # 불일치 값은 완성된 리스트에 안 들어감
    ok = _row(client, "BLTEST004", "RC-100")["cells"][CART]
    assert ok["ai_value"] == 12 and ok["flag"] != "mismatch"  # 일치 값은 들어감


def test_resolve_and_recheck_keeps_final(client):  # noqa: F811
    _up(client, "BL-TEST-004")
    rid = _row(client, "BLTEST004", "RC-200")["row_id"]
    r = client.patch(
        f"/api/history/{rid}/resolve",
        json={"choices": [{"item": CART, "source": "PL", "memo": "PL이 맞음"}]},
    )
    assert r.status_code == 200, r.text
    cell = r.json()["cells"][CART]
    assert cell["final_value"] == 9 and cell["flag"] == "edited"
    assert any(e["source"] == "MANUAL" and "PL 값 선택" in e["note"] for e in cell["evidence"])
    assert client.post("/api/history/crosscheck", params={"shipper_id": "A"}).status_code == 200
    cell = _row(client, "BLTEST004", "RC-200")["cells"][CART]
    assert cell["final_value"] == 9  # 다시 대조해도 담당자 값 유지
    st = [
        m["status"]
        for m in client.get("/api/history/mismatches", params={"shipper_id": "A"}).json()
        if m["row_id"] == rid and m["item"] == CART
    ]
    assert st == ["해결됨"]
    r = client.patch(
        f"/api/history/{rid}/resolve",
        json={"choices": [{"item": CART, "source": "manual", "value": "10"}]},
    )
    cell = r.json()["cells"][CART]
    assert cell["final_value"] == 10 and any(
        e["note"].startswith("MANUAL: 직접 입력") for e in cell["evidence"]
    )


def test_bl_typo_ai_points_document(client, monkeypatch):  # noqa: F811
    import app.core.llm as llm

    def fake_call(prompt, version, inputs, schema, mask_names=None, images=None):
        if schema is not ai_check.AiOut:
            return None  # 추출 보충 등 다른 호출은 '못 얻음'
        items = [
            ai_check.AiItem(
                key=i["key"],
                same=False,
                what="B/L 번호: PL만 한 글자 다름",
                typo_doc="PL",
                suggested="BLTEST006",
                confidence=0.9,
            )
            for i in inputs["items"]
            if i["item"] == "B/L 번호"
        ]
        return ai_check.AiOut(items=items)

    monkeypatch.setattr(llm, "ready", lambda: True)
    monkeypatch.setattr(llm, "send_allowed", lambda: True)  # 화주명 목록이 있다고 가정(가짜 AI)
    monkeypatch.setattr(llm, "call_structured", fake_call)
    _up(client, "BL-TEST-006")
    ms = [
        m
        for m in client.get("/api/history/mismatches", params={"shipper_id": "A"}).json()
        if m["item"] == "B/L 번호"
    ]
    assert ms and all(m["status"] == "불일치" for m in ms)
    assert ms[0]["ai"]["typo_doc"] == "PL" and ms[0]["ai"]["suggested"] == "BLTEST006"
    assert ms[0]["code_different"] is True
    rid = ms[0]["row_id"]
    cell = client.get(f"/api/history/{rid}").json()["cells"]["B/L Number"]
    assert cell["ai_value"] is None and cell["final_value"] is None
    pick = {"choices": [{"item": "B/L 번호", "source": "manual", "value": "CHECKED"}]}
    assert client.patch(f"/api/history/{rid}/resolve", json=pick).status_code == 200
    again = _up(client, "BL-TEST-006")
    assert rid in again["updated"] and not again["created"]
    assert client.post("/api/history/crosscheck", params={"shipper_id": "A"}).status_code == 200
    review = client.get(f"/api/history/{rid}/review").json()
    assert review["row"]["cells"]["B/L Number"]["final_value"] == "CHECKED"
    bl = next(it for it in review["items"] if it["item"] == "B/L 번호")
    assert bl["PL"] != bl["BL"] and bl["status"] == "해결됨"


def test_ai_off_code_only(client):  # noqa: F811
    _up(client, "BL-TEST-003")  # 정상 건: 불일치 없음, AI는 꺼져 있음(ai=None)
    ms = client.get("/api/history/mismatches", params={"shipper_id": "A", "status": "일치"}).json()
    assert ms and all(m["ai"] is None for m in ms)
    assert not client.get("/api/history/mismatches", params={"shipper_id": "A"}).json()


def test_fill_from_registry(client):  # noqa: F811
    _up(client, "BL-TEST-003")
    _register(client, "A")
    registered = _row(client, "BLTEST003", "RC-100")["cells"]
    assert registered["실적접수번호 (승인일)"]["ai_value"] == "202300000101 (2023.04.25)"
    assert (
        registered["제조사"]["ai_value"]
        and registered["재질 (재질 코드명으로 작성, 가나다 순으로 기재)"]["ai_value"]
    )
    out = client.post("/api/history/fill", params={"shipper_id": "A"}).json()
    assert out["judged"] >= 1
    cell = _row(client, "BLTEST003", "RC-100")["cells"]["실적접수번호 (승인일)"]
    assert cell["ai_value"] == "202300000101 (2023.04.25)"
    steps = client.get("/api/history/steps", params={"shipper_id": "A"}).json()
    assert [s["key"] for s in steps["steps"]] == ["upload", "review", "list"]
