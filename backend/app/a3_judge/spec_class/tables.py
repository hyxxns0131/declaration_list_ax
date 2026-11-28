"""구분표(공전 총칙 3.자) — 구분 기준 수치 읽기·적용. 순수 함수. 담당: LSY [개선] A3-1

기준 수치는 코드에 쓰지 않는다(RULES 11-5, AGENTS 0-5). 화주 설정의 `spec_class_table` 키에서 읽는다.
지금 rules/default.json에는 이 키가 없다 → 구분 이름을 자동으로 붙이지 않고 입력값만 정리한다.
키 추가는 JUJ(rules 담당)에게 요청(제안). 수치는 공전 최신본에서 옮겨야 한다 — 최신본 확인 필요(확인 필요 7).

형식(제안): {"도자기제": [{"label": "...", "depth_min_cm": 2.5, "volume_max_ml": 1100,
                          "heat": true|false|null, "flat": true|false|null}, ...], ...}
행마다 적힌 조건만 본다(없는 조건은 상관없음). 위에서부터 처음 맞는 행의 label.
"""

from app.a3_judge.spec_class.parse import SpecInput

RULE_KEY = "spec_class_table"


def _hit(cond: dict, s: SpecInput) -> bool | None:
    """True/False, 판단에 필요한 입력이 없으면 None."""
    # 평판·가열조리용은 적지 않으면 '아님'으로 본다(RULES 11-5 적는 법: 적힌 것만 해당)
    for key, got in (("flat", bool(s.flat)), ("heat", bool(s.heat))):
        if cond.get(key) is not None and cond[key] != got:
            return False
    for key, value, op in (
        ("depth_min_cm", s.depth_cm, "min"),
        ("depth_max_cm", s.depth_cm, "max"),
        ("volume_min_ml", s.volume_ml, "min"),
        ("volume_max_ml", s.volume_ml, "max"),
    ):
        if key not in cond or cond[key] is None:
            continue
        if value is None:
            return None
        limit = float(cond[key])
        if (op == "min" and value < limit) or (op == "max" and value >= limit):
            return False
    return True


def lookup(family: str, spec: SpecInput, table: dict | None) -> tuple[str | None, str]:
    """(구분 이름 또는 None, 메모). 표가 없거나 그 재질 행이 없으면 None."""
    rows = (table or {}).get(family) or []
    if not rows:
        return None, "구분표 설정 없음(spec_class_table) — 입력값만 정리"
    for row in rows:
        hit = _hit(row, spec)
        if hit is None:
            return None, "구분표에 필요한 입력이 모자람"
        if hit:
            return str(row.get("label", "")), "구분표(spec_class_table) 기준 — 최신본 확인 필요"
    return None, "구분표에 맞는 행 없음 — 확인 필요"
