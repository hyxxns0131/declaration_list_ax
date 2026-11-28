"""모델 자료(현품사진·라벨 엑셀, 수입신고서.json 등) 찾기 — 드라이브 읽기만. 담당: LSY [신규] (시연 피드백 11/27)

위치: 서류 접수(공유본, DRIVE_INBOX_FOLDER_ID) / {화주 폴더} / 현품사진 및 한글표시 사항 / {모델명} /
- 화주 폴더 이름: '{화주ID}기업'(기존 도구 가명 규칙, 예 A기업)을 먼저, 없으면 '{화주ID}'.
  화주 설정에 드라이브 폴더 이름 칸이 생기면 그 값을 먼저 쓴다(JUJ·KHS 요청 예정).
- 모델 폴더: 모델 코드가 정확히 같아야 한다(대소문자만 무시, RULES 11-2).
- 폴더를 새로 만들지 않는다(core drive.folder_path는 만들기 때문에 쓰지 않는다). 쓰기·이동·삭제 없음.
- 사진·라벨만으로 재질을 정하지 않는다(AGENTS 7-9). 담당자가 열어 보도록 목록만 준다.
"""

import httpx

from app.a3_judge.history_lookup.model_key import same_model
from app.core.config import get_settings
from app.core.storage import drive, google_auth

MODEL_DOCS_DIR = "현품사진 및 한글표시 사항"
PRECISE_PREFIX = "정밀실적"
_known_files: dict[str, str] = {}  # 목록으로 보여 준 파일만 내려받게 한다 (file_id → 이름)


def _kind(f: dict) -> str:
    name = str(f.get("name", ""))
    if f.get("mimeType") == drive.FOLDER_MIME:
        return "precise" if name.startswith(PRECISE_PREFIX) else "folder"
    low = name.lower()
    if low.endswith(".json"):
        return "import_decl" if "수입신고서" in name else "json"
    if low.endswith((".xlsx", ".xls", ".xlsm")) or "spreadsheet" in str(f.get("mimeType", "")):
        return "excel"
    if low.endswith((".png", ".jpg", ".jpeg", ".pdf")):
        return "image"
    return "other"


def _child(
    parent: str, names: list[str], h: dict[str, str], folder_only: bool = True
) -> dict | None:
    kids = drive.list_children(parent, h)
    for want in names:
        for k in kids:
            if folder_only and k.get("mimeType") != drive.FOLDER_MIME:
                continue
            if k.get("name") == want:
                return k
    return None


def shipper_folder_names(shipper_id: str) -> list[str]:
    return [f"{shipper_id}기업", shipper_id]


def find_model_docs(shipper_id: str, model: str) -> dict:
    """{ok, reason, path, files:[{id,name,kind}]}. 연결·폴더가 없으면 ok=False + 이유(판단은 계속)."""
    out: dict = {"ok": False, "reason": "", "path": "", "files": []}
    if not model:
        out["reason"] = "모델 코드가 없어 모델 자료를 찾지 않음"
        return out
    st = drive.status()
    if not st["ok"]:
        out["reason"] = f"드라이브 미연결: {st['reason']}"
        return out
    h = google_auth.headers()
    if not h:
        out["reason"] = "드라이브 미연결: 구글 토큰 갱신 실패"
        return out
    try:
        root = get_settings().drive_inbox_folder_id
        shipper = _child(root, shipper_folder_names(shipper_id), h)
        if not shipper:
            out["reason"] = f"화주 폴더 없음({' 또는 '.join(shipper_folder_names(shipper_id))})"
            return out
        docs = _child(shipper["id"], [MODEL_DOCS_DIR], h)
        if not docs:
            out["reason"] = f"'{shipper['name']}/{MODEL_DOCS_DIR}' 폴더 없음"
            return out
        hit = next(
            (
                k
                for k in drive.list_children(docs["id"], h)
                if k.get("mimeType") == drive.FOLDER_MIME
                and same_model(str(k.get("name", "")), model)
            ),
            None,
        )
        out["path"] = f"{shipper['name']}/{MODEL_DOCS_DIR}/{hit['name'] if hit else model}"
        if not hit:
            out["reason"] = "이 모델의 자료 폴더 없음"
            return out
        files = [
            {"id": f["id"], "name": f["name"], "kind": _kind(f)}
            for f in drive.list_children(hit["id"], h)
        ]
    except httpx.HTTPError as e:
        out["reason"] = f"드라이브를 읽지 못함: {type(e).__name__}"
        return out
    for f in files:
        if f["kind"] not in ("folder", "precise"):
            _known_files[f["id"]] = f["name"]
    out.update(ok=True, files=files)
    return out


def download_model_doc(file_id: str) -> tuple[str, bytes] | None:
    """목록으로 보여 준 파일만 내려받는다. (이름, 바이트) 또는 None."""
    name = _known_files.get(file_id)
    h = google_auth.headers()
    if not name or not h:
        return None
    return name, drive.download(file_id, h)
