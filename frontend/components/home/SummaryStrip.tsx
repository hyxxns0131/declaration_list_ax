"use client";
// 검역이력 표 위 한 줄 요약: 확인 필요 · 신청 준비 · 실적 만료 임박 · 연결 n/전체 (각각 링크). 홈 숫자 카드의 줄임판.
// 메인 화면이 검역이력 표가 되면서(제안서 가이드라인 ④, 로직 점검 반영 11/25) 홈에 가지 않아도 보이게. 담당: KHS
import Link from "next/link";
import { useEffect, useState } from "react";

import { colors, font, space } from "@/components/ui/tokens";
import { connections } from "@/lib/api/core";
import { getAlerts } from "@/lib/api/registry";
import { DASH } from "@/lib/text/dashboard";
import type { Badges } from "@/lib/types/history";

export function SummaryStrip({ shipperId, badges }: { shipperId: string; badges: Badges | null }) {
  const [soon, setSoon] = useState<number | null>(null);
  const [conn, setConn] = useState<{ ok: number; total: number } | null>(null);

  useEffect(() => {
    if (!shipperId) return;
    getAlerts(shipperId, 90)
      .then((a) => setSoon(a.items.filter((i) => i.kind === "record").length))
      .catch(() => setSoon(null));
  }, [shipperId]);

  useEffect(() => {
    connections()
      .then((c) => setConn({ ok: c.rows.filter((r) => r.last?.state === "ok").length, total: c.rows.length }))
      .catch(() => setConn(null));
  }, []);

  const items: { label: string; value: string; href: string; color: string }[] = [
    {
      label: DASH.strip.needCheck,
      value: badges ? String(badges.need_check) : "–",
      href: "/history/review/",
      color: badges?.need_check ? colors.needCheck : colors.ok,
    },
    { label: DASH.strip.ready, value: badges ? String(badges.ready) : "–", href: "/history/", color: colors.ok },
    {
      label: DASH.strip.recordSoon,
      value: soon === null ? "–" : String(soon),
      href: "/registry/alerts/",
      color: soon ? colors.edited : colors.ok,
    },
    {
      label: DASH.strip.connections,
      value: conn ? `${conn.ok}/${conn.total}` : "–",
      href: "/connections/",
      color: colors.brand,
    },
  ];

  return (
    <nav
      aria-label={DASH.strip.title}
      style={{ display: "flex", gap: space.sm, flexWrap: "wrap", marginBottom: space.md }}
    >
      {items.map((it) => (
        <Link
          key={it.label}
          href={it.href}
          style={{
            display: "inline-flex",
            alignItems: "baseline",
            gap: space.xs + 2,
            padding: `${space.xs + 2}px ${space.md - 2}px`,
            borderRadius: 999,
            background: colors.cardBg,
            textDecoration: "none",
            color: colors.text,
            fontSize: font.sm,
          }}
        >
          {it.label}
          <strong style={{ fontSize: font.lg, color: it.color }}>{it.value}</strong>
        </Link>
      ))}
    </nav>
  );
}
