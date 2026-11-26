"""선적 건 묶기(B/L 번호), 빠진 서류 표시, B/L 번호 오타 서류도 같은 선적 건. 가상 샘플 A만. (검역 리스트 탭 1단계)"""

from tests.e2e.test_p0_flow import SAMPLES, _files, client  # noqa: F401


def _up(client, name: str) -> dict:  # noqa: F811
    r = client.post(
        "/api/reader/upload", data={"shipper_id": "A"}, files=_files(SAMPLES / "A" / name)
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_shipments_grouping(client):  # noqa: F811
    for n in ("BL-TEST-003", "BL-TEST-005", "BL-TEST-006"):
        _up(client, n)
    ships = client.get("/api/reader/shipments", params={"shipper_id": "A"}).json()
    by_bl = {s["bl_no"]: s for s in ships}
    assert (
        set(by_bl["BLTEST003"]["documents"]) >= {"CI", "PL", "BL"}
        and by_bl["BLTEST003"]["missing"] == []
    )
    no_bl = by_bl["BLTEST005"]
    assert no_bl["missing"] == ["BL"] and "B/L 자료 추가 필요" in no_bl["missing_marks"]
    typo = by_bl["BLTEST006"]  # PL의 B/L 번호가 오타여도 폴더 1개 = 선적 1건
    assert set(typo["documents"]) >= {"CI", "PL", "BL"}
    assert typo["documents"]["PL"]["values"]["bl_no"] == "BLTEST0O6"
    assert len([s for s in ships if s["bl_no"].startswith("BLTEST00")]) == 3
