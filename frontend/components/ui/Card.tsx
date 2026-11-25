// 대시보드 부품: 페이지 머리말 · 카드 · 숫자 카드 · 작은 머리글 (DESIGN 8장 테마). 담당: 공통(KHS 관리)
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { cardRadius, colors, font, space } from "@/components/ui/tokens";

/** 큰 파란 굵은 제목 + 설명 + 오른쪽 버튼들. 아래에 가는 구분선. */
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
        borderBottom: `1px solid ${colors.line}`,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, color: colors.brand, letterSpacing: "-0.01em" }}>
          {title}
        </h1>
        {sub && <p style={{ margin: `${space.xs + 2}px 0 0`, color: colors.muted, fontSize: font.sm }}>{sub}</p>}
      </div>
      {actions && (
        <div style={{ marginLeft: "auto", display: "flex", gap: space.sm, alignItems: "center", flexWrap: "wrap" }}>
          {actions}
        </div>
      )}
    </div>
  );
}

/** 작은 대문자·자간 머리글 (예: 섹션 이름). */
export function SectionTitle({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: space.sm, marginBottom: space.sm + 4 }}>
      <h2
        style={{
          margin: 0,
          fontSize: 13,
          fontWeight: 700,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: colors.heading,
        }}
      >
        {children}
      </h2>
      {actions && <div style={{ marginLeft: "auto", display: "flex", gap: space.sm }}>{actions}</div>}
    </div>
  );
}

/** 연한 회청색 카드(테두리 없음, 큰 둥근 모서리). */
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
        background: colors.cardBg,
        borderRadius: cardRadius,
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
  neutral: colors.text,
  info: colors.brand,
  ok: colors.ok,
  warn: colors.edited,
  danger: colors.mismatch,
  check: colors.needCheck,
} as const;

export type StatTone = keyof typeof ACCENT;

/**
 * 숫자 카드. 색과 함께 제목 글자로 뜻을 알린다(색만으로 구분하지 않음).
 * tone="info"는 강조 카드: 진한 파랑 바탕 + 흰 글자.
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
  const solid = tone === "info";
  const body = (
    <div
      style={{
        background: solid ? colors.brand : colors.cardBg,
        color: solid ? "#fff" : colors.text,
        borderRadius: cardRadius,
        boxShadow: solid ? "0 8px 20px rgba(37, 99, 201, 0.35)" : colors.cardShadow,
        padding: `${space.md + 2}px ${space.md + 4}px`,
        height: "100%",
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: solid ? "rgba(255, 255, 255, 0.85)" : colors.muted,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: font.xxl,
          fontWeight: 800,
          color: solid ? "#fff" : ACCENT[tone],
          margin: `${space.sm}px 0 ${space.xs}px`,
        }}
      >
        {value ?? "–"}
      </div>
      {hint && (
        <div style={{ fontSize: font.sm, color: solid ? "rgba(255, 255, 255, 0.85)" : colors.muted }}>{hint}</div>
      )}
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
