"use client";
// 메인 화면(검역이력 표) 도구 줄 (DESIGN 3-3, 로직 점검 반영 11/25): 한 줄에
// [검역이력 · 작업 화주] [상태 칩: 전체·확인 필요·진행 중·신청 준비] [실적 만료 임박 · 연결 n/전체] … [버튼 4개].
// 화주는 기업 설정 첫 화면에서 고른다(이 줄에서는 이름만, 누르면 기업 설정). 담당: KHS
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { colors, font, radius, space } from "@/components/ui/tokens";
import { connections } from "@/lib/api/core";
import { getAlerts } from "@/lib/api/registry";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { Badges } from "@/lib/types/history";

export type HomeFilter = "all" | "attention" | "progress" | "ready";

function Chip({
  on,
  label,
  count,
  color,
  onClick,
  title,
}: {
  on: boolean;
  label: string;
  count?: number;
  color: string;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      title={title}
      onClick={onClick}
      style={{
        border: `1px solid ${on ? colors.brand : "transparent"}`,
        background: on ? colors.primarySoft : "transparent",
        color: colors.text,
        borderRadius: 999,
        padding: `2px ${space.sm + 2}px`,
        fontSize: font.sm,
        cursor: "pointer",
        whiteSpace: "nowrap",
      }}
    >
      {label}
      {count !== undefined && <strong style={{ marginLeft: 4, color }}>{count}</strong>}
    </button>
  );
}

const sep = <span aria-hidden style={{ width: 1, height: 18, background: colors.line }} />;

export function TopBar({
  shipperId,
  shipperName,
  badges,
  filter,
  onFilter,
  onUpload,
  onRefresh,
  refreshing,
  itemSheet,
}: {
  shipperId: string;
  shipperName: string;
  badges: Badges | null;
  filter: HomeFilter;
  onFilter: (f: HomeFilter) => void;
  onUpload: () => void;
  onRefresh: () => void;
  refreshing: boolean;
  itemSheet: ReactNode;
}) {
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

  const toggle = (f: HomeFilter) => onFilter(filter === f ? "all" : f);
  const small = { fontSize: font.sm, color: colors.muted, textDecoration: "none", whiteSpace: "nowrap" as const };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: space.sm,
        flexWrap: "wrap",
        padding: `${space.xs}px 0 ${space.sm}px`,
        borderBottom: `1px solid ${colors.line}`,
        marginBottom: space.xs,
      }}
    >
      <strong style={{ fontSize: font.lg, color: colors.brand }}>{HOME.bar.title}</strong>
      <Link href="/settings/" title={HOME.bar.changeShipper} style={{ ...small, color: colors.text }}>
        {shipperName || T.pickShipper} ▾
      </Link>
      {sep}
      <Chip on={filter === "all"} label={HOME.bar.all} count={badges?.total} color={colors.text} onClick={() => onFilter("all")} />
      <Chip
        on={filter === "attention"}
        label={HOME.bar.needCheck}
        count={badges?.need_check}
        color={badges?.need_check ? colors.needCheck : colors.ok}
        onClick={() => toggle("attention")}
        title="확인 필요·불일치·자료 추가 필요 행만 보기"
      />
      <Chip
        on={filter === "progress"}
        label={HOME.bar.progress}
        count={badges?.in_progress}
        color={colors.brand}
        onClick={() => toggle("progress")}
        title="신고건으로 묶인(신청 전·승인 전) 행만 보기"
      />
      <Chip
        on={filter === "ready"}
        label={HOME.bar.ready}
        count={badges?.ready}
        color={colors.ok}
        onClick={() => toggle("ready")}
        title="반입일이 들어와 신청할 수 있는 행만 보기"
      />
      {badges && badges.mismatch > 0 && <span style={{ ...small, color: colors.mismatch }}>■ {HOME.badges.mismatch(badges.mismatch)}</span>}
      {badges && badges.edited > 0 && <span style={{ ...small, color: colors.edited }}>✎ {HOME.badges.edited(badges.edited)}</span>}
      {sep}
      <Link href="/registry/alerts/" style={small}>
        {HOME.bar.recordSoon} <strong style={{ color: soon ? colors.edited : colors.ok }}>{soon ?? "–"}</strong>
      </Link>
      <Link href="/connections/" style={small}>
        {HOME.bar.connections} <strong style={{ color: colors.brand }}>{conn ? `${conn.ok}/${conn.total}` : "–"}</strong>
      </Link>
      <span style={{ marginLeft: "auto", display: "flex", gap: space.sm, alignItems: "center" }}>
        <Button variant="primary" onClick={onUpload} disabled={!shipperId}>
          {HOME.buttons.upload}
        </Button>
        {itemSheet}
        <Button onClick={onRefresh} disabled={!shipperId || refreshing} title={HOME.buttons.refresh}>
          ⟳ {refreshing ? T.loading : HOME.buttons.refresh}
        </Button>
        <Link
          href="/settings/rules/"
          title={HOME.bar.settingsTitle}
          style={{
            border: `1px solid ${colors.border}`,
            borderRadius: radius,
            padding: `${space.xs + 2}px ${space.md - 2}px`,
            color: colors.text,
            textDecoration: "none",
            fontSize: font.md,
            whiteSpace: "nowrap",
          }}
        >
          ⚙ {HOME.buttons.settings}
        </Link>
      </span>
    </div>
  );
}
