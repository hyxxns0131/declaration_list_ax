"""재질 구분이 같은 실적만(same_record_same_spec). 순수 함수. 담당: LSY [재사용] A3-2 (기존 spec_filter)

RULES 11-8: 재질 구분(11-5)이 다른 실적은 건너뛴다. 비교는 정리한 형식으로(spec_class/parse.same_spec —
순서·단위 차이는 같은 구분). 실적 쪽 구분 기록이 없으면 건너뛰지 않고 "같은 구분인지 확인 필요".
"""

from app.a3_judge.spec_class.parse import same_spec


def spec_ok(record_spec: str, row_spec: str, enabled: bool = True) -> bool:
    """이 실적을 재질 구분 때문에 빼야 하면 False. 꺼져 있거나 한쪽 기록이 없으면 True."""
    if not (enabled and row_spec and record_spec):
        return True
    return same_spec(record_spec, row_spec)


def split_by_spec(items: list, row_spec: str, spec_of) -> tuple[list, list, bool]:
    """(남길 것, 건너뛴 것, 실적 쪽 구분 기록 없는 것이 남았는지). spec_of(item) → 실적 재질 구분."""
    kept = [x for x in items if spec_ok(spec_of(x), row_spec)]
    skipped = [x for x in items if x not in kept]
    return kept, skipped, any(not spec_of(x) for x in kept)
