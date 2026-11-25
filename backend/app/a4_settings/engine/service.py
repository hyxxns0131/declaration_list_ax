"""화주 설정 → A1·A3에 주입: get_rules(shipper_id). 담당: JUJ [신규] A4-2

rules/default.json(공통 기본값) 위에 rules/shippers/<id>.json(화주별 스위치)을 덮어 쓴다.
등록 안 된 화주는 공통 기본값으로 시작한다(RULES 11-9 '새 화주 기본값').
코드에 화주 이름을 쓰지 않는다(AGENTS 원칙 2).
"""

import json
import re
from pathlib import Path

from app.core.config import REPO_ROOT
from app.core.schema.shipper import ShipperSettings

RULES_DIR = REPO_ROOT / "backend" / "rules"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def merge_rules(default: dict, shipper: dict, shipper_id: str) -> ShipperSettings:
    """순수 함수: 기본값 + 화주 값 → ShipperSettings. group_by_maker는 끌 수 없다(RULES 11-6)."""
    data = {**default, **shipper}
    data["shipper_id"] = shipper.get("shipper_id", shipper_id)
    data["display_name"] = shipper.get("display_name", shipper_id)
    data["group_by_maker"] = True
    return ShipperSettings.model_validate(data)


def get_rules(shipper_id: str, rules_dir: Path = RULES_DIR) -> ShipperSettings:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", shipper_id)
    default = _load(rules_dir / "default.json")
    shipper = _load(rules_dir / "shippers" / f"{safe}.json") if safe else {}
    return merge_rules(default, shipper, shipper_id)


def rule(settings: ShipperSettings, key: str, fallback: object = None) -> object:
    """스위치 값 읽기(ShipperSettings에 선언 안 된 키도 extra로 들어 있다)."""
    return getattr(settings, key, fallback)
