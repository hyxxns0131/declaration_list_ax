"""다시 묶기 — 신고건 번호를 지킨다. 순수 함수. 담당: LSY [개선] A3-4 (기존 regroup.place_added)

담당자가 한 행의 재질·모델·제조사를 바꾸면 신고건을 다시 계산하는데, 그때마다 번호(A-D001…)가 새로 매겨지면
다른 신고건까지 번호가 바뀌어 헷갈린다. 그래서 **새로 계산한 묶음을 이전 묶음과 맞춰 번호를 이어받는다.**
- 행이 겹치는 이전 신고건의 번호를 쓴다. 같은 키를 먼저, 그다음 많이 겹치는 순 → 바뀐 행만 옮겨 가고 나머지 번호는 그대로.
  재질이 없던 행이 재질을 얻어 키가 바뀌어도(혼자 있던 신고건) 번호를 이어받는다.
- 새 행이 기존 묶음 키와 같으면 그 신고건에 들어간다(번호 유지, 기존 place_added와 같은 효과).
- 짝이 없는 새 묶음은 지금까지 쓴 가장 큰 번호 다음 번호(비었던 번호를 다시 쓰지 않음 → 지난 번호와 헷갈리지 않게).
"""

import re

from app.a3_judge.grouping.keys import key_tuple
from app.core.schema.declaration import Declaration

_NUM_RE = re.compile(r"-D(\d+)$")


def _num(declaration_id: str) -> int:
    m = _NUM_RE.search(declaration_id)
    return int(m.group(1)) if m else 0


def keep_ids(
    previous: list[Declaration], new: list[Declaration], shipper_id: str
) -> list[Declaration]:
    """new의 번호를 previous에 맞춘다. new 순서(화주 정렬)는 그대로."""
    pairs: list[tuple[bool, int, int, int]] = []  # (같은 키, 겹친 행 수, new 위치, previous 위치)
    for ni, n in enumerate(new):
        rows = set(n.row_ids)
        for pi, p in enumerate(previous):
            overlap = len(rows & set(p.row_ids))
            if overlap:
                pairs.append((key_tuple(p.key) == key_tuple(n.key), overlap, ni, pi))
    taken_new: dict[int, str] = {}
    taken_prev: set[int] = set()
    for _, _, ni, pi in sorted(pairs, key=lambda x: (not x[0], -x[1], x[2], x[3])):
        if ni in taken_new or pi in taken_prev:
            continue
        taken_new[ni] = previous[pi].declaration_id
        taken_prev.add(pi)
    next_no = max([_num(d.declaration_id) for d in previous] + [0]) + 1
    out: list[Declaration] = []
    for ni, n in enumerate(new):
        if ni in taken_new:
            did = taken_new[ni]
        else:
            did = f"{shipper_id}-D{next_no:03d}"
            next_no += 1
        out.append(n.model_copy(update={"declaration_id": did}))
    return out
