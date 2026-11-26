"""영역 라우터 (검역이력 행·서류 대조·검수 패널). 담당: KHS

GET   /history?shipper_id=&status=&attention=     검역이력 표
GET   /history/badges?shipper_id=                 확인 필요 n, 진행 중 n
GET   /history/columns?shipper_id=                열 이름(26칸 + 색상, 숨김 열). 색상 열은 화주 설정 group_by_color로 켠다
GET   /history/steps?shipper_id=                  단계 표시줄 완료 판단(① 자료 추가 필요 ② 미해결 불일치 ③ 빈 필수 칸) — 0단계
POST  /history/refresh?shipper_id=                새로고침(유니패스·대조·재계산, 확정 값 유지)
POST  /history/crosscheck?shipper_id=             서류 3종 다시 대조(코드 + OpenAI) — 2단계
GET   /history/mismatches?shipper_id=&status=     대조 결과(불일치·해결됨, status=일치/불일치/해결됨) — 2단계
POST  /history/fill?shipper_id=                   서류 등록 탭 정보로 제조사·재질·실적 채우기 — 4단계
PATCH /history/{row_id}/resolve                   검수 패널에서 고른 값 저장(final_value, 근거 MANUAL) — 3단계
POST  /history/archive?shipper_id=                처리완료 이동(드라이브)
GET   /history/{row_id}                           행 하나
PATCH /history/{row_id}                           담당자 수정(final_value)
DELETE /history/{row_id}                          행 지우기(승인 행 금지)
POST  /history/{row_id}/move                      행 이동
GET   /history/{row_id}/review                    검수 패널 데이터
POST  /history/{row_id}/confirm                   확인함 / 확인 취소
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.a1_history.fill import service as fill_service
from app.a1_history.review import service as review_service
from app.a1_history.rows import service
from app.a1_history.rows.steps import steps as compute_steps
from app.a4_settings.engine.service import get_rules
from app.core.errors import AppError
from app.core.schema.history import COLOR_COLUMN, COLUMNS, HIDDEN_COLUMNS, HistoryRow
from app.core.storage import work_db

router = APIRouter(prefix="/history", tags=["history"])

# 기본 보기 열(DESIGN 3-2)
DEFAULT_VIEW = (
    "B/L Number",
    "모선명",
    "반입일",
    "한글 제품명(모델넘버)",
    "재질 (재질 코드명으로 작성, 가나다 순으로 기재)",
    "카톤 수",
    "실적접수번호 (승인일)",
    "비고",
)


class PatchIn(BaseModel):
    column: str
    value: Any = None
    memo: str | None = None
    clear: bool = False  # 사람 값 지우기(프로그램 값으로 되돌리기)


class ConfirmIn(BaseModel):
    on: bool = True


class MoveIn(BaseModel):
    before_row_id: str | None = None


@router.get("")
def history(
    shipper_id: str, status: str | None = None, attention: bool = False
) -> list[HistoryRow]:
    return service.list_history(shipper_id, status, attention)


@router.get("/badges")
def badges(shipper_id: str) -> dict:
    return service.badges(shipper_id)


class ResolveIn(BaseModel):
    choices: list[review_service.Choice]


@router.post("/crosscheck")
def crosscheck(shipper_id: str) -> dict:
    return review_service.crosscheck_all(shipper_id)


@router.get("/mismatches")
def mismatches(shipper_id: str, status: str | None = None) -> list[dict]:
    return review_service.list_mismatches(shipper_id, status)


@router.post("/fill")
def fill(shipper_id: str) -> dict:
    return fill_service.fill(shipper_id)


@router.get("/steps")
def steps(shipper_id: str) -> dict:
    return compute_steps(work_db.list_rows(shipper_id))


@router.get("/columns")
def columns(shipper_id: str | None = None) -> dict:
    show_color = (
        bool(getattr(get_rules(shipper_id), "group_by_color", False)) if shipper_id else None
    )
    return {
        "columns": list(COLUMNS),
        "color_column": COLOR_COLUMN,
        "show_color": show_color,  # None = 화주 모름(행에 색상이 있으면 보임)
        "hidden": list(HIDDEN_COLUMNS),
        "default_view": list(DEFAULT_VIEW),
    }


@router.post("/refresh")
def refresh(shipper_id: str) -> dict:
    return service.refresh(shipper_id)


@router.post("/archive")
def archive(shipper_id: str) -> dict:
    return service.archive_ready(shipper_id)


@router.get("/{row_id}")
def get_row(row_id: str) -> HistoryRow:
    row = work_db.get_row(row_id)
    if not row:
        raise AppError("not_found", "행이 없습니다.", 404)
    return row


@router.patch("/{row_id}")
def patch(row_id: str, body: PatchIn) -> HistoryRow:
    return service.patch_cell(row_id, body.column, body.value, body.memo, body.clear)


@router.delete("/{row_id}")
def delete(row_id: str) -> dict:
    service.delete_row(row_id)
    return {"ok": True}


@router.post("/{row_id}/move")
def move(row_id: str, body: MoveIn) -> dict:
    service.move_row(row_id, body.before_row_id)
    return {"ok": True}


@router.get("/{row_id}/review")
def review(row_id: str) -> dict:
    return service.review(row_id)


@router.patch("/{row_id}/resolve")
def resolve(row_id: str, body: ResolveIn) -> HistoryRow:
    return review_service.resolve(row_id, body.choices)


@router.post("/{row_id}/confirm")
def confirm(row_id: str, body: ConfirmIn) -> HistoryRow:
    return service.confirm(row_id, body.on)
