// 공통 fetch: 주소, 로그인 토큰, 오류 처리. 컴포넌트에서 fetch를 직접 쓰지 않는다 (RULES 5-2). 담당: KHS
import type { ApiErrorBody } from "@/lib/types/core";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api";
const TOKEN_KEY = "dl_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export const tokenStore = {
  get: (): string | null =>
    typeof window === "undefined" ? null : window.sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => window.sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => window.sessionStorage.removeItem(TOKEN_KEY),
};

function isErrorBody(v: unknown): v is ApiErrorBody {
  return typeof v === "object" && v !== null && "error" in v;
}

/** 쿼리 문자열 만들기(빈 값은 뺀다). */
export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

/** 파일 받기(로그인 토큰을 붙여야 해서 <a href>로 직접 열 수 없다). */
export async function apiBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { headers });
  } catch {
    throw new ApiError(0, "network", "network");
  }
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null);
    const err = isErrorBody(body) ? body.error : { code: "unknown", message: res.statusText };
    throw new ApiError(res.status, err.code, err.message);
  }
  return res.blob();
}

/** 받은 파일을 내려받기(이름 지정) 또는 새 창에서 열기. */
export function saveBlob(blob: Blob, filename: string | null): void {
  const url = URL.createObjectURL(blob);
  if (filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
  } else {
    window.open(url, "_blank", "noopener");
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network", "network");
  }
  const body: unknown = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/core/auth")) {
      tokenStore.clear();
      const next = encodeURIComponent(window.location.pathname);
      window.location.href = `/login/?next=${next}`; // 세션 끝 → 로그인 → 원래 화면 (DESIGN 2-1)
    }
    const err = isErrorBody(body) ? body.error : { code: "unknown", message: res.statusText };
    throw new ApiError(res.status, err.code, err.message);
  }
  return body as T;
}
