"""영역 라우터 (검역이력 행·서류 대조·검수 패널). 담당: KHS

GET   /history?shipper_id=&status=&attention=     검역이력 표
GET   /history/badges?shipper_id=                 확인 필요 n, 진행 중 n
GET   /history/columns                            열 이름(26칸 + 색상, 숨김 열)
POST  /history/refresh?shipper_id=                새로고침(유니패스·대조·재계산, 확정 값 유지)
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

from app.a1_history.rows import service
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


@router.get("/columns")
def columns() -> dict:
    return {
        "columns": list(COLUMNS),
        "color_column": COLOR_COLUMN,
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


@router.post("/{row_id}/confirm")
def confirm(row_id: str, body: ConfirmIn) -> HistoryRow:
    return service.confirm(row_id, body.on)
