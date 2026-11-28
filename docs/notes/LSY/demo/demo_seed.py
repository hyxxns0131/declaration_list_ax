"""시연용 데이터 한 번에 넣기 (탭 4·5 확인용, 구글 드라이브 연동 전까지). 담당: LSY

하는 일 — 화면에서 버튼을 누르는 것과 같은 API를 차례로 부른다(프로그램 안에서 직접, 서버 안 켜도 됨):
  1) 탭 3 서류 올리기: A사 밥솥 샘플(BL-TEST-001·002), B사 그릇 샘플(BL-DEMO-201, 내색·외색)
  2) 탭 2 서류 등록: samples/registry/A(밥솥 실적) + docs/notes/LSY/demo/registry/B(그릇 실적)
  3) 탭 4 신고건 묶음 계산 → 요약 출력

어디에 저장되나: 내 PC 로컬 DB(.env의 DATA_DIR, 기본 backend/data/app.db)에만.
  - 구글 드라이브: 이 스크립트 안에서는 연동을 끈다(DRIVE_INBOX_FOLDER_ID 비움) → 드라이브에 안 올라감
  - Supabase: 프로그램은 읽기만 한다(쓰기 없음, AGENTS 0-4)
  - AI(OpenAI): 끈다(LLM_ENABLED=false). 유니패스는 가짜 응답(UNIPASS_MODE=mock)
모든 값은 가상(VIRTUAL·DEMO)이다.

우선순위: 구글 드라이브·Supabase 실제 연동이 되면 그쪽 자료를 우선하고, 이 스크립트는 연동 전 임시 시연용으로만 쓴다.

실행 (backend 폴더에서):
  python ../docs/notes/LSY/demo/demo_seed.py
다시 넣고 싶을 때: 같은 B/L은 같은 선적 건으로 다시 계산된다(담당자가 고친 final_value는 유지).
완전히 처음부터 하려면 로컬 DB 파일을 직접 지운 뒤 다시 실행(스크립트는 아무것도 지우지 않는다).
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BACKEND = ROOT / "backend"

# 앱을 불러오기 전에 이 실행에서만 쓸 설정(.env보다 우선). .env 파일은 바꾸지 않는다.
os.environ.update(
    AUTH_ENABLED="false",
    LLM_ENABLED="false",
    UNIPASS_MODE="mock",
    DRIVE_INBOX_FOLDER_ID="",
)
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SHIPMENTS = [
    ("A", ROOT / "samples" / "A" / "BL-TEST-001"),
    ("A", ROOT / "samples" / "A" / "BL-TEST-002"),
    ("B", ROOT / "samples" / "B" / "BL-DEMO-201"),
]
REGISTRY = [
    ("A", ROOT / "samples" / "registry" / "A"),
    ("B", HERE / "registry" / "B"),
]


def _files(folder: Path) -> list:
    return [("files", (p.name, p.read_bytes())) for p in sorted(folder.iterdir()) if p.is_file()]


def _ok(r, what: str) -> dict:
    if r.status_code >= 400:
        raise SystemExit(f"[실패] {what}: {r.status_code} {r.text[:300]}")
    return r.json()


def main() -> None:
    if not (ROOT / "samples" / "B" / "BL-DEMO-201" / "CI.xlsx").exists():
        raise SystemExit(
            "B사 그릇 샘플이 없습니다. 먼저: python ../docs/notes/LSY/demo/make_demo_files.py"
        )
    with TestClient(app) as c:
        print("1) 탭 3 서류 올리기")
        for sh, folder in SHIPMENTS:
            j = _ok(
                c.post("/api/reader/upload", data={"shipper_id": sh}, files=_files(folder)),
                folder.name,
            )
            print(
                f"   {sh}사 {folder.name}: B/L {j.get('bl_no')}, 서류 {len(j.get('documents', []))}개"
            )
        print("2) 탭 2 서류 등록(수입신고서·시험성적서)")
        for sh, folder in REGISTRY:
            up = _ok(
                c.post("/api/registry/upload", data={"shipper_id": sh}, files=_files(folder)),
                folder.name,
            )
            uid = up.get("upload_id")
            done = _ok(
                c.post(f"/api/registry/upload/{uid}/commit", json={"edits": []}), f"{sh} 등록 저장"
            )
            print(
                f"   {sh}사: 후보 {len(up.get('candidates', []))}건 등록, 다시 판단한 행 {done.get('rejudged')}"
            )
        print("3) 탭 4 신고건 묶음")
        for sh in "AB":
            decl = _ok(c.post(f"/api/judge/declarations?shipper_id={sh}"), f"{sh} 신고건")
            print(f"   {sh}사: 신고건 {len(decl)}건")
            for d in decl:
                k = d["key"]
                warn = f"  ⚠ {' / '.join(d['warnings'])}" if d.get("warnings") else ""
                print(
                    f"     - {d['declaration_id']}: 행 {len(d['row_ids'])} · 재질 {k.get('material') or '없음'}"
                    f" · 색 {k.get('color') or '-'} · 실적 {', '.join(d.get('record_nos') or []) or '없음'}{warn}"
                )
    print("끝. 화면(탭 4 재질·실적 판단, 탭 5 품목사항)에서 A사·B사를 골라 확인하세요.")


if __name__ == "__main__":
    main()
