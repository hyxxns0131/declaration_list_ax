// 대시보드 부품: 페이지 머리말 · 카드 · 숫자 카드 · 작은 머리글 (DESIGN 8장 테마, HS 요청 11/28 재디자인).
// 홈 파랑 띠 위 모양(흰 제목·작은 모서리·제목 밑 파랑 줄)은 globals.css의 .shell-home 변수로 바꾼다. 담당: 공통(KHS 관리)
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { cardRadius, colors, font, space } from "@/components/ui/tokens";

/** 큰 남색 굵은 제목 + 설명 + 오른쪽 버튼들. 아래에 가는 구분선(홈은 띠 위 흰 글자). */
export function PageHeader({ title, sub, actions }: { title: string; sub?: string; actions?: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-end",
        gap: space.md,
        flexWrap: "wrap",
        paddingBottom: space.md,
        marginBottom: space.lg,
        borderBottom: `1px solid var(--ph-line, ${colors.line})`,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <h1
          style={{
            margin: 0,
            fontSize: 26,
            fontWeight: 800,
            color: `var(--ph-title, ${colors.heading})`,
            letterSpacing: "-0.01em",
          }}
        >
          {title}
        </h1>
        {sub && (
          <p style={{ margin: `${space.xs + 2}px 0 0`, color: `var(--ph-sub, ${colors.muted})`, fontSize: font.sm }}>{sub}</p>
        )}
      </div>
      {actions && (
        <div style={{ marginLeft: "auto", display: "flex", gap: space.sm, alignItems: "center", flexWrap: "wrap" }}>
          {actions}
        </div>
      )}
    </div>
  );
}

/** 카드 머리글 (예: 섹션 이름). 진한 남색 굵은 글자. 홈에서는 아래에 짧은 파랑 줄(.card-title). */
export function SectionTitle({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: space.sm, marginBottom: space.sm + 4 }}>
      <h2 className="card-title" style={{ margin: 0, fontSize: 15, fontWeight: 700, color: colors.heading }}>
        {children}
      </h2>
      {actions && <div style={{ marginLeft: "auto", display: "flex", gap: space.sm }}>{actions}</div>}
    </div>
  );
}

/** 흰 카드: 아주 연한 테두리·그림자, 둥근 모서리(홈은 작은 모서리). */
export function Card({
  title,
  actions,
  children,
  style,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <section
      style={{
        background: colors.surface,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: `var(--card-radius, ${cardRadius}px)`,
        boxShadow: colors.cardShadow,
        padding: space.lg - 4,
        marginBottom: space.lg,
        minWidth: 0,
        ...style,
      }}
    >
      {(title || actions) && <SectionTitle actions={actions}>{title}</SectionTitle>}
      {children}
    </section>
  );
}

const ACCENT = {
  neutral: colors.heading,
  info: `var(--stat-accent, ${colors.brand})`, // 강조 숫자: 파랑
  ok: colors.heading, // 정상은 진한 남색 숫자(제목 글자로 뜻을 알림)
  warn: colors.edited,
  danger: colors.mismatch,
  check: colors.needCheck,
} as const;

export type StatTone = keyof typeof ACCENT;

/**
 * 숫자 카드. 색과 함께 제목 글자로 뜻을 알린다(색만으로 구분하지 않음).
 * 흰 카드 + 굵은 숫자. tone="info"는 파랑 숫자, warn·danger·check는 상태 색 숫자.
 */
export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
  href,
}: {
  label: string;
  value: number | string | null;
  hint?: string;
  tone?: StatTone;
  href?: string;
}) {
  const body = (
    <div
      className="stat-card"
      style={{
        background: colors.surface,
        color: colors.text,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: `var(--card-radius, ${cardRadius}px)`,
        boxShadow: colors.cardShadow,
        padding: `${space.md + 2}px ${space.md + 4}px`,
        height: "100%",
      }}
    >
      <div style={{ fontSize: font.sm, fontWeight: 600, color: colors.muted }}>{label}</div>
      <div
        style={{
          fontSize: 30,
          fontWeight: 800,
          color: ACCENT[tone],
          margin: `${space.sm}px 0 ${space.xs}px`,
          fontVariantNumeric: "tabular-nums",
          letterSpacing: "-0.02em",
        }}
      >
        {value ?? "–"}
      </div>
      {hint && <div style={{ fontSize: font.sm, color: colors.muted }}>{hint}</div>}
    </div>
  );
  return href ? (
    <Link href={href} style={{ textDecoration: "none", color: "inherit" }}>
      {body}
    </Link>
  ) : (
    body
  );
}

export function StatGrid({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))",
        gap: space.md,
        marginBottom: space.lg,
      }}
    >
      {children}
    </div>
  );
}
