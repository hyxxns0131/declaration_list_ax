"""구글 시트 읽기·쓰기 (Sheets API v4). 담당: KHS

드라이브(drive.py)와 같은 방식: token.json(google_auth)으로 httpx 직접 호출, 새 라이브러리 없음.
시트 ID는 .env에만 둔다(공개 저장소, 공유본 ID만). 화면·API는 시트 '이름표'(key)로만 부른다.
token.json이나 시트 ID가 없으면 {"ok": False, "reason": ...}만 돌려주고 아무것도 하지 않는다.
"""

from urllib.parse import quote

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.storage import google_auth

API = "https://sheets.googleapis.com/v4/spreadsheets"

# 이름표 → (설정 칸 이름, 화면 이름). 한글표시사항 자동 작성은 범위 밖(AGENTS 0-1)이라 넣지 않는다
SHEETS = {
    "history": ("spreadsheet_id", "검역 이력 (공유본)"),
    "item": ("item_spreadsheet_id", "품목사항 (공유본)"),
}


def _sheet_id(key: str) -> str:
    if key not in SHEETS:
        raise AppError("unknown_sheet", f"알 수 없는 시트입니다: {key}", 404)
    sid = getattr(get_settings(), SHEETS[key][0])
    if not sid:
        raise AppError("sheet_not_configured", f"{SHEETS[key][1]} 시트 ID가 .env에 없습니다.", 409)
    return sid


def _headers() -> dict[str, str]:
    h = google_auth.headers()
    if not h:
        raise AppError("google_login_required", "구글 로그인 필요(token.json 없음 또는 만료).", 409)
    return h


def _call(method: str, url: str, **kw) -> dict:
    try:
        r = httpx.request(method, url, headers=_headers(), timeout=30, **kw)
    except httpx.HTTPError as e:
        raise AppError(
            "google_unreachable", f"구글에 접속하지 못했습니다: {type(e).__name__}", 502
        ) from None
    if r.status_code >= 400:
        # 구글 오류 메시지만 전달(토큰·ID는 넣지 않는다)
        try:
            msg = r.json().get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        raise AppError("google_error", f"구글 시트 오류 {r.status_code}: {msg}".strip(), 502)
    return r.json()


def status() -> dict:
    """시트별 설정 여부(네트워크 없음). ID 값은 돌려주지 않는다."""
    login = google_auth.configured()
    s = get_settings()
    out = {
        key: {
            "name": name,
            "ok": login and bool(getattr(s, attr)),
            "reason": ""
            if login and getattr(s, attr)
            else ("token.json 없음(구글 로그인 필요)" if not login else "시트 ID 없음"),
        }
        for key, (attr, name) in SHEETS.items()
    }
    return out


def tabs(key: str) -> list[str]:
    """시트 안의 탭 이름 목록."""
    data = _call("GET", f"{API}/{_sheet_id(key)}", params={"fields": "sheets.properties.title"})
    return [s["properties"]["title"] for s in data.get("sheets", [])]


def read(key: str, range_: str) -> list[list[str]]:
    """범위 읽기. 예: range_='A기업!A1:Z50'. 빈 칸 끝부분은 구글이 잘라서 준다."""
    rng = quote(range_, safe="")
    data = _call("GET", f"{API}/{_sheet_id(key)}/values/{rng}")
    return data.get("values", [])


def write(key: str, range_: str, values: list[list[str]]) -> dict:
    """범위 덮어쓰기. 글자 그대로 넣는다(RAW: 앞자리 0·화물관리번호 보존, 수식 실행 안 함)."""
    rng = quote(range_, safe="")
    data = _call(
        "PUT",
        f"{API}/{_sheet_id(key)}/values/{rng}",
        params={"valueInputOption": "RAW"},
        json={"range": range_, "majorDimension": "ROWS", "values": values},
    )
    return {
        "updated_range": data.get("updatedRange", ""),
        "updated_cells": data.get("updatedCells", 0),
    }
