"""품목사항 → 구글 시트로 새로 만들기(신고건 1건 = 시트 1개). 담당: LSY [신규] A3-5 (시연 피드백 11/28 3-2)

- 엑셀 파일과 같은 값(build_item_sheet)을 공유 드라이브 폴더에 새 구글 시트로 만든다. 기존 파일은 건드리지 않는다.
- 시트 이름: 품목사항_{화주}사_신고건{번호}_{YYYYMMDD} (LSY 11/28). 같은 이름이 있어도 새로 만든다(구글은 이름 중복 허용).
- 만들 폴더: .env의 ITEM_SHEET_FOLDER_ID(공유본 폴더 ID, 공개 저장소라 .env에만). 아직 core 설정 칸이 없어
  .env 파일을 직접 읽는다 → KHS에 core/config·.env.example 칸 추가 요청(제안).
- 로그인·토큰은 core/storage/google_auth의 공개 함수만 쓴다. core/storage/sheets.py(공통, KHS)는 고치지 않는다.
- 구글 로그인 없음·폴더 ID 없음 → 아무것도 만들지 않고 이유만 돌려준다.
"""

import os
from datetime import date

import httpx

from app.a3_judge.item_sheet.build import HEADERS, build_item_sheet
from app.a3_judge.item_sheet.bulk import _declarations, _problems
from app.a4_settings.engine.service import get_rules
from app.core.config import REPO_ROOT
from app.core.errors import AppError
from app.core.storage import google_auth

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
FOLDER_ENV = "ITEM_SHEET_FOLDER_ID"


def folder_id() -> str:
    """환경 변수 → .env 순서로. 값은 화면·로그에 내지 않는다."""
    v = os.getenv(FOLDER_ENV, "").strip()
    if v:
        return v
    try:
        from dotenv import dotenv_values

        return str(dotenv_values(REPO_ROOT / ".env").get(FOLDER_ENV) or "").strip()
    except Exception:  # dotenv 없음·파일 없음
        return ""


def sheet_title(shipper_id: str, number: int, on: date | None = None) -> str:
    return f"품목사항_{shipper_id}사_신고건{number}_{(on or date.today()):%Y%m%d}"


def _call(method: str, url: str, headers: dict[str, str], **kw) -> dict:
    try:
        r = httpx.request(method, url, headers=headers, timeout=30, **kw)
    except httpx.HTTPError as e:
        raise AppError(
            "google_unreachable", f"구글에 접속하지 못했습니다: {type(e).__name__}", 502
        ) from None
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        raise AppError("google_error", f"구글 오류 {r.status_code}: {msg}".strip(), 502)
    return r.json()


def create_item_sheet(shipper_id: str, declaration_id: str) -> dict:
    """{ok, reason} 또는 {ok, title, url, rows}. 검사에 걸린 신고건(한 신고건 아님·실적 없음)은 만들지 않는다."""
    item = next(
        (x for x in _declarations(shipper_id) if x[1].declaration_id == declaration_id), None
    )
    if not item:
        raise AppError("not_found", "신고건이 없습니다.", 404)
    number, _decl, rows = item
    reasons = _problems(rows, get_rules(shipper_id))
    if reasons:
        return {"ok": False, "reason": "품목사항을 만들 수 없는 신고건: " + " / ".join(reasons)}
    folder = folder_id()
    if not folder:
        return {
            "ok": False,
            "reason": f"{FOLDER_ENV}가 .env에 없습니다(품목사항 시트를 만들 폴더).",
        }
    h = google_auth.headers()
    if not h:
        return {"ok": False, "reason": "구글 로그인 필요(token.json 없음 또는 만료)."}
    title = sheet_title(shipper_id, number)
    made = _call(
        "POST",
        DRIVE_FILES,
        h,
        params={"supportsAllDrives": "true", "fields": "id,webViewLink"},
        json={"name": title, "mimeType": SHEET_MIME, "parents": [folder]},
    )
    sid = made["id"]
    values = [[name for name, _ in HEADERS], *build_item_sheet(rows).rows]
    # 글자 그대로(RAW): 화물관리번호 앞자리 0 보존, 수식 실행 안 함
    _call(
        "PUT",
        f"{SHEETS_API}/{sid}/values/A1",
        h,
        params={"valueInputOption": "RAW"},
        json={"range": "A1", "majorDimension": "ROWS", "values": values},
    )
    return {"ok": True, "title": title, "url": made.get("webViewLink", ""), "rows": len(values) - 1}
