"""품목사항 한꺼번에 내려받기(HS 요청 11/26): 전체 ZIP 파일 수·제외 목록, 같은 품목끼리 고르기,
한 시트에 신고건이 섞이지 않는지. 가상 화주 A 샘플만 쓴다(외부 API 없음)."""

import zipfile
from io import BytesIO

from openpyxl import load_workbook

from tests.e2e.test_p0_flow import SAMPLES, _files, _register, client  # noqa: F401


def _upload_a(client):  # noqa: F811
    _register(client, "A")
    for bl in ("BL-TEST-001", "BL-TEST-002"):
        r = client.post(
            "/api/reader/upload", data={"shipper_id": "A"}, files=_files(SAMPLES / "A" / bl)
        )
        assert r.status_code == 200, r.text
    return client.get("/api/judge/declarations", params={"shipper_id": "A"}).json()


def _zip(client, file_id: str) -> zipfile.ZipFile:  # noqa: F811
    r = client.get(f"/api/judge/item-sheet/bulk/{file_id}")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(BytesIO(r.content))


def test_all_export_counts_and_exclusions(client):  # noqa: F811
    decls = _upload_a(client)
    out = client.post("/api/judge/item-sheet/bulk", json={"shipper_id": "A"}).json()
    assert len(out["included"]) + len(out["excluded"]) == len(decls)  # 빠뜨린 신고건 없음
    zf = _zip(client, out["file_id"])
    names = zf.namelist()
    per_decl = [n for n in names if n.endswith(".xlsx") and not n.startswith("검토용_합본")]
    assert len(per_decl) == len(out["included"])
    assert all(n.startswith("A_신고건") for n in per_decl)
    assert "제외됨.txt" in names
    text = zf.read("제외됨.txt").decode("utf-8")
    for x in out["excluded"]:
        assert f"신고건 {x['number']}" in text and x["reasons"]


def test_group_selection_limits_declarations(client):  # noqa: F811
    decls = _upload_a(client)
    groups = client.get(
        "/api/judge/item-sheet-groups", params={"shipper_id": "A", "group_by": "factory"}
    ).json()
    assert sum(g["count"] for g in groups) == len(decls)
    g = groups[0]
    out = client.post(
        "/api/judge/item-sheet/bulk",
        json={"shipper_id": "A", "group_by": "factory", "groups": [g["key"]]},
    ).json()
    got = {x["declaration_id"] for x in out["included"] + out["excluded"]}
    assert got == set(g["declaration_ids"])


def test_one_sheet_never_mixes_declarations(client):  # noqa: F811
    decls = _upload_a(client)
    rows_of = {d["declaration_id"]: len(d["row_ids"]) for d in decls}
    out = client.post("/api/judge/item-sheet/bulk", json={"shipper_id": "A"}).json()
    zf = _zip(client, out["file_id"])
    for x in out["included"]:
        ws = load_workbook(BytesIO(zf.read(x["filename"]))).active
        body = [r for r in ws.iter_rows(min_row=2, values_only=True) if any(r)]
        assert len(body) == rows_of[x["declaration_id"]]  # 그 신고건 행만
        assert [r[2] for r in body].count("Y") == 1  # 대표품목 1개
    book = next(n for n in zf.namelist() if n.startswith("검토용_합본"))
    wb = load_workbook(BytesIO(zf.read(book)))
    assert len(wb.sheetnames) == max(1, len(out["included"]))


def test_bad_group_basis(client):  # noqa: F811
    r = client.get("/api/judge/item-sheet-groups", params={"shipper_id": "A", "group_by": "color"})
    assert r.status_code == 400
