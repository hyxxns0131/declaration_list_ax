"""구글 드라이브·시트 API (/core/google/...). 담당: KHS

모두 로그인 필요. 폴더·시트 ID 값은 돌려주지 않고 이름표(inbox·law / history·item)로만 부른다.
처음 구글 로그인은 API가 아니라 PC에서 `python scripts/google_login.py`로 한다(브라우저가 필요해서).
"""

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth.deps import require_login
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.storage import drive, google_auth, sheets

router = APIRouter(prefix="/google", tags=["google"], dependencies=[Depends(require_login)])

FOLDERS = {
    "inbox": ("drive_inbox_folder_id", "서류 접수 (공유본)"),
    "law": ("drive_law_folder_id", "법령자료 (공유본)"),
}


class WriteIn(BaseModel):
    range: str  # 예: "A기업!A2:C2"
    values: list[list[str]]


@router.get("/status")
def google_status() -> dict:
    """로그인·폴더·시트 설정 여부(네트워크 없음). 값은 돌려주지 않는다."""
    s = get_settings()
    return {
        "login": {
            "ok": google_auth.configured(),
            "client": "env"
            if s.google_client_id
            else ("file" if google_auth.client_config() else "없음"),
        },
        "folders": {k: {"name": n, "ok": bool(getattr(s, a))} for k, (a, n) in FOLDERS.items()},
        "sheets": sheets.status(),
    }


@router.get("/drive/{folder}")
def drive_list(folder: str) -> dict:
    """접수·법령자료 폴더 바로 아래 항목 목록(이름·종류)."""
    if folder not in FOLDERS:
        raise AppError("unknown_folder", "inbox 또는 law만 볼 수 있습니다.", 404)
    folder_id = getattr(get_settings(), FOLDERS[folder][0])
    if not folder_id:
        raise AppError(
            "folder_not_configured", f"{FOLDERS[folder][1]} 폴더 ID가 .env에 없습니다.", 409
        )
    h = google_auth.headers()
    if not h:
        raise AppError("google_login_required", "구글 로그인 필요(token.json 없음 또는 만료).", 409)
    try:
        items = drive.list_children(folder_id, h)
    except httpx.HTTPError as e:
        raise AppError(
            "google_error", f"드라이브 목록을 읽지 못했습니다: {type(e).__name__}", 502
        ) from None
    return {
        "folder": FOLDERS[folder][1],
        "items": [
            {"name": f["name"], "is_folder": f.get("mimeType") == drive.FOLDER_MIME} for f in items
        ],
    }


@router.get("/sheets/{key}/tabs")
def sheet_tabs(key: str) -> dict:
    return {"tabs": sheets.tabs(key)}


@router.get("/sheets/{key}")
def sheet_read(key: str, range: str = Query(..., description="예: A기업!A1:Z20")) -> dict:
    return {"range": range, "values": sheets.read(key, range)}


@router.put("/sheets/{key}")
def sheet_write(key: str, body: WriteIn) -> dict:
    return sheets.write(key, body.range, body.values)
