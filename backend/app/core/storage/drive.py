"""구글 드라이브: 업로드 사본 저장, 처리완료 이동(지우기 대신 이동). 담당: KHS (A0-1, A1-5, A2-4)

폴더 ID는 .env(DRIVE_INBOX_FOLDER_ID)에만 둔다(공개 저장소). token.json이 없으면 아무것도 하지 않고
{"ok": False, "reason": ...}를 돌려준다 → 화면에 "드라이브 연동 꺼짐"만 보인다. 로컬 사본은 항상 DATA_DIR에 있다.
폴더 구조(RULES 11-1): {화주}/{B/L} {모델} 외/, {화주}/재질 시험성적서/, 처리완료/{화주}/, 확인 필요/
"""

import json
import mimetypes
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.storage import google_auth

API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id"
FOLDER_MIME = "application/vnd.google-apps.folder"


def status() -> dict:
    s = get_settings()
    if not s.drive_inbox_folder_id:
        return {"ok": False, "reason": "DRIVE_INBOX_FOLDER_ID 없음"}
    if not google_auth.configured():
        return {"ok": False, "reason": "token.json 없음(구글 로그인 필요)"}
    return {"ok": True, "reason": ""}


def _find_or_create(name: str, parent: str, h: dict[str, str]) -> str:
    safe = name.replace("'", "\\'")
    q = f"name = '{safe}' and '{parent}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false"
    r = httpx.get(API, params={"q": q, "fields": "files(id)"}, headers=h, timeout=30)
    r.raise_for_status()
    files = r.json().get("files", [])
    if files:
        return files[0]["id"]
    r = httpx.post(
        API,
        params={"fields": "id"},
        json={"name": name, "mimeType": FOLDER_MIME, "parents": [parent]},
        headers=h,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["id"]


def folder_path(parts: list[str]) -> str | None:
    """접수 폴더 아래 parts 경로의 폴더 id(없으면 만든다). 연동 꺼짐이면 None."""
    h = google_auth.headers()
    if not h or not status()["ok"]:
        return None
    parent = get_settings().drive_inbox_folder_id
    for p in parts:
        parent = _find_or_create(p, parent, h)
    return parent


def upload(local: Path, name: str, parts: list[str]) -> dict:
    """로컬 파일 → 드라이브 parts 폴더. {"ok", "file_id"|"reason"}"""
    st = status()
    if not st["ok"]:
        return st
    h = google_auth.headers()
    if not h:
        return {"ok": False, "reason": "구글 토큰 갱신 실패"}
    try:
        parent = folder_path(parts)
        meta = json.dumps({"name": name, "parents": [parent]})
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        files = {
            "metadata": ("metadata", meta, "application/json; charset=UTF-8"),
            "file": (name, local.read_bytes(), mime),
        }
        r = httpx.post(UPLOAD, files=files, headers=h, timeout=120)
        r.raise_for_status()
        return {"ok": True, "file_id": r.json()["id"]}
    except httpx.HTTPError as e:
        return {"ok": False, "reason": f"드라이브 저장 실패({type(e).__name__})"}


def move_folder(name_parts: list[str], to_parts: list[str]) -> dict:
    """폴더 이동(처리완료). 지우지 않는다."""
    st = status()
    if not st["ok"]:
        return st
    h = google_auth.headers()
    if not h:
        return {"ok": False, "reason": "구글 토큰 갱신 실패"}
    try:
        src = folder_path(name_parts)
        dst = folder_path(to_parts)
        cur = (
            folder_path(name_parts[:-1])
            if len(name_parts) > 1
            else get_settings().drive_inbox_folder_id
        )
        r = httpx.patch(
            f"{API}/{src}",
            params={"addParents": dst, "removeParents": cur, "fields": "id"},
            headers=h,
            timeout=30,
        )
        r.raise_for_status()
        return {"ok": True, "file_id": src}
    except httpx.HTTPError as e:
        return {"ok": False, "reason": f"드라이브 이동 실패({type(e).__name__})"}


# ── 접수 폴더 자동 처리(inbox, 로직 점검 반영 11/25) ─────────────────────────
INBOX_NEW = "새 서류"  # {접수 폴더}/{화주}/새 서류/{B/L 폴더}/ 에 서류를 넣으면 가져온다
INBOX_DONE = "가져옴"  # 가져온 B/L 폴더는 {화주}/가져옴/ 으로 옮긴다(지우지 않음)


def list_children(folder_id: str, h: dict[str, str]) -> list[dict]:
    """폴더 안 항목 [{id, name, mimeType}] (휴지통 제외)."""
    r = httpx.get(
        API,
        params={
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "files(id,name,mimeType)",
            "pageSize": 200,
        },
        headers=h,
        timeout=30,
    )
    r.raise_for_status()
    return list(r.json().get("files", []))


def download(file_id: str, h: dict[str, str]) -> bytes:
    r = httpx.get(f"{API}/{file_id}", params={"alt": "media"}, headers=h, timeout=120)
    r.raise_for_status()
    return r.content


def inbox_folders(shipper_id: str) -> tuple[list[tuple[str, list[tuple[str, bytes]]]], str]:
    """{화주}/새 서류/ 아래 B/L 폴더마다 (폴더 이름, [(파일 이름, 바이트)]). 연결 안 되면 ([], 이유)."""
    st = status()
    if not st["ok"]:
        return [], f"드라이브 미연결: {st['reason']}"
    h = google_auth.headers()
    if not h:
        return [], "드라이브 미연결: 구글 토큰 갱신 실패"
    try:
        new_id = folder_path([shipper_id, INBOX_NEW])
        if not new_id:
            return [], "드라이브 미연결"
        out: list[tuple[str, list[tuple[str, bytes]]]] = []
        for f in list_children(new_id, h):
            if f.get("mimeType") != FOLDER_MIME:
                continue
            files = [
                (c["name"], download(c["id"], h))
                for c in list_children(f["id"], h)
                if c.get("mimeType") != FOLDER_MIME
            ]
            if files:
                out.append((f["name"], files))
        return out, ""
    except httpx.HTTPError as e:
        return [], f"드라이브 읽기 실패({type(e).__name__})"
