"""신규 화주 등록(통관고유부호 + 별칭): 검증·중복·id 생성·동시성·복구·환경·노출.
임시 규칙 폴더와 임시 DATA_DIR만 쓴다. 가상 TEST 부호만 쓴다(실제 부호·기업명 금지)."""

import functools
import hashlib
import json
import shutil
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from app.a4_settings.engine.service import RULES_DIR, get_rules
from app.a4_settings.router import NewShipper
from app.a4_settings.shippers import registry, service
from app.core.errors import AppError


def _hash(name: str) -> str:
    return hashlib.sha256((RULES_DIR / "shippers" / name).read_bytes()).hexdigest()


REAL_AB = {n: _hash(n) for n in ("A.json", "B.json")}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOCAL_DB_PATH", str(tmp_path / "t.db"))
    from app.core.config import get_settings
    from app.core.storage import local_db

    get_settings.cache_clear()
    local_db.migrate()
    d = tmp_path / "rules"
    (d / "shippers").mkdir(parents=True)
    for name in ("catalog.json", "default.json", "customs_code.json"):
        shutil.copy(RULES_DIR / name, d / name)
    for name in ("A.json", "B.json"):
        shutil.copy(RULES_DIR / "shippers" / name, d / "shippers" / name)
    yield d
    get_settings.cache_clear()


def _set_env(monkeypatch, value):
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", value)
    get_settings.cache_clear()


def _err(fn, *args) -> AppError:
    with pytest.raises(AppError) as e:
        fn(*args)
    return e.value


def test_register_ok(env):
    out = service.create_shipper("TEST000000003", "C", env)
    sid = out["settings"]["shipper_id"]
    assert sid == "S0003" and out["settings"]["display_name"] == "C사"
    body = json.loads((env / "shippers" / f"{sid}.json").read_text(encoding="utf-8"))
    assert body == {"shipper_id": "S0003", "display_name": "C사"}  # 부호 없음, 나머지는 default
    entry = registry.load()["shippers"][sid]
    assert entry["status"] == registry.ACTIVE and entry["customs_code"] == "TEST000000003"
    assert [s["display_name"] for s in service.list_shippers(env)][-1] == "C사"


def test_default_rules_applied(env):
    sid = service.create_shipper("TEST000000003", "C", env)["settings"]["shipper_id"]
    got = get_rules(sid, env).model_dump()
    base = service.default(env)
    for key in service.rule_index(service.catalog(env)):
        if key in base:
            assert got[key] == base[key], key


@pytest.mark.parametrize(
    "code,alias",
    [
        ("", "C"),
        ("TEST000000003", ""),
        ("TEST00000003", "C"),
        ("TEST0000000031", "C"),
        ("ABCD000000003", "C"),
        ("TEST000000003", "C1"),
        ("TEST000000003", "씨"),
        ("TEST000000003", "ABCD"),
        ("TEST000000003", "C사"),
    ],
)
def test_bad_input_400(env, code, alias):
    e = _err(service.create_shipper, code, alias, env)
    assert e.status == 400
    assert not list((env / "shippers").glob("S*.json"))


def test_duplicate_code_409(env):
    assert _err(service.create_shipper, "TEST000000001", "C", env).status == 409  # A사 가상 부호
    service.create_shipper("TEST000000003", "C", env)
    e = _err(service.create_shipper, "TEST000000003", "D", env)
    assert e.status == 409 and e.message == "이미 등록된 통관고유부호입니다."


@pytest.mark.parametrize("alias", ["A", "B", "C", "c", " c "])
def test_duplicate_alias_409(env, alias):
    service.create_shipper("TEST000000003", "C", env)
    e = _err(service.create_shipper, "TEST000000004", alias, env)
    assert e.status == 409 and "이미 등록된 별칭" in e.message


def test_normalize_and_extended_alias(env):
    out = service.create_shipper("  test000000004 ", " d ", env)
    sid = out["settings"]["shipper_id"]
    assert registry.load()["shippers"][sid]["customs_code"] == "TEST000000004"
    assert out["settings"]["display_name"] == "D사"
    assert service.create_shipper("TEST000000005", "aa", env)["settings"]["display_name"] == "AA사"
    assert service.create_shipper("TEST000000006", "AB", env)["settings"]["display_name"] == "AB사"


def test_ids_auto_and_not_reused(env, tmp_path):
    s3 = service.create_shipper("TEST000000003", "C", env)["settings"]["shipper_id"]
    s4 = service.create_shipper("TEST000000004", "D", env)["settings"]["shipper_id"]
    assert (s3, s4) == ("S0003", "S0004")
    service.delete_shipper(s3, env)
    assert service.create_shipper("TEST000000005", "E", env)["settings"]["shipper_id"] == "S0005"
    # 등록부가 사라져도 규칙 파일·삭제 백업 이름으로 순번을 이어 간다
    registry.registry_path().unlink()
    assert service.create_shipper("TEST000000006", "F", env)["settings"]["shipper_id"] == "S0006"
    assert not any("TEST" in p.name for p in (env / "shippers").iterdir())


def test_deleted_code_blocked_alias_reusable(env):
    sid = service.create_shipper("TEST000000003", "C", env)["settings"]["shipper_id"]
    service.delete_shipper(sid, env)
    assert registry.load()["shippers"][sid]["status"] == registry.DELETED
    e = _err(service.create_shipper, "TEST000000003", "C", env)
    assert e.status == 409 and "삭제된 화주" in e.message
    assert service.create_shipper("TEST000000007", "C", env)["settings"]["display_name"] == "C사"


def test_concurrent_same_code(env):
    aliases = ["C", "D", "E", "F", "G", "H", "I", "J"]

    def go(alias):
        try:
            service.create_shipper("TEST000000003", alias, env)
            return 200
        except AppError as e:
            return e.status

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(go, aliases))
    assert results.count(200) == 1 and results.count(409) == 7
    assert len(list((env / "shippers").glob("S*.json"))) == 1


def test_save_failure_rolls_back(env, monkeypatch):
    service.create_shipper("TEST000000003", "C", env)
    before = registry.load()
    real_save = registry.save
    calls = {"n": 0}

    def flaky(data):
        calls["n"] += 1
        if calls["n"] == 2:  # pending 저장 다음, active 저장에서 실패
            raise OSError("disk")
        real_save(data)

    monkeypatch.setattr(registry, "save", flaky)
    e = _err(service.create_shipper, "TEST000000004", "D", env)
    assert e.status == 500
    assert not (env / "shippers" / "S0004.json").exists()
    assert registry.load() == before


def test_reconcile_after_crash(env):
    (env / "shippers" / "S0003.json").write_text(
        json.dumps({"shipper_id": "S0003", "display_name": "C사"}), encoding="utf-8"
    )
    registry.save(
        {
            "version": 1,
            "last_seq": 4,
            "shippers": {
                "S0003": {"alias": "C", "customs_code": "TEST000000003", "status": "pending"},
                "S0004": {"alias": "D", "customs_code": "TEST000000004", "status": "pending"},
            },
        }
    )
    assert _err(service.create_shipper, "TEST000000003", "X", env).status == 409  # 살아난 C사
    sid = service.create_shipper("TEST000000004", "D", env)["settings"]["shipper_id"]
    data = registry.load()["shippers"]
    assert data["S0003"]["status"] == registry.ACTIVE
    assert data["S0004"]["status"] == registry.ABANDONED
    assert sid == "S0005"  # 버려진 S0004도 재사용하지 않음


def test_lock_wait_and_timeout(env, monkeypatch):
    held, release = threading.Event(), threading.Event()

    def hold():
        with registry.locked():
            held.set()
            release.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    held.wait(5)
    monkeypatch.setattr(registry, "locked", functools.partial(registry.locked, timeout=0.2))
    assert _err(service.create_shipper, "TEST000000003", "C", env).status == 503
    release.set()
    t.join()
    assert service.create_shipper("TEST000000003", "C", env)["settings"]["shipper_id"] == "S0003"
    assert (
        registry.registry_path().parent / registry.LOCK_NAME
    ).exists()  # 잠금 파일은 지우지 않음


def test_env_dev_and_prod(env, monkeypatch):
    _set_env(monkeypatch, "demo")
    assert service.create_shipper("TEST000000003", "C", env)["settings"]["shipper_id"] == "S0003"
    _set_env(monkeypatch, "prod")
    e = _err(service.create_shipper, "TEST000000004", "D", env)
    assert e.status == 400 and "가상(TEST)" in e.message
    e = _err(service.create_shipper, "ABCDE1234567890", "D", env)
    assert e.status == 400 and "확정되기 전" in e.message
    assert service.check_new_shipper("TEST000000004", "D", env)["mode"] == "prod"


def test_check_api(env):
    ok = service.check_new_shipper("TEST000000003", "C", env)
    assert ok == {
        "mode": "dev",
        "code": {"ok": True, "reason": None, "message": ""},
        "alias": {"ok": True, "reason": None, "message": ""},
    }
    dup = service.check_new_shipper("test000000001", "a", env)
    assert dup["code"]["reason"] == "duplicate" and dup["alias"]["reason"] == "duplicate"
    assert not registry.registry_path().exists()  # 검사만으로는 저장하지 않음


def test_no_code_exposure(env, tmp_path):
    code = "TEST000000003"
    sid = service.create_shipper(code, "C", env)["settings"]["shipper_id"]
    texts = [
        json.dumps(service.list_shippers(env)),
        json.dumps(service.get_shipper(sid, env)),
        json.dumps(service.check_new_shipper(code, "D", env)),
        _err(service.create_shipper, code, "D", env).message,
        (env / "shippers" / f"{sid}.json").read_text(encoding="utf-8"),
    ]
    with sqlite3.connect(tmp_path / "t.db") as conn:
        texts += [
            " ".join(map(str, r))
            for r in conn.execute("select action, target, detail from audit_log")
        ]
    assert not any(code in t for t in texts)


def test_router_rejects_old_body():
    with pytest.raises(ValidationError):
        NewShipper.model_validate({"shipper_id": "C", "display_name": "C사"})


def test_real_ab_unchanged():
    assert {n: _hash(n) for n in REAL_AB} == REAL_AB
