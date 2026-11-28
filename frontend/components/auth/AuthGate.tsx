"use client";
// 로그인 확인: 로그인 안 했으면 /login으로 (DESIGN 2-1). 대시보드 틀(연한 회청 바탕 위 큰 둥근 흰 판, 위 탭, 왼쪽 흰 사이드바 = 지금 탭의 세부 메뉴. 홈만 위쪽 파랑 띠 + 흰 카드. HS 요청 11/28)도 여기서 그린다. 탭·메뉴 목록은 lib/nav.ts. 담당: KHS
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { UserMenu } from "@/components/auth/UserMenu";
import { ShipperBadge, ShipperGate } from "@/components/home/CurrentShipper";
import { SideStepMark } from "@/components/review/ListStepper";
import { colors, font, homeCardRadius, panelRadius, space } from "@/components/ui/tokens";
import { ApiError, tokenStore } from "@/lib/api/client";
import { connections, me } from "@/lib/api/core";
import { MAIN_PATH, TABS, currentTab, isSideActive } from "@/lib/nav";
import { T } from "@/lib/text/common";

type State = "checking" | "in" | "error";

const FRAME = 28; // 파란 바탕과 흰 판 사이 여백
const SIDE_W = 240;
const RAIL_W = 72; // 닫힌 사이드바(아이콘만)
const SIDEBAR_KEY = "dl_sidebar_open";
const LANDED_KEY = "dl_landed"; // sessionStorage: 처음 화면 이동을 한 번만
const EASE = "200ms ease";
const HEADER_H = 76;
const BAND_H = 340; // 홈 파랑 띠 높이: 머리줄 + 내용 위쪽 절반쯤

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname.startsWith("/login");
  const [state, setState] = useState<State>("checking");
  const [name, setName] = useState("");
  const [conn, setConn] = useState<{ ok: number; total: number } | null>(null);
  // 사이드바 열림(240px) / 닫힘(아이콘만 72px). 브라우저에 기억, 처음엔 넓은 화면만 열림
  const [open, setOpen] = useState(true);

  useEffect(() => {
    // 고른 적이 있으면 그대로. 처음이면 넓은 화면만 열되, 메인 화면(검역이력 표)에서는 표 폭을 위해 접는다
    const saved = window.localStorage.getItem(SIDEBAR_KEY);
    setOpen(saved === null ? window.innerWidth >= 1024 && !pathname.startsWith(MAIN_PATH) : saved === "1");
  }, [pathname]);

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
        // 이 창에서 처음 연 화면이 홈이면 메인 화면(검역이력 표)으로. 그 뒤 [홈] 탭은 그대로 홈(전체 현황)
        if (!window.sessionStorage.getItem(LANDED_KEY)) {
          window.sessionStorage.setItem(LANDED_KEY, "1");
          if (pathname === "/") router.replace(MAIN_PATH);
        }
        connections() // 사이드바 아래 연결 막대: 마지막 검사 결과 기준(새 검사는 하지 않음)
          .then((c) => setConn({ ok: c.rows.filter((r) => r.last?.state === "ok").length, total: c.rows.length }))
          .catch(() => setConn(null));
      })
      .catch((e: unknown) => setState(e instanceof ApiError && e.status === 0 ? "error" : "checking"));
  }, [isLogin, pathname, router]);

  if (isLogin) return <>{children}</>;
  if (state === "error") return <p style={{ padding: space.lg, color: colors.text }}>{T.networkError}</p>;
  if (state === "checking") return <p style={{ padding: space.lg, color: colors.muted }}>{T.loading}</p>;

  const tab = currentTab(pathname);
  // 홈(전체 현황)만 포털형: 위쪽 진한 파랑 띠 위에 흰 글자 머리줄, 흰 카드가 띠에 겹쳐 뜬다 (HS 요청 11/28)
  const home = tab.key === "home";
  const onBand = home ? "#fff" : colors.text;
  const frame = `clamp(12px, 1.6vw, ${FRAME}px)`;

  return (
    <div
      className={home ? "shell shell-home" : "shell"}
      style={{
        minHeight: "100vh",
        background: home ? `${colors.homeBand} top / 100% ${BAND_H}px no-repeat, ${colors.pageBg}` : colors.pageBg,
        padding: home ? 0 : frame,
      }}
    >
      <div
        style={{
          background: home ? "transparent" : colors.panelBg,
          borderRadius: home ? 0 : panelRadius,
          boxShadow: home ? "none" : colors.panelShadow,
          overflow: home ? "visible" : "hidden",
          minHeight: home ? "100vh" : `calc(100vh - 2 * ${frame})`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <header
          style={{
            display: "flex",
            alignItems: "center",
            gap: space.lg,
            height: HEADER_H,
            paddingRight: space.xl,
            borderBottom: home ? "1px solid rgba(255, 255, 255, 0.16)" : `1px solid ${colors.line}`,
          }}
        >
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
              background: home ? "rgba(255, 255, 255, 0.16)" : colors.bgSubtle,
              color: home ? "#fff" : colors.muted,
              fontSize: 18,
              cursor: "pointer",
            }}
          >
            ☰
          </button>
          <Link
            href={MAIN_PATH}
            style={{
              width: SIDE_W - 56,
              flexShrink: 0,
              color: onBand,
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
                background: home ? "#fff" : colors.primary,
                color: home ? colors.homeAccent : "#fff",
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
              const fg = home ? (on ? "#fff" : "rgba(255, 255, 255, 0.78)") : on ? colors.primary : colors.muted;
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
                    color: fg,
                    borderBottom: `3px solid ${on ? (home ? "#fff" : colors.primary) : "transparent"}`,
                  }}
                >
                  {m.label}
                </Link>
              );
            })}
          </nav>
          <div style={{ marginLeft: "auto", flexShrink: 0 }}>
            <UserMenu name={name} onBand={home} />
          </div>
        </header>
        <div
          style={{
            display: "flex",
            flex: 1,
            minHeight: 0,
            gap: home ? space.lg : 0,
            padding: home ? `${space.lg}px clamp(${space.md}px, 2vw, ${space.xl}px) ${space.xl}px` : 0,
          }}
        >
          <aside
            style={{
              width: open ? SIDE_W : RAIL_W,
              flexShrink: 0,
              background: colors.sidebarBg,
              borderRight: home ? "none" : `1px solid ${colors.line}`,
              borderRadius: home ? homeCardRadius : 0,
              boxShadow: home ? colors.cardShadow : "none",
              alignSelf: home ? "flex-start" : "stretch",
              color: colors.text,
              overflow: "hidden",
              transition: `width ${EASE}`,
            }}
          >
            <div
              style={{
                position: "sticky",
                top: 0,
                minHeight: home ? 0 : `calc(100vh - ${FRAME * 2 + HEADER_H}px)`,
                display: "flex",
                flexDirection: "column",
                padding: open ? `${space.lg}px ${space.md}px ${space.lg}px` : `${space.lg}px ${space.sm + 4}px ${space.lg}px`,
                transition: `padding ${EASE}`,
              }}
            >
              <Link
                href={tab.href}
                title={tab.label}
                style={{
                  display: "block",
                  textAlign: open ? "left" : "center",
                  color: colors.heading,
                  fontWeight: 800,
                  fontSize: font.md,
                  padding: open ? `0 ${space.sm}px` : 0,
                  textDecoration: "none",
                  marginBottom: space.md,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
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
                        padding: `${space.sm + 2}px ${space.sm + 4}px`,
                        borderRadius: 999,
                        textDecoration: "none",
                        color: on ? colors.sidebarActiveText : colors.sidebarText,
                        background: on ? colors.sidebarActive : "transparent",
                        fontWeight: on ? 700 : 500,
                      }}
                    >
                      <span aria-hidden style={{ width: 20, textAlign: "center", fontSize: font.lg }}>
                        {s.icon}
                      </span>
                      {open && s.label}
                      {open && s.step !== undefined && <SideStepMark step={s.step} />}
                    </Link>
                  );
                })}
              </nav>
              {!open && conn && (
                <Link
                  href="/connections/"
                  title={`${T.side.connections.all} ${conn.ok} / ${conn.total}`}
                  style={{
                    marginTop: home ? space.lg : "auto",
                    color: colors.muted,
                    textDecoration: "none",
                    textAlign: "center",
                    fontSize: font.sm,
                  }}
                >
                  <Bar ratio={conn.total ? conn.ok / conn.total : 0} />
                  {`${conn.ok}/${conn.total}`}
                </Link>
              )}
              <div style={{ marginTop: home ? 0 : "auto", paddingTop: space.xl, display: open ? "block" : "none" }}>
                <SideLabel>{`담당 ${tab.owner}`}</SideLabel>
                {conn && (
                  <Link
                    href="/connections/"
                    style={{
                      display: "block",
                      color: colors.text,
                      textDecoration: "none",
                      marginTop: space.md,
                      background: colors.bgSubtle,
                      borderRadius: 12,
                      padding: `${space.sm + 2}px ${space.md - 4}px`,
                    }}
                  >
                    <div style={{ fontSize: font.md, fontWeight: 600 }}>{T.side.connections.all}</div>
                    <Bar ratio={conn.total ? conn.ok / conn.total : 0} />
                    <div style={{ fontSize: font.sm, color: colors.muted }}>{`${conn.ok} / ${conn.total} 연결됨`}</div>
                  </Link>
                )}
              </div>
            </div>
          </aside>
          <main
            style={{
              // 메인 화면(표)은 위 여백을 줄여 행을 더 보이게. 홈은 바깥 틀이 여백을 준다
              padding: home
                ? 0
                : pathname.startsWith(MAIN_PATH)
                  ? `${space.sm + 4}px clamp(${space.md}px, 1.6vw, ${space.lg}px)`
                  : `${space.xl - 8}px clamp(${space.md}px, 2.4vw, ${space.xl}px)`,
              flex: 1,
              minWidth: 0,
              background: home ? "transparent" : colors.mainBg,
            }}
          >
            <ShipperGate pathname={pathname}>{children}</ShipperGate>
          </main>
        </div>
      </div>
    </div>
  );
}

/** 사이드바 아래 작은 대문자·자간 머리글 + 가는 선. */
function SideLabel({ children }: { children: string }) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color: colors.sidebarText,
        padding: `0 ${space.sm}px`,
        display: "flex",
        alignItems: "center",
        gap: space.sm,
      }}
    >
      {children}
      <span style={{ flex: 1, height: 1, background: colors.line }} />
    </div>
  );
}

/** 가는 진행 막대(회색 바탕 + 하늘색). */
function Bar({ ratio }: { ratio: number }) {
  return (
    <div style={{ height: 4, borderRadius: 2, background: "#dfe7f1", margin: `${space.xs + 2}px 0` }}>
      <div style={{ width: `${Math.round(ratio * 100)}%`, height: "100%", borderRadius: 2, background: colors.primary }} />
    </div>
  );
}
