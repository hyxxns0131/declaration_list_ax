"""유니패스 가짜 응답: samples/unipass/<B/L>.json. 가상·비식별 자료만 둔다. 담당: KHS"""

import json
import re

from app.core.config import REPO_ROOT

MOCK_DIR = REPO_ROOT / "samples" / "unipass"


def cargo(bl_no: str) -> dict | None:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", bl_no)
    path = MOCK_DIR / f"{safe}.json"
    if not safe or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
