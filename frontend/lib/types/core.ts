// 백엔드 core 스키마와 같은 타입. 담당: KHS
export interface ApiErrorBody {
  error: { code: string; message: string };
}

export interface LoginOut {
  token: string;
  expires_at: string;
  display_name: string;
}

export interface MeOut {
  logged_in: boolean;
  display_name: string;
  remote_data: boolean;
}

export interface Health {
  ok: boolean;
  llm_enabled: boolean;
  ai_provider: string;
  unipass_mode: string;
  supabase: boolean;
}

export interface IntegrationState {
  ok: boolean;
  reason?: string;
}

export interface Integrations {
  llm: IntegrationState;
  unipass: IntegrationState & { mode: string; fx: boolean };
  mfds: IntegrationState;
  drive: IntegrationState;
  gmail: IntegrationState;
  supabase: IntegrationState;
}

export interface Shipper {
  shipper_id: string;
  display_name: string;
}

// 설정 › 연결 상태 (GET /core/connections). 키 값은 오지 않는다
export type ConnState = "ok" | "fail" | "off";

export interface ConnCheck {
  state: ConnState;
  message: string;
  checked_at: string;
  elapsed_ms: number;
}

export interface AiModelOption {
  id: string;
  tier: string; // 추천 버전의 비용·속도 등급
  group: "recommended" | "account" | "custom"; // 추천 / 이 계정에서 쓸 수 있는 전체 버전 / 직접 입력
  available: boolean | null; // null = 아직 검사 전
}

export interface ConnRow {
  key: string;
  label: string;
  uses: string;
  configured: boolean;
  config_reason: string;
  last: ConnCheck | null;
  ai?: { in_use: boolean; model: string; models: AiModelOption[]; account_list: boolean };
}

export interface Connections {
  provider: "openai" | "claude";
  llm_enabled: boolean;
  rows: ConnRow[];
}
