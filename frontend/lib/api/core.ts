// core API: 로그인, 상태, 화주 목록, 연동 상태, 연결 검사·AI 모델 고르기. 담당: KHS
import { api, tokenStore } from "@/lib/api/client";
import type { Connections, Health, Integrations, LoginOut, MeOut, Shipper } from "@/lib/types/core";

export async function login(username: string, password: string): Promise<LoginOut> {
  const out = await api<LoginOut>("/core/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  tokenStore.set(out.token);
  return out;
}

export async function logout(): Promise<void> {
  await api<{ ok: boolean }>("/core/auth/logout", { method: "POST" }).catch(() => undefined);
  tokenStore.clear();
}

export const me = () => api<MeOut>("/core/auth/me");
export const health = () => api<Health>("/core/health");
export const shippers = () => api<Shipper[]>("/core/shippers");
export const integrations = () => api<Integrations>("/core/integrations");

export const connections = () => api<Connections>("/core/connections");

/** [연결 검사]: service 없으면 전체. 실제로 접속해 본다(AI는 토큰을 쓰지 않음). */
export const checkConnections = (service = "all") =>
  api<Connections>("/core/connections/check", { method: "POST", body: JSON.stringify({ service }) });

/** 사용할 AI(model 없이) 또는 그 AI의 모델 저장. */
/** OpenAI 모델(버전) 저장. AI는 OpenAI만(HS 결정 11/26). 첫 인자는 예전 호출과 맞추려고 남긴 연결 키("openai"). */
export const setAiChoice = (_key: string, model: string) =>
  api<Connections>("/core/ai-choice", { method: "PUT", body: JSON.stringify({ provider: "openai", model }) });
