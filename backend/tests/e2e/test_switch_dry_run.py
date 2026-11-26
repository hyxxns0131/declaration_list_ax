"""기업 설정 → 시험 실행(dry-run)에서 스위치를 바꾸면 결과가 바뀌는지: 가상 화주 A·B 샘플 서류로. 담당: KHS"""

from tests.e2e.test_p0_flow import client  # noqa: F401


def _run(client, sid: str, values: dict) -> dict:  # noqa: F811
    r = client.post(f"/api/settings/shippers/{sid}/dry-run", json={"settings": values})
    assert r.status_code == 200, r.text
    return r.json()


def test_sort_by_changes_dry_run(client):  # noqa: F811
    out = _run(client, "A", {"sort_by": ["model"]})
    before = [x for d in out["before"] for x in d["rows"]]
    after = [x for d in out["after"] for x in d["rows"]]
    assert sorted(before) == sorted(after)
    assert any(c["key"] == "sort_by" for c in out["changed"])
    assert after == sorted(after, key=lambda s: s.split(" ")[0])  # 모델 순


def test_product_name_switch_changes_rows(client):  # noqa: F811
    out = _run(client, "A", {"product_name_with_model": False})
    assert any(c["key"] == "product_name_with_model" for c in out["changed"])
