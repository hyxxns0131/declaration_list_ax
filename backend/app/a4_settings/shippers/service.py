"""화주 설정 조회·저장·추가. 담당: JUJ [개선] A4-1 (기존 CompanyRules 코드 → rules/*.json 설정)

- 규칙 목록·설명: rules/catalog.json. 기본값: rules/default.json. 화주 값: rules/shippers/<id>.json(기본과 다른 키만).
- 저장 전 검증: 모르는 키는 거절. group_by_maker는 끌 수 없다. 화주 id는 영문·숫자만(가명).
- 공통(기본)과 다르게 켠 '예외' 스위치는 exceptions[]에 키·이유·근거·시작 시점을 남긴다(RULES 11-12).
- 새 화주 = default.json 복사 + 이름. 코드 수정 없이 추가된다.
"""

import json
import re
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.a4_settings.engine.service import RULES_DIR, get_rules
from app.core.errors import AppError
from app.core.schema.shipper import ShipperSettings
from app.core.storage import local_db

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,20}$")


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
        if t in ("multi", "order", "select"):
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


def create_shipper(
    shipper_id: str, display_name: str, required_docs: list[str] | None, rules_dir: Path = RULES_DIR
) -> dict:
    path = _path(shipper_id, rules_dir)
    if path.exists():
        raise AppError("exists", f"화주 {shipper_id}이(가) 이미 있습니다.", 409)
    if not display_name.strip():
        raise AppError("invalid_input", "화주 이름(가명)을 적어 주세요.")
    data: dict = {"shipper_id": shipper_id, "display_name": display_name.strip()}
    if required_docs is not None:
        data["required_docs"] = required_docs
    validate(data, rules_dir)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local_db.audit("shipper_create", shipper_id, date.today().isoformat())
    return get_shipper(shipper_id, rules_dir)
