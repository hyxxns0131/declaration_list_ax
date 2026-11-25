"use client";
// 빈·로딩·오류 상태 (DESIGN 8장 "빈·로딩·오류 상태를 모든 화면에"). 담당: 공통(KHS 관리)
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { colors, font, space } from "@/components/ui/tokens";
import { ApiError } from "@/lib/api/client";
import { T } from "@/lib/text/common";

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.status === 0 ? T.networkError : e.message;
  return T.unknownError;
}

export function Skeleton({ lines = 5 }: { lines?: number }) {
  return (
    <div aria-busy="true" aria-label={T.loading}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          style={{
            height: 28,
            margin: `${space.xs}px 0`,
            borderRadius: 4,
            background: colors.bgSubtle,
          }}
        />
      ))}
    </div>
  );
}

export function EmptyState({ text, action }: { text: string; action?: ReactNode }) {
  return (
    <div style={{ padding: space.xl, textAlign: "center", color: colors.muted }}>
      <p style={{ margin: 0, marginBottom: space.md }}>{text}</p>
      {action}
    </div>
  );
}

export function ErrorLine({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        gap: space.sm,
        padding: `${space.sm}px ${space.md}px`,
        margin: `${space.sm}px 0`,
        background: colors.mismatchSoft,
        color: colors.mismatch,
        borderRadius: 4,
        fontSize: font.md,
      }}
    >
      <span>■ {errorText(error)}</span>
      {onRetry && (
        <Button small onClick={onRetry} style={{ marginLeft: "auto" }}>
          {T.retry}
        </Button>
      )}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  return (
    <div
      style={{
        padding: `${space.xs + 2}px ${space.md}px`,
        margin: `${space.xs}px 0`,
        borderRadius: 4,
        fontSize: font.sm,
        background: tone === "warn" ? colors.needInput : colors.primarySoft,
        color: tone === "warn" ? colors.needInputText : colors.primary,
      }}
    >
      {children}
    </div>
  );
}
