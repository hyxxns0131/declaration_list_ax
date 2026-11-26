"""화주 설정 조회·저장·추가. 담당: JUJ [개선] A4-1 (기존 CompanyRules 코드 → rules/*.json 설정)

- 규칙 목록·설명: rules/catalog.json. 기본값: rules/default.json. 화주 값: rules/shippers/<id>.json(기본과 다른 키만).
- 저장 전 검증: 모르는 키는 거절. group_by_maker는 끌 수 없다. 화주 id는 영문·숫자만(가명).
- 공통(기본)과 다르게 켠 '예외' 스위치는 exceptions[]에 키·이유·근거·시작 시점을 남긴다(RULES 11-12).
- 새 화주 = 통관고유부호 + 화주 별칭만 받는다. 내부 id(S0003…)는 자동 생성, 규칙은 default.json 그대로(A4-1 개편 11/26).
  통관고유부호는 DATA_DIR/shipper_registry.json에만 저장하고 규칙 파일·파일명·로그·audit·오류 문구에 쓰지 않는다.
- 화주 삭제(HS 요청 11/25): 기본 화주 A·B는 지울 수 없다. 지우지 않고 DATA_DIR/deleted_shippers/<id>-<시각>.json으로 옮겨 둔다.
"""

import copy
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path

from pydantic import ValidationError

from app.a4_settings.engine.service import RULES_DIR, get_rules
from app.a4_settings.shippers import identity, registry
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schema.shipper import ShipperSettings
from app.core.storage import local_db

log = logging.getLogger(__name__)

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
DEFAULT_SHIPPERS = frozenset({"A", "B"})  # 기본 화주: 삭제 불가 (HS 요청 11/25)

# 중복·삭제 사유 코드 (형식 사유는 identity.py)
DUPLICATE = "duplicate"
DELETED_CODE = "deleted_code"  # 삭제된 화주의 부호: 재등록 정책 확정 전까지 막음(PM·SAMC 확인 필요)

# 서버 문구. 입력값(특히 통관고유부호)은 넣지 않는다.
CODE_MESSAGES = {
    identity.REQUIRED: "통관고유부호를 입력해 주세요.",
    identity.FORMAT: "통관고유부호 형식이 맞지 않습니다.",
    identity.PROD_TEST_BLOCKED: "운영 환경에서는 가상(TEST) 부호를 등록할 수 없습니다.",
    identity.PROD_NOT_READY: "실제 통관고유부호 형식이 확정되기 전이라 운영 환경에서는 등록할 수 없습니다.",
    DUPLICATE: "이미 등록된 통관고유부호입니다.",
    DELETED_CODE: "삭제된 화주의 통관고유부호입니다. 관리자 확인이 필요합니다.",
}
ALIAS_MESSAGES = {
    identity.REQUIRED: "화주 별칭을 입력해 주세요.",
    identity.FORMAT: "화주 별칭은 영문 알파벳 1~3자로 적어 주세요.",
    DUPLICATE: "이미 등록된 별칭입니다.",
}


def catalog(rules_dir: Path = RULES_DIR) -> dict:
    return json.loads((rules_dir / "catalog.json").read_text(encoding="utf-8"))


def default(rules_dir: Path = RULES_DIR) -> dict:
    return json.loads((rules_dir / "default.json").read_text(encoding="utf-8"))


def rule_index(cat: dict) -> dict[str, dict]:
    return {r["key"]: r for g in cat["groups"] for r in g["rules"]}


def known_keys(cat: dict) -> set[str]:
    return set(rule_index(cat)) | set(cat.get("meta_keys", []))


def _path(shipper_id: str, rules_dir: Path) -> Path:
    if not ID_RE.match(shipper_id):
        raise AppError("invalid_input", "화주 id는 영문·숫자 20자 이내(가명)로 정하세요.")
    return rules_dir / "shippers" / f"{shipper_id}.json"


def list_shippers(rules_dir: Path = RULES_DIR) -> list[dict]:
    out = []
    for p in sorted((rules_dir / "shippers").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out.append(
            {
                "shipper_id": d.get("shipper_id", p.stem),
                "display_name": d.get("display_name", p.stem),
            }
        )
    return out


def get_shipper(shipper_id: str, rules_dir: Path = RULES_DIR) -> dict:
    path = _path(shipper_id, rules_dir)
    if not path.exists():
        raise AppError("not_found", f"화주 {shipper_id} 설정이 없습니다.", 404)
    merged = get_rules(shipper_id, rules_dir).model_dump()
    base = default(rules_dir)
    diff = sorted(
        k for k in rule_index(catalog(rules_dir)) if k in merged and merged.get(k) != base.get(k)
    )
    return {"settings": merged, "differs_from_default": diff, "default": base}


def validate(data: dict, rules_dir: Path = RULES_DIR) -> ShipperSettings:
    cat = catalog(rules_dir)
    unknown = set(data) - known_keys(cat)
    if unknown:
        raise AppError("unknown_key", f"모르는 설정 키: {', '.join(sorted(unknown))}")
    idx = rule_index(cat)
    for key, value in data.items():
        r = idx.get(key)
        if not r:
            continue
        t = r["type"]
        if t == "bool" and not isinstance(value, bool):
            raise AppError("invalid_input", f"{r['label']}: 켬/끔 값이어야 합니다.")
        if t == "int" and value is not None and (not isinstance(value, int) or value < 1):
            raise AppError("invalid_input", f"{r['label']}: 1 이상 숫자이거나 비워 두세요.")
        if t in ("multi", "order") and not isinstance(value, list):
            raise AppError("invalid_input", f"{r['label']}: 목록이어야 합니다.")
        if t == "select_list" and not isinstance(value, list):
            raise AppError("invalid_input", f"{r['label']}: 목록이어야 합니다.")
        if t in ("multi", "order", "select", "select_list"):
            allowed = {o["value"] for o in r.get("options", [])}
            vals = value if isinstance(value, list) else [value]
            bad = [v for v in vals if v not in allowed]
            if bad:
                raise AppError("invalid_input", f"{r['label']}: 고를 수 없는 값 {bad}")
    if data.get("group_by_maker") is False:
        raise AppError("invalid_input", "제조사가 같아야 같은 신고는 공통 규칙이라 끌 수 없습니다.")
    for ex in data.get("exceptions", []) or []:
        if not isinstance(ex, dict) or not ex.get("key") or not ex.get("reason"):
            raise AppError("invalid_input", "예외에는 키와 이유가 있어야 합니다(RULES 11-12).")
    try:
        merged = {**default(rules_dir), **data}
        merged["group_by_maker"] = True
        return ShipperSettings.model_validate(merged)
    except ValidationError:
        raise AppError("invalid_input", "설정 값을 확인해 주세요.") from None


def _exceptions_check(data: dict, rules_dir: Path) -> None:
    """예외 스위치(catalog exception=true)를 기본과 다르게 켰으면 이유가 있어야 한다."""
    cat, base = catalog(rules_dir), default(rules_dir)
    keys = {e.get("key") for e in data.get("exceptions", []) or []}
    for key, r in rule_index(cat).items():
        if r.get("exception") and key in data and data[key] != base.get(key) and key not in keys:
            raise AppError(
                "reason_required",
                f"'{r['label']}'은(는) 화주 요청 예외입니다. 켜는 이유를 적어 주세요.",
            )


def save_shipper(shipper_id: str, data: dict, rules_dir: Path = RULES_DIR) -> dict:
    path = _path(shipper_id, rules_dir)
    if not path.exists():
        raise AppError("not_found", f"화주 {shipper_id} 설정이 없습니다.", 404)
    data = {k: v for k, v in data.items() if k != "group_by_maker"}
    data["shipper_id"] = shipper_id
    validate(data, rules_dir)
    _exceptions_check(data, rules_dir)
    base = default(rules_dir)
    # 기본과 같은 키는 적지 않는다(화주 파일 = 다른 점만). 이름·id·예외는 항상 적는다
    keep = {
        k: v
        for k, v in data.items()
        if k in ("shipper_id", "display_name", "exceptions", "mask_names") or base.get(k) != v
    }
    if "display_name" not in keep:
        keep["display_name"] = json.loads(path.read_text(encoding="utf-8")).get(
            "display_name", shipper_id
        )
    path.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local_db.audit("settings_save", shipper_id, ",".join(sorted(keep)))
    return get_shipper(shipper_id, rules_dir)


# ── 신규 화주 등록 (통관고유부호 + 화주 별칭, A4-1 개편 11/26) ──


def code_config(rules_dir: Path = RULES_DIR) -> dict:
    return json.loads((rules_dir / "customs_code.json").read_text(encoding="utf-8"))


def _is_dev(cfg: dict) -> bool:
    return identity.is_dev(get_settings().app_env, cfg)


def _backup_dir() -> Path:
    return get_settings().data_path / "deleted_shippers"


def _used_seqs(data: dict, rules_dir: Path, prefix: str) -> list[int]:
    """이미 쓴 순번: 등록부·살아 있는 규칙 파일·삭제 백업. 삭제된 id를 다시 쓰지 않기 위해."""
    names = list(data["shippers"])
    names += [p.stem for p in (rules_dir / "shippers").glob("*.json")]
    if _backup_dir().exists():
        names += [p.stem.split("-")[0] for p in _backup_dir().glob("*.json")]
    seqs = [s for s in (identity.parse_seq(n, prefix) for n in names) if s is not None]
    return [*seqs, int(data.get("last_seq", 0))]


def _taken(data: dict, cfg: dict, dev: bool, rules_dir: Path) -> tuple[set, set, set]:
    """(쓰는 중인 부호, 삭제된 화주의 부호, 쓰는 중인 별칭)."""
    shippers_dir = rules_dir / "shippers"
    codes: set[str] = set()
    deleted: set[str] = set()
    aliases: set[str] = set()
    reg = data["shippers"]
    for sid, e in reg.items():
        status = e.get("status")
        live = status == registry.PENDING or (
            status == registry.ACTIVE and (shippers_dir / f"{sid}.json").exists()
        )
        if live:
            codes.add(e["customs_code"])
            aliases.add(e["alias"])
        elif status == registry.DELETED:
            deleted.add(e["customs_code"])
    # 기본 화주 가상 부호(seed). 등록부에 같은 id가 있으면 등록부가 우선(실제 부호 전환 대비, 전환 기능은 범위 밖)
    for sid, s in cfg.get("seed", {}).items():
        if sid in reg:
            continue
        aliases.add(s["alias"])
        if dev:  # 운영 환경에서는 가상 부호를 중복 대상으로 보지 않는다(어차피 TEST 차단)
            codes.add(s["customs_code"])
    # 등록부에 없는 기존 규칙 파일(예전 방식으로 만든 화주)의 id·이름도 별칭으로 예약
    for p in shippers_dir.glob("*.json"):
        if p.stem in reg:
            continue
        aliases.add(p.stem.upper())
        name = json.loads(p.read_text(encoding="utf-8")).get("display_name", "")
        aliases.add(str(name).strip().upper())
    return codes, deleted, aliases


def _judge(
    code: str, alias: str, data: dict, cfg: dict, dev: bool, rules_dir: Path
) -> tuple[str | None, str | None]:
    """형식 → 중복 순서로 사유 코드를 돌려준다(문제 없으면 None)."""
    code_reason = identity.check_code_format(code, dev, cfg)
    alias_reason = identity.check_alias_format(alias, cfg)
    codes, deleted, aliases = _taken(data, cfg, dev, rules_dir)
    if code_reason is None:
        if code in codes:
            code_reason = DUPLICATE
        elif code in deleted:
            code_reason = DELETED_CODE
    if alias_reason is None and alias in aliases:
        alias_reason = DUPLICATE
    return code_reason, alias_reason


def _field(reason: str | None, messages: dict) -> dict:
    return {
        "ok": reason is None,
        "reason": reason,
        "message": messages.get(reason, "") if reason else "",
    }


def check_new_shipper(customs_code: str, alias: str, rules_dir: Path = RULES_DIR) -> dict:
    """화면의 미리 검사(잠금 없이 읽기만). 최종 판단은 create_shipper의 재검사. 응답에 부호를 넣지 않는다."""
    cfg = code_config(rules_dir)
    dev = _is_dev(cfg)
    data = registry.load()
    registry.reconcile(
        data, rules_dir / "shippers"
    )  # 메모리에서만 정리(저장은 create가 잠금 안에서)
    cr, ar = _judge(
        identity.normalize_code(customs_code),
        identity.normalize_alias(alias),
        data,
        cfg,
        dev,
        rules_dir,
    )
    return {
        "mode": "dev" if dev else "prod",
        "code": _field(cr, CODE_MESSAGES),
        "alias": _field(ar, ALIAS_MESSAGES),
    }


def _raise_reasons(cr: str | None, ar: str | None) -> None:
    if cr is None and ar is None:
        return
    duplicate = {DUPLICATE, DELETED_CODE}
    status = 409 if (cr in duplicate or ar in duplicate) else 400
    msgs = [m for m in (CODE_MESSAGES.get(cr or ""), ALIAS_MESSAGES.get(ar or "")) if m]
    raise AppError("exists" if status == 409 else "invalid_input", " ".join(msgs), status)


def create_shipper(customs_code: str, alias: str, rules_dir: Path = RULES_DIR) -> dict:
    """신규 화주 등록. 순서(계획 v3 3장): 정규화·형식 → 잠금 → 정리 → 중복 재검사 → id 생성
    → 등록부 pending → 규칙 파일(배타 생성) → 등록부 active. 중간 실패는 이전 상태로 되돌린다."""
    cfg = code_config(rules_dir)
    dev = _is_dev(cfg)
    code = identity.normalize_code(customs_code)
    al = identity.normalize_alias(alias)
    _raise_reasons(identity.check_code_format(code, dev, cfg), identity.check_alias_format(al, cfg))

    shippers_dir = rules_dir / "shippers"
    prefix = cfg.get("id_prefix", "S")
    try:
        with registry.locked():
            data = registry.load()
            if registry.reconcile(data, shippers_dir):
                registry.save(data)
            _raise_reasons(*_judge(code, al, data, cfg, dev, rules_dir))

            sid = identity.next_shipper_id(
                _used_seqs(data, rules_dir, prefix), prefix, int(cfg.get("id_digits", 4))
            )
            before = copy.deepcopy(data)
            data["last_seq"] = identity.parse_seq(sid, prefix)
            data["shippers"][sid] = {
                "alias": al,
                "customs_code": code,
                "status": registry.PENDING,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            registry.save(data)

            path = shippers_dir / f"{sid}.json"
            created = False
            try:
                body = {"shipper_id": sid, "display_name": identity.display_name(al)}
                validate(body, rules_dir)  # 나머지 규칙은 default.json이 채운다(부호는 쓰지 않음)
                with open(path, "x", encoding="utf-8") as f:
                    created = True
                    f.write(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
                data["shippers"][sid]["status"] = registry.ACTIVE
                registry.save(data)
            except Exception as e:
                if created:
                    path.unlink(missing_ok=True)
                try:
                    registry.save(before)
                except Exception:  # 되돌리기 실패 → 다음 등록 때 reconcile이 pending을 정리
                    log.warning("shipper registry rollback failed: %s", sid)
                if isinstance(e, AppError):
                    raise
                raise AppError(
                    "save_failed",
                    "저장에 실패해 이전 상태로 되돌렸습니다. 다시 시도해 주세요.",
                    500,
                ) from None
    except registry.LockTimeout:
        raise AppError(
            "busy", "다른 등록이 진행 중입니다. 잠시 후 다시 시도해 주세요.", 503
        ) from None

    try:
        local_db.audit(
            "shipper_create", sid, date.today().isoformat()
        )  # id만, 부호·별칭은 남기지 않음
    except Exception:
        log.warning("audit failed: shipper_create %s", sid)
    return get_shipper(sid, rules_dir)


def delete_shipper(shipper_id: str, rules_dir: Path = RULES_DIR) -> dict:
    """화주 설정 파일을 지우지 않고 DATA_DIR/deleted_shippers/로 옮긴다(되살릴 수 있게). 기본 화주는 거절.
    등록부 항목은 지우지 않고 deleted로 표시한다(부호 재등록 정책은 PM·SAMC 확인 필요)."""
    if shipper_id.upper() in DEFAULT_SHIPPERS:
        raise AppError("default_shipper", "기본 화주(A사·B사)는 삭제할 수 없습니다.", 409)
    path = _path(shipper_id, rules_dir)
    if not path.exists():
        raise AppError("not_found", f"화주 {shipper_id} 설정이 없습니다.", 404)
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"{shipper_id}-{stamp}.json"
    try:
        with registry.locked():
            path.replace(backup)
            data = registry.load()
            entry = data["shippers"].get(shipper_id)
            if entry is not None:
                entry["status"] = registry.DELETED
                entry["deleted_at"] = datetime.now().isoformat(timespec="seconds")
                registry.save(data)
    except registry.LockTimeout:
        raise AppError(
            "busy", "다른 작업이 진행 중입니다. 잠시 후 다시 시도해 주세요.", 503
        ) from None
    local_db.audit("shipper_delete", shipper_id, backup.name)
    return {"ok": True, "shipper_id": shipper_id, "backup": backup.name}
