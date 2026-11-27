"""환경 변수(.env) 한 곳. 다른 파일은 settings만 import한다. 담당: KHS"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 0. 로그인 (RULES 7-4)
    auth_enabled: bool = True
    auth_secret_key: str = ""
    auth_session_hours: int = 12
    admin_username: str = ""
    admin_password: str = ""
    admin_display_name: str = "관리자"
    auth_max_failures: int = 5  # 틀린 횟수 한도 (RULES 7-4)
    auth_lock_minutes: int = 10

    # 1. 실행 환경
    app_env: str = "local"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    data_dir: str = "data"
    local_db_path: str = "data/app.db"

    # 2. AI (core/llm.py)
    llm_enabled: bool = True
    # AI는 OpenAI만 쓴다(HS 결정 11/26). 예전 .env의 AI_PROVIDER·ANTHROPIC_API_KEY·CLAUDE_MODEL 줄은 무시된다(extra="ignore")
    openai_api_key: str = ""
    openai_model: str = ""
    mask_shipper_names: bool = True

    # 3. 구글 (드라이브·Gmail). 파일이 없으면 연동을 끄고 로컬 사본만 둔다
    google_credentials_file: str = "credentials.json"
    google_token_file: str = "token.json"
    drive_inbox_folder_id: str = ""
    drive_law_folder_id: str = ""
    # OAuth 데스크톱 앱 클라이언트를 .env에서 읽는다(credentials.json 파일 대신, 값이 있으면 우선)
    google_client_type: str = "installed"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    google_token_uri: str = "https://oauth2.googleapis.com/token"
    google_redirect_uri: str = "http://localhost:8080/"
    # 구글 시트 ID (공유본만. 운영용 ID 금지)
    spreadsheet_id: str = ""  # 검역 이력 (공유본)
    item_spreadsheet_id: str = ""  # 품목사항 (공유본)
    gmail_sender: str = ""
    alert_email_to: str = ""

    # 4. 유니패스 (mock | live). 신청서 작성·전송 코드는 만들지 않는다
    unipass_mode: str = "mock"
    unipass_cargo_api_key: str = ""
    unipass_fxrt_api_key: str = ""
    unipass_inspection_api_key: str = ""
    unipass_timeout_sec: float = 10.0

    # 5. 식약처 (공공데이터포털)
    mfds_overseas_maker_api_key: str = ""
    mfds_import_rcpt_entp_api_key: str = ""
    mfds_material_code_api_key: str = ""

    # 5-1. 기타 공공 API (연결 상태 화면에서 검사만. 탭 6. 연결 설정)
    law_api_oc: str = ""  # 법제처 OPEN API (등록한 공인 IP에서만 동작)
    foodsafety_api_key: str = ""  # 식품안전나라

    # 6. Supabase (읽기만. 쓰기는 PM 스크립트)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # 업무 수치 (법령·실무 규칙. 코드에 숫자를 박지 않는다, AGENTS 0-5)
    # 정밀검사 실적 유효기간: 승인일 + 5년 (SAMC 실무 규칙) — 근거 조항 최신본 확인 필요
    record_valid_years: int = 5
    alert_days_before: str = "90,30"  # 미팅 11/24: 3개월·1개월 전
    # 해외제조업소 코드 유효기간(년). 등록(갱신)일 + 2년 (A2-5, RULES 11-8-1)
    # 근거: 수입식품안전관리 특별법 시행규칙(해외제조업소 등록 유효기간) — 최신본 확인 필요
    factory_code_valid_years: int = 2
    # 해외제조업소 주소 유사도: 0.45 이상이고 2등과 0.1 이상 차이 (기존 도구 2026-11-13 확정)
    factory_addr_min_score: float = 0.45
    factory_addr_min_gap: float = 0.10
    # 실적 만료 임박 경고(검역이력 비고): 만료 n일 전부터 (기존 도구 EXPIRY_WARN_DAYS) — 확인 필요
    record_warn_days: int = 90

    @property
    def alert_days(self) -> list[int]:
        out = []
        for part in self.alert_days_before.split(","):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return sorted(out, reverse=True)

    @property
    def data_path(self) -> Path:
        p = self.path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def path(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else REPO_ROOT / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
