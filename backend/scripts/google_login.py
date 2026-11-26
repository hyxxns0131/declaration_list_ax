"""처음 구글 로그인 → token.json 만들기.

내 PC에서 한 번만 실행한다(브라우저가 열린다). 클라우드·서버에서는 실행하지 않는다.
    cd backend
    python scripts/google_login.py

준비: 저장소 맨 위 .env에 GOOGLE_CLIENT_ID·GOOGLE_CLIENT_SECRET(또는 credentials.json).
결과: GOOGLE_TOKEN_FILE(기본 token.json)에 저장. 커밋 금지(.gitignore 확인).
토큰·키 값은 화면에 출력하지 않는다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.storage import google_auth  # noqa: E402


def main() -> int:
    if google_auth.client_config() is None:
        print(
            "OAuth 클라이언트 정보가 없습니다. .env의 GOOGLE_CLIENT_ID·GOOGLE_CLIENT_SECRET을 확인하세요."
        )
        return 1
    print("브라우저에서 구글 계정으로 로그인하고 권한을 허용하세요...")
    path = google_auth.login()
    print(f"로그인 완료: {path} 저장 (커밋하지 마세요)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
