"""여러 행 판단(업로드·새로고침·설정 변경 후 재계산). 승인 행 제외. 담당: LSY

본품 행을 먼저 판단해, 같은 묶음의 부분품이 본품 결과를 이력처럼 쓸 수 있게 한다.
"""

from dataclasses import replace

from app.a3_judge.pipeline.context import JudgeContext
from app.a3_judge.pipeline.judge_row import judge_row
from app.core.schema.history import HistoryRow


def judge_rows(targets: list[HistoryRow], ctx: JudgeContext) -> list[HistoryRow]:
    """targets를 판단해 같은 순서로 돌려준다. ctx.history = 그 화주의 전체 행(표 순서)."""
    done: dict[str, HistoryRow] = {}
    for r in sorted(targets, key=lambda x: x.is_part):  # 본품 먼저
        cur = [done.get(h.row_id, h) for h in ctx.history]
        done[r.row_id] = judge_row(r, replace(ctx, history=cur))
    return [done[r.row_id] for r in targets]
