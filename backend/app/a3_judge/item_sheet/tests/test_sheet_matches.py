"""신고건별 엑셀을 실제로 열어 선택한 신고건의 품목과 같은지(시연 피드백 11/28 3-1).
행 수·순서·한글명·수량(카톤)·과세가격(USD)·화물관리번호까지 검역이력 행과 비교한다. 가상 화주 A 샘플만."""

import zipfile
from io import BytesIO

from openpyxl import load_workbook

from app.a3_judge.item_sheet.tests.test_bulk import _upload_a
from tests.e2e.test_p0_flow import client  # noqa: F401

C_NAME_KO, C_CARTONS, C_PRICE, C_CARGO = (
    "한글 제품명(모델넘버)",
    "카톤 수",
    "가격(USD)",
    "화물관리번호",
)


def _rows(client, shipper="A"):  # noqa: F811
    j = client.get("/api/history", params={"shipper_id": shipper}).json()
    rows = j.get("rows", j) if isinstance(j, dict) else j
    return {r["row_id"]: r for r in rows}


def _val(row, col):
    c = row["cells"].get(col) or {}
    v = c.get("final_value")
    return c.get("ai_value") if v is None else v


def _num(v):
    return None if v in (None, "") else float(str(v).replace(",", ""))


def _expected(row):
    cargo = str(_val(row, C_CARGO) or "").replace("-", "")
    return (
        str(_val(row, C_NAME_KO) or ""),
        _num(_val(row, C_CARTONS)),
        _num(_val(row, C_PRICE)),
        cargo[:11],
    )


def _actual(r):
    # 머리글 순서: 제품명, 한글명, 대표품목, 수량, 순중량, 과세가격, 화물관리번호1·2·3 …
    return (str(r[1] or ""), _num(r[3]), _num(r[5]), str(r[6] or ""))


def test_each_declaration_file_has_exactly_its_rows(client):  # noqa: F811
    decls = {d["declaration_id"]: d for d in _upload_a(client)}
    rows = _rows(client)
    out = client.post("/api/judge/item-sheet/bulk", json={"shipper_id": "A"}).json()
    zf = zipfile.ZipFile(
        BytesIO(client.get(f"/api/judge/item-sheet/bulk/{out['file_id']}").content)
    )
    assert out["included"], "품목사항을 만들 수 있는 신고건이 있어야 시험이 된다"
    for x in out["included"]:
        ws = load_workbook(BytesIO(zf.read(x["filename"]))).active
        body = [r for r in ws.iter_rows(min_row=2, values_only=True) if any(r)]
        want = [_expected(rows[rid]) for rid in decls[x["declaration_id"]]["row_ids"]]
        assert [_actual(r) for r in body] == want  # 같은 행, 같은 순서, 같은 값
        assert [r[2] for r in body] == ["Y"] + ["N"] * (len(body) - 1)  # 첫 행만 대표품목


def test_picked_declarations_only(client):  # noqa: F811
    decls = _upload_a(client)
    pick = decls[0]["declaration_id"]
    out = client.post(
        "/api/judge/item-sheet/bulk", json={"shipper_id": "A", "declaration_ids": [pick]}
    ).json()
    got = {x["declaration_id"] for x in out["included"] + out["excluded"]}
    assert got == {pick}
