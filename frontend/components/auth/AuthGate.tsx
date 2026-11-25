"use client";
// 로그인 확인: 로그인 안 했으면 /login으로 (DESIGN 2-1). 상단 탭 4개도 여기서 그린다(1인 1탭, 고정). 담당: KHS
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { UserMenu } from "@/components/auth/UserMenu";
import { colors, space } from "@/components/ui/tokens";
import { ApiError, tokenStore } from "@/lib/api/client";
import { me } from "@/lib/api/core";
import { T } from "@/lib/text/common";

// 탭 4개 = 제안서 가이드라인 1~4번. 탭 하나 = 담당 1명 (AGENTS 1장 탭 표)
const MENU = [
  { href: "/", label: T.tabs.list }, // KHS
  { href: "/registry/", label: T.tabs.registry }, // YHS
  { href: "/judge/", label: T.tabs.judge }, // LSY
  { href: "/settings/", label: T.tabs.settings }, // JUJ
] as const;

const norm = (p: string) => (p.endsWith("/") ? p : `${p}/`);
const isActive = (pathname: string, href: string) =>
  href === "/" ? norm(pathname) === "/" : norm(pathname).startsWith(href);

type State = "checking" | "in" | "error";

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname.startsWith("/login");
  const [state, setState] = useState<State>("checking");
  const [name, setName] = useState("");

  useEffect(() => {
    if (isLogin) return;
    const goLogin = () => {
      window.location.href = `/login/?next=${encodeURIComponent(pathname)}`;
    };
    if (!tokenStore.get()) {
      goLogin();
      return;
    }
    me()
      .then((m) => {
        if (!m.logged_in) {
          tokenStore.clear();
          goLogin();
          return;
        }
        setName(m.display_name);
        setState("in");
      })
      .catch((e: unknown) => setState(e instanceof ApiError && e.status === 0 ? "error" : "checking"));
  }, [isLogin, pathname]);

  if (isLogin) return <>{children}</>;
  if (state === "error") return <p style={{ padding: space.lg }}>{T.networkError}</p>;
  if (state === "checking") return <p style={{ padding: space.lg }}>{T.loading}</p>;

  return (
    <>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: space.lg,
          padding: `${space.sm}px ${space.lg}px`,
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        <strong>{T.appName}</strong>
        <nav role="tablist" style={{ display: "flex", gap: space.xs, alignSelf: "stretch" }}>
          {MENU.map((m) => {
            const on = isActive(pathname, m.href);
            return (
              <Link
                key={m.href}
                href={m.href}
                role="tab"
                aria-selected={on}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: `0 ${space.md}px`,
                  textDecoration: "none",
                  fontWeight: on ? 700 : 400,
                  color: on ? colors.primary : colors.text,
                  background: on ? colors.primarySoft : "transparent",
                  borderBottom: `3px solid ${on ? colors.primary : "transparent"}`,
                }}
              >
                {m.label}
              </Link>
            );
          })}
        </nav>
        <div style={{ marginLeft: "auto" }}>
          <UserMenu name={name} />
        </div>
      </header>
      <main style={{ padding: space.lg }}>{children}</main>
    </>
  );
}
