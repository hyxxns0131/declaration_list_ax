"""P0·P1 흐름 전체 연결: 실적 등록 → 선적서류 1건 → 검역이력 행 → 신고건 → 품목사항 엑셀. 담당: KHS

가상 자료(samples/)만 쓴다. 외부 API는 부르지 않는다(유니패스 mock, 식약처 키 비움 → 가상 공장 목록).
"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
C_MATERIAL = "재질 (재질 코드명으로 작성, 가나다 순으로 기재)"
C_RECORD = "실적접수번호 (승인일)"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    env = {
        "LOCAL_DB_PATH": str(tmp_path / "t.db"),
        "DATA_DIR": str(tmp_path / "data"),
        "AUTH_ENABLED": "false",
        "UNIPASS_MODE": "mock",
        "LLM_ENABLED": "false",
        "MFDS_OVERSEAS_MAKER_API_KEY": "",
        "SUPABASE_URL": "",
        "SUPABASE_ANON_KEY": "",
        "GOOGLE_TOKEN_FILE": str(tmp_path / "no-token.json"),
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.a3_judge.material import codes

    codes.load_aliases.cache_clear()
    codes.load_known_names.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def _files(folder: Path) -> list[tuple[str, tuple[str, bytes]]]:
    return [("files", (p.name, p.read_bytes())) for p in sorted(folder.iterdir()) if p.is_file()]


def _register(client: TestClient, shipper: str) -> dict:
    r = client.post(
        "/api/registry/upload",
        data={"shipper_id": shipper},
        files=_files(SAMPLES / "registry" / shipper),
    )
    assert r.status_code == 200, r.text
    up = r.json()
    r = client.post(f"/api/registry/upload/{up['upload_id']}/commit", json={"edits": []})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_flow_upload_to_item_sheet(client):
    reg = _register(client, "A")
    assert "202300000101" in reg["records"]

    r = client.post(
        "/api/reader/upload", data={"shipper_id": "A"}, files=_files(SAMPLES / "A" / "BL-TEST-001")
    )
    assert r.status_code == 200, r.text
    up = r.json()
    assert up["bl_no"] == "BLTEST001" and up["created"]

    rows = client.get("/api/history", params={"shipper_id": "A"}).json()
    by_model = {(x["model"], x["is_part"]): x for x in rows}
    rc100 = by_model[("RC-100", False)]["cells"]
    # 재질 ② 이전 수입신고서, 제조사 = 가상 공장 주소 매칭, 실적 = 같은 공장·재질 포함 유효 실적
    assert rc100[C_MATERIAL]["ai_value"] == "금속제(불소수지도장), 폴리프로필렌"
    assert rc100["제조사"]["ai_value"].endswith("(CN900000001)")
    assert rc100[C_RECORD]["ai_value"] == "202300000101 (2023.04.25)"
    # A사: 부분품 줄은 본품 모델 1행으로 합침(merge_spare_parts)
    parts = [x for x in rows if x["is_part"]]
    assert len(parts) == 1 and len(parts[0]["part_lines"]) == 2

    decls = client.post("/api/judge/declarations", params={"shipper_id": "A"}).json()
    assert decls
    first = decls[0]
    prev = client.post("/api/judge/item-sheet/preview", json={"row_ids": first["row_ids"]}).json()
    assert prev["ok"], prev
    made = client.post("/api/judge/item-sheet", json={"row_ids": first["row_ids"]}).json()
    xl = client.get(f"/api/judge/item-sheet/{made['file_id']}")
    assert xl.status_code == 200
    ws = load_workbook(BytesIO(xl.content)).active
    assert ws.cell(1, 1).value == "제품명" and ws.cell(2, 3).value == "Y"


def test_item_sheet_rejects_mixed_declarations(client):
    _register(client, "A")
    for bl in ("BL-TEST-001", "BL-TEST-002"):
        client.post(
            "/api/reader/upload", data={"shipper_id": "A"}, files=_files(SAMPLES / "A" / bl)
        )
    rows = client.get("/api/history", params={"shipper_id": "A"}).json()
    bls = {x["cells"]["B/L Number"]["ai_value"] for x in rows}
    assert bls == {"BLTEST001", "BLTEST002"}
    mixed = [
        next(x["row_id"] for x in rows if x["cells"]["B/L Number"]["ai_value"] == b)
        for b in sorted(bls)
    ]
    prev = client.post("/api/judge/item-sheet/preview", json={"row_ids": mixed}).json()
    assert not prev["ok"] and "모선" in prev["reasons"][0]
    assert client.post("/api/judge/item-sheet", json={"row_ids": mixed}).status_code == 400


def test_final_value_survives_refresh(client):
    _register(client, "A")
    client.post(
        "/api/reader/upload", data={"shipper_id": "A"}, files=_files(SAMPLES / "A" / "BL-TEST-001")
    )
    row = client.get("/api/history", params={"shipper_id": "A"}).json()[0]
    r = client.patch(
        f"/api/history/{row['row_id']}", json={"column": "비고", "value": "담당자 메모"}
    )
    assert r.status_code == 200
    client.post("/api/history/refresh", params={"shipper_id": "A"})
    again = client.get(f"/api/history/{row['row_id']}").json()
    assert again["cells"]["비고"]["final_value"] == "담당자 메모"
    # 가격(USD)은 계산 칸이라 직접 입력 금지
    r = client.patch(f"/api/history/{row['row_id']}", json={"column": "가격(USD)", "value": 1})
    assert r.status_code == 400


def test_settings_change_result_without_code(client):
    """가상 화주 2곳: 설정만으로 결과가 달라진다(A4-3). 시험 실행은 저장하지 않는다."""
    _register(client, "A")
    out = client.post(
        "/api/settings/shippers/A/dry-run", json={"settings": {"merge_spare_parts": False}}
    ).json()
    assert out["changed"][0]["key"] == "merge_spare_parts"
    before_rows = sum(len(d["rows"]) for d in out["before"])
    after_rows = sum(len(d["rows"]) for d in out["after"])
    assert after_rows == before_rows + 1  # 부분품 2줄이 따로 행이 된다
    assert client.get("/api/settings/shippers/A").json()["settings"]["merge_spare_parts"] is True


def test_b_shipper_max_rows_and_color(client):
    _register(client, "B")
    client.post(
        "/api/reader/upload", data={"shipper_id": "B"}, files=_files(SAMPLES / "B" / "BL-TEST-101")
    )
    decls = client.post("/api/judge/declarations", params={"shipper_id": "B"}).json()
    assert all(len(d["row_ids"]) <= 5 for d in decls)  # B사 신고당 최대 5행
    colors = {d["key"]["color"] for d in decls}
    assert {"SILVER", "BLACK"} <= colors  # 색상이 같아야 같은 신고


def test_registry_alerts_and_status(client):
    _register(client, "A")
    recs = {
        r["record_no"]: r
        for r in client.get("/api/registry/records", params={"shipper_id": "A"}).json()
    }
    assert recs["202000000404"]["status"] == "만료"
    assert recs["202300000101"]["expires_on"] == "2028-04-25"
    alerts = client.get(
        "/api/registry/alerts", params={"shipper_id": "A", "within_days": 3650}
    ).json()
    assert alerts["mail"]["ok"] is False  # 메일 계정 미설정 → 보내지 않음
    sent = client.post("/api/registry/alerts/send", params={"shipper_id": "A"}).json()
    assert sent["sent"] == 0
