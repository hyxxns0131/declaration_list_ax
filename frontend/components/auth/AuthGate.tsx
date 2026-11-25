"use client";
// 로그인 확인: 로그인 안 했으면 /login으로 (DESIGN 2-1). 대시보드 틀(파란 바탕 위 큰 흰 판, 위 탭 홈+5개, 왼쪽 파란 사이드바 = 지금 탭의 세부 메뉴. DESIGN 8장 테마)도 여기서 그린다. 탭·메뉴 목록은 lib/nav.ts. 담당: KHS
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { UserMenu } from "@/components/auth/UserMenu";
import { ShipperBadge, ShipperGate } from "@/components/home/CurrentShipper";
import { colors, font, panelRadius, sidebarCurve, space } from "@/components/ui/tokens";
import { ApiError, tokenStore } from "@/lib/api/client";
import { connections, me } from "@/lib/api/core";
import { TABS, currentTab, isSideActive } from "@/lib/nav";
import { T } from "@/lib/text/common";

type State = "checking" | "in" | "error";

const FRAME = 28; // 파란 바탕과 흰 판 사이 여백
const SIDE_W = 240;
const RAIL_W = 72; // 닫힌 사이드바(아이콘만)
const SIDEBAR_KEY = "dl_sidebar_open";
const EASE = "200ms ease";
const HEADER_H = 76;

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname.startsWith("/login");
  const [state, setState] = useState<State>("checking");
  const [name, setName] = useState("");
  const [conn, setConn] = useState<{ ok: number; total: number } | null>(null);
  // 사이드바 열림(240px) / 닫힘(아이콘만 72px). 브라우저에 기억, 처음엔 넓은 화면만 열림
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const saved = window.localStorage.getItem(SIDEBAR_KEY);
    setOpen(saved === null ? window.innerWidth >= 1024 : saved === "1");
  }, []);

  const toggle = () => {
    setOpen((v) => {
      window.localStorage.setItem(SIDEBAR_KEY, v ? "0" : "1");
      return !v;
    });
  };

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
        connections() // 사이드바 아래 연결 막대: 마지막 검사 결과 기준(새 검사는 하지 않음)
          .then((c) => setConn({ ok: c.rows.filter((r) => r.last?.state === "ok").length, total: c.rows.length }))
          .catch(() => setConn(null));
      })
      .catch((e: unknown) => setState(e instanceof ApiError && e.status === 0 ? "error" : "checking"));
  }, [isLogin, pathname]);

  if (isLogin) return <>{children}</>;
  if (state === "error") return <p style={{ padding: space.lg, color: "#fff" }}>{T.networkError}</p>;
  if (state === "checking") return <p style={{ padding: space.lg, color: "#fff" }}>{T.loading}</p>;

  const tab = currentTab(pathname);

  return (
    <div style={{ minHeight: "100vh", background: colors.pageBg, padding: `clamp(12px, 1.6vw, ${FRAME}px)` }}>
      <div
        style={{
          background: colors.panelBg,
          borderRadius: panelRadius,
          boxShadow: colors.panelShadow,
          overflow: "hidden",
          minHeight: `calc(100vh - 2 * clamp(12px, 1.6vw, ${FRAME}px))`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <header style={{ display: "flex", alignItems: "center", gap: space.lg, height: HEADER_H, paddingRight: space.xl }}>
          <button
            type="button"
            onClick={toggle}
            aria-label={open ? T.sidebar.close : T.sidebar.open}
            aria-expanded={open}
            title={open ? T.sidebar.close : T.sidebar.open}
            style={{
              marginLeft: space.md + 2,
              marginRight: -space.sm,
              width: 38,
              height: 38,
              flexShrink: 0,
              border: 0,
              borderRadius: 10,
              background: colors.cardBg,
              color: colors.brand,
              fontSize: 18,
              cursor: "pointer",
            }}
          >
            ☰
          </button>
          <Link
            href="/"
            style={{
              width: SIDE_W - 56,
              flexShrink: 0,
              color: colors.brand,
              textDecoration: "none",
              fontWeight: 800,
              fontSize: font.lg,
              lineHeight: 1.3,
              display: "flex",
              alignItems: "center",
              gap: space.sm,
            }}
          >
            <span
              aria-hidden
              style={{
                width: 30,
                height: 30,
                borderRadius: 9,
                background: colors.brand,
                color: "#fff",
                display: "grid",
                placeItems: "center",
                fontSize: 15,
                flexShrink: 0,
              }}
            >
              ✓
            </span>
            {T.appName}
          </Link>
          <nav role="tablist" style={{ display: "flex", gap: space.xs, alignSelf: "stretch", overflowX: "auto" }}>
            {TABS.map((m) => {
              const on = m.key === tab.key;
              return (
                <Link
                  key={m.href}
                  href={m.href}
                  role="tab"
                  aria-selected={on}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: `0 ${space.sm + 4}px`,
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                    fontWeight: on ? 700 : 500,
                    color: on ? colors.brand : colors.muted,
                    borderBottom: `2px solid ${on ? colors.brand : "transparent"}`,
                  }}
                >
                  {m.label}
                </Link>
              );
            })}
          </nav>
          <div style={{ marginLeft: "auto", flexShrink: 0 }}>
            <UserMenu name={name} />
          </div>
        </header>
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          <aside
            style={{
              width: open ? SIDE_W : RAIL_W,
              flexShrink: 0,
              background: colors.sidebarBg,
              borderTopRightRadius: open ? sidebarCurve : sidebarCurve / 2,
              color: "#fff",
              overflow: "hidden",
              transition: `width ${EASE}, border-top-right-radius ${EASE}`,
            }}
          >
            <div
              style={{
                position: "sticky",
                top: 0,
                minHeight: `calc(100vh - ${FRAME * 2 + HEADER_H}px)`,
                display: "flex",
                flexDirection: "column",
                padding: open ? `${space.xl}px ${space.lg}px ${space.lg}px` : `${space.xl}px ${space.sm + 4}px ${space.lg}px`,
                transition: `padding ${EASE}`,
              }}
            >
              <Link
                href={tab.href}
                title={tab.label}
                style={{
                  display: "block",
                  textAlign: "center",
                  background: "#fff",
                  color: colors.brand,
                  fontWeight: 700,
                  borderRadius: 999,
                  padding: open ? `${space.sm + 2}px ${space.md}px` : `${space.sm + 2}px 0`,
                  textDecoration: "none",
                  boxShadow: "0 4px 12px rgba(9, 30, 80, 0.18)",
                  marginBottom: space.lg,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                }}
              >
                {open ? tab.label : tab.label.split(".")[0] || "⌂"}
              </Link>
              <ShipperBadge open={open} />
              <nav aria-label={tab.label} style={{ display: "flex", flexDirection: "column", gap: space.xs }}>
                {tab.side.map((s) => {
                  const on = isSideActive(pathname, tab, s.href);
                  return (
                    <Link
                      key={s.href}
                      href={s.href}
                      aria-current={on ? "page" : undefined}
                      aria-label={open ? undefined : s.label}
                      title={open ? undefined : s.label}
                      style={{
                        display: "flex",
                        gap: space.sm + 4,
                        alignItems: "center",
                        justifyContent: open ? "flex-start" : "center",
                        whiteSpace: "nowrap",
                        padding: `${space.sm + 2}px ${space.sm}px`,
                        borderRadius: 10,
                        textDecoration: "none",
                        color: on ? "#fff" : colors.sidebarText,
                        background: on ? colors.sidebarActive : "transparent",
                        fontWeight: on ? 700 : 500,
                      }}
                    >
                      <span aria-hidden style={{ width: 20, textAlign: "center", fontSize: font.lg }}>
                        {s.icon}
                      </span>
                      {open && s.label}
                    </Link>
                  );
                })}
              </nav>
              {!open && conn && (
                <Link
                  href="/connections/"
                  title={`${T.side.connections.all} ${conn.ok} / ${conn.total}`}
                  style={{ marginTop: "auto", color: "#fff", textDecoration: "none", textAlign: "center", fontSize: font.sm }}
                >
                  <Bar ratio={conn.total ? conn.ok / conn.total : 0} />
                  {`${conn.ok}/${conn.total}`}
                </Link>
              )}
              <div style={{ marginTop: "auto", paddingTop: space.xl, display: open ? "block" : "none" }}>
                <SideLabel>{`담당 ${tab.owner}`}</SideLabel>
                {conn && (
                  <Link
                    href="/connections/"
                    style={{ display: "block", color: "#fff", textDecoration: "none", marginTop: space.md }}
                  >
                    <div style={{ fontSize: font.md, fontWeight: 600 }}>{T.side.connections.all}</div>
                    <Bar ratio={conn.total ? conn.ok / conn.total : 0} />
                    <div style={{ fontSize: font.sm, color: colors.sidebarText }}>
                      {`${conn.ok} / ${conn.total} 연결됨`}
                    </div>
                  </Link>
                )}
              </div>
            </div>
          </aside>
          <main style={{ padding: `${space.xl - 8}px clamp(${space.md}px, 2.4vw, ${space.xl}px)`, flex: 1, minWidth: 0 }}>
            <ShipperGate pathname={pathname}>{children}</ShipperGate>
          </main>
        </div>
      </div>
    </div>
  );
}

/** 사이드바 아래 작은 대문자·자간 머리글 + 가는 흰 선. */
function SideLabel({ children }: { children: string }) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color: colors.sidebarText,
        display: "flex",
        alignItems: "center",
        gap: space.sm,
      }}
    >
      {children}
      <span style={{ flex: 1, height: 1, background: "rgba(255, 255, 255, 0.35)" }} />
    </div>
  );
}

/** 가는 흰 진행 막대. */
function Bar({ ratio }: { ratio: number }) {
  return (
    <div style={{ height: 4, borderRadius: 2, background: "rgba(255, 255, 255, 0.3)", margin: `${space.xs + 2}px 0` }}>
      <div style={{ width: `${Math.round(ratio * 100)}%`, height: "100%", borderRadius: 2, background: "#fff" }} />
    </div>
  );
}
