// core API: 로그인, 상태, 화주 목록, 연동 상태. 담당: KHS
import { api, tokenStore } from "@/lib/api/client";
import type { Health, Integrations, LoginOut, MeOut, Shipper } from "@/lib/types/core";

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
