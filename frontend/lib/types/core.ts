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
