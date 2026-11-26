"use client";
// 로그인 화면 본문 (DESIGN 2-1). 틀리면 어느 쪽이 틀렸는지 말하지 않는다. 담당: KHS
import { useState, type FormEvent } from "react";

import { colors, panelRadius, space } from "@/components/ui/tokens";
import { ApiError } from "@/lib/api/client";
import { login } from "@/lib/api/core";
import { MAIN_PATH } from "@/lib/nav";
import { T } from "@/lib/text/common";

/** 로그인 뒤 갈 곳: 원래 화면, 없거나 홈이면 메인 화면(검역이력 표, 제안서 가이드라인 ④). */
function nextPath(): string {
  const next = new URLSearchParams(window.location.search).get("next");
  const ok = next && next.startsWith("/") && !next.startsWith("/login") && next !== "/";
  return ok ? next : MAIN_PATH;
}

export function LoginForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      window.location.href = nextPath();
    } catch (err: unknown) {
      if (err instanceof ApiError) setError(err.status === 0 ? T.networkError : err.message);
      setBusy(false);
    }
  };

  const field = { display: "block", width: "100%", padding: space.sm, marginTop: space.xs };
  return (
    <form
      onSubmit={onSubmit}
      style={{
        width: 360,
        margin: "120px auto",
        padding: space.xl,
        background: colors.panelBg,
        borderRadius: panelRadius,
        boxShadow: colors.panelShadow,
      }}
    >
      <h1 style={{ fontSize: 22, fontWeight: 800, color: colors.brand, textAlign: "center", marginBottom: space.lg }}>{T.appName}</h1>
      <label>
        {T.login.username}
        <input
          style={field}
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </label>
      <label style={{ display: "block", marginTop: space.md }}>
        {T.login.password}
        <input
          style={field}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error && <p style={{ color: colors.mismatch, marginTop: space.md }}>{error}</p>}
      <button
        type="submit"
        disabled={busy}
        style={{
          width: "100%",
          marginTop: space.lg,
          padding: space.sm + 2,
          background: colors.brand,
          color: "#fff",
          border: 0,
          borderRadius: 999,
          fontWeight: 700,
          cursor: busy ? "not-allowed" : "pointer",
        }}
      >
        {busy ? T.login.submitting : T.login.submit}
      </button>
      <p style={{ color: colors.muted, fontSize: 13, marginTop: space.md, textAlign: "center" }}>
        {T.login.help}
      </p>
    </form>
  );
}
