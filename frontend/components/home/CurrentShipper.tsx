"use client";
// 지금 작업 화주: 사이드바 표시(화주 바꾸기 → 탭 1 기업 설정) + 화주를 안 고른 채 다른 탭에 오면 "기업 설정에서 먼저 고르세요".
// 값은 lib/hooks/useShipper(모든 탭 공용). 그리기는 components/auth/AuthGate. 담당: KHS (HS 요청 11/25)
import Link from "next/link";
import type { ReactNode } from "react";

import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";

/** 화주를 몰라도 되는 화면: 홈(자체 안내), 기업 설정 첫 화면(여기서 고름), 연결 설정 */
const FREE = ["/connections"];
const PICK = "/settings/";

export function needsShipper(pathname: string): boolean {
  const p = pathname.endsWith("/") ? pathname : `${pathname}/`;
  return p !== "/" && p !== PICK && !FREE.some((f) => p.startsWith(f));
}

/** 사이드바 안 '작업 화주' 상자. open=false(아이콘 줄)이면 첫 글자만. */
export function ShipperBadge({ open }: { open: boolean }) {
  const { shipperName, chosen, loaded } = useShipper();
  if (!loaded) return null;
  const label = chosen ? shipperName : T.shipperPick.none;
  if (!open) {
    return (
      <Link
        href={PICK}
        title={`${T.shipperPick.current}: ${label} · ${T.shipperPick.change}`}
        style={{
          display: "grid",
          placeItems: "center",
          height: 40,
          borderRadius: 10,
          marginBottom: space.md,
          background: "rgba(255, 255, 255, 0.16)",
          color: "#fff",
          fontWeight: 800,
          textDecoration: "none",
        }}
      >
        {chosen ? shipperName.charAt(0) : "?"}
      </Link>
    );
  }
  return (
    <div
      style={{
        borderRadius: 12,
        padding: `${space.sm + 2}px ${space.md - 4}px`,
        marginBottom: space.md,
        background: "rgba(255, 255, 255, 0.14)",
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", color: colors.sidebarText }}>
        {T.shipperPick.current}
      </div>
      <div style={{ fontSize: font.lg, fontWeight: 800, color: "#fff", margin: "2px 0" }}>{label}</div>
      <Link href={PICK} style={{ fontSize: font.sm, color: "#fff", opacity: 0.9 }}>
        {chosen ? T.shipperPick.change : T.shipperPick.goPick} →
      </Link>
    </div>
  );
}

/** 화주가 필요한 화면인데 아직 안 골랐으면 안내만 보인다. */
export function ShipperGate({ pathname, children }: { pathname: string; children: ReactNode }) {
  const { chosen, loaded, shippers } = useShipper();
  if (!needsShipper(pathname) || !loaded || chosen || shippers.length === 0) return <>{children}</>;
  return (
    <Card>
      <EmptyState
        text={T.shipperPick.needFirst}
        action={
          <Link
            href={PICK}
            style={{
              display: "inline-block",
              background: colors.brand,
              color: "#fff",
              padding: `${space.sm}px ${space.lg}px`,
              borderRadius: 999,
              fontWeight: 700,
              textDecoration: "none",
            }}
          >
            {T.shipperPick.goPick}
          </Link>
        }
      />
    </Card>
  );
}
