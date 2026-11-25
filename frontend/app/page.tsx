"use client";
// 메인 홈 — 전체 현황 대시보드 (DESIGN 2-2). 각 탭 담당 API의 숫자만 모아 보여 준다. 계산하지 않는다. 담당: KHS
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, PageHeader, StatCard, StatGrid } from "@/components/ui/Card";
import { EmptyState, ErrorLine } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { integrations } from "@/lib/api/core";
import { getBadges } from "@/lib/api/history";
import { getDeclarations } from "@/lib/api/judge";
import { getAlerts, getFactories, getRecords } from "@/lib/api/registry";
import { fmtDate } from "@/lib/format";
import { useShipper } from "@/lib/hooks/useShipper";
import { DASH } from "@/lib/text/dashboard";
import type { Integrations } from "@/lib/types/core";
import type { Badges, Declaration } from "@/lib/types/history";
import type { AlertsOut, FactoryCode, PreciseRecord } from "@/lib/types/registry";

const td = { padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.md } as const;

export default function HomePage() {
  const { shipperId, shipperName, chosen, loaded, error: shipperError } = useShipper();
  const [records, setRecords] = useState<PreciseRecord[] | null>(null);
  const [alerts, setAlerts] = useState<AlertsOut | null>(null);
  const [factories, setFactories] = useState<FactoryCode[] | null>(null);
  const [badges, setBadges] = useState<Badges | null>(null);
  const [decls, setDecls] = useState<Declaration[] | null>(null);
  const [info, setInfo] = useState<Integrations | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    integrations().then(setInfo).catch(() => setInfo(null));
    getFactories().then(setFactories).catch(setError);
  }, []);

  const load = useCallback(() => {
    if (!shipperId || !chosen) return;
    setError(null);
    // 한 곳이 실패해도 나머지 카드는 보이게 따로 부른다
    getRecords({ shipperId, status: "" }).then(setRecords).catch(setError);
    getAlerts(shipperId, 90).then(setAlerts).catch(setError);
    getBadges(shipperId).then(setBadges).catch(setError);
    getDeclarations(shipperId).then(setDecls).catch(setError);
  }, [shipperId, chosen]);

  useEffect(load, [load]);

  const recordSoon = alerts?.items.filter((a) => a.kind === "record").length ?? null;
  const factorySoon = factories ? factories.filter((f) => f.status === "만료 임박").length : null;
  const groupWarn = decls ? decls.filter((d) => d.warnings.length > 0).length : null;

  return (
    <div>
      <PageHeader title={DASH.title} sub={DASH.sub} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      {/* 작업 화주: 고르기·추가·삭제는 탭 1 기업 설정 첫 화면 (HS 요청 11/25) */}
      {loaded && chosen && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: space.md,
            flexWrap: "wrap",
            background: colors.brand,
            color: "#fff",
            borderRadius: 16,
            padding: `${space.md}px ${space.lg}px`,
            marginBottom: space.lg,
          }}
        >
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", opacity: 0.85 }}>{DASH.shipperNow}</span>
          <strong style={{ fontSize: font.xl }}>{shipperName}</strong>
          <Link href="/settings/" style={{ marginLeft: "auto", color: "#fff", fontWeight: 600 }}>
            {DASH.shipperChange}
          </Link>
        </div>
      )}
      {loaded && !chosen && (
        <Card>
          <EmptyState
            text={DASH.shipperFirst}
            action={
              <Link
                href="/settings/"
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
                {DASH.shipperGo}
              </Link>
            }
          />
        </Card>
      )}

      {chosen && (
        <>
          <h3 style={{ margin: `0 0 ${space.sm}px`, fontSize: font.md, color: colors.muted }}>{DASH.sections.registry}</h3>
          <StatGrid>
            <StatCard label={DASH.stats.records} value={records?.length ?? null} hint={DASH.hints.records} tone="info" href="/registry/" />
            <StatCard label={DASH.stats.recordsSoon} value={recordSoon} hint={DASH.hints.soon} tone={recordSoon ? "warn" : "ok"} href="/registry/alerts/" />
            <StatCard label={DASH.stats.factorySoon} value={factorySoon} hint={DASH.hints.soon} tone={factorySoon ? "warn" : "ok"} href="/registry/factories/" />
          </StatGrid>

          <h3 style={{ margin: `0 0 ${space.sm}px`, fontSize: font.md, color: colors.muted }}>{DASH.sections.judge}</h3>
          <StatGrid>
            <StatCard label={DASH.stats.groups} value={decls?.length ?? null} hint={DASH.hints.groups} tone="info" href="/judge/" />
            <StatCard label={DASH.stats.groupWarn} value={groupWarn} hint={DASH.hints.groupWarn} tone={groupWarn ? "danger" : "ok"} href="/judge/" />
          </StatGrid>

          <h3 style={{ margin: `0 0 ${space.sm}px`, fontSize: font.md, color: colors.muted }}>{DASH.sections.list}</h3>
          <StatGrid>
            <StatCard label={DASH.stats.rows} value={badges?.total ?? null} tone="info" href="/history/" />
            <StatCard label={DASH.stats.needCheck} value={badges?.need_check ?? null} hint={DASH.hints.needCheck} tone={badges?.need_check ? "check" : "ok"} href="/history/review/" />
            <StatCard label={DASH.stats.ready} value={badges?.ready ?? null} hint={DASH.hints.ready} tone="ok" href="/history/" />
          </StatGrid>

          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(260px, 1fr)", gap: space.md, alignItems: "start" }}>
            <Card title={DASH.sections.upcoming} actions={<Link href="/registry/alerts/">만료 알림 →</Link>}>
              {alerts && alerts.items.length === 0 && <p style={{ color: colors.muted, margin: 0 }}>{DASH.upcomingEmpty}</p>}
              {alerts && alerts.items.length > 0 && (
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <tbody>
                    {alerts.items.slice(0, 6).map((a) => (
                      <tr key={`${a.kind}-${a.record_no}`}>
                        <td style={td}>
                          <Badge tone={a.kind === "record" ? "info" : "needCheck"}>{DASH.kind[a.kind]}</Badge>
                        </td>
                        <td style={td}>{a.record_no}</td>
                        <td style={{ ...td, color: colors.muted }}>{a.factory}</td>
                        <td style={td}>{fmtDate(a.expires_on)}</td>
                        <td style={{ ...td, fontWeight: 700, color: a.days_left <= 30 ? colors.mismatch : colors.edited }}>D-{a.days_left}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>

            <div>
              <Card title={DASH.sections.system}>
                {info &&
                  (["llm", "unipass", "drive", "gmail", "supabase", "mfds"] as const).map((k) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: `${space.xs}px 0`, fontSize: font.md }}>
                      <span>{DASH.integrations[k]}</span>
                      <Badge tone={info[k].ok ? "ok" : "neutral"} title={info[k].reason}>
                        {info[k].ok ? `● ${DASH.integrations.on}` : `○ ${DASH.integrations.off}`}
                        {k === "unipass" && ` (${info.unipass.mode})`}
                      </Badge>
                    </div>
                  ))}
              </Card>
              <Card title={DASH.sections.flow}>
                <ol style={{ margin: 0, paddingLeft: space.lg }}>
                  {DASH.flow.map((f) => (
                    <li key={f.step} style={{ marginBottom: space.xs }}>
                      <Link href={f.href} style={{ fontWeight: 600 }}>
                        {f.step}
                      </Link>
                      <div style={{ fontSize: font.sm, color: colors.muted }}>{f.text}</div>
                    </li>
                  ))}
                </ol>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
