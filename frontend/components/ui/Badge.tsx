"use client";
// 배지: 색과 글자를 함께 쓴다(색만으로 구분하지 않음, DESIGN 8장). 담당: 공통(KHS 관리)
import type { ReactNode } from "react";

import { colors, font, space } from "@/components/ui/tokens";

export type Tone = "neutral" | "mismatch" | "edited" | "needInput" | "needCheck" | "ok" | "info";

const TONES: Record<Tone, { bg: string; fg: string }> = {
  neutral: { bg: colors.bgSubtle, fg: colors.muted },
  mismatch: { bg: colors.mismatchSoft, fg: colors.mismatch },
  edited: { bg: colors.editedSoft, fg: colors.edited },
  needInput: { bg: colors.needInput, fg: colors.needInputText },
  needCheck: { bg: colors.needCheckSoft, fg: colors.needCheck },
  ok: { bg: colors.okSoft, fg: colors.ok },
  info: { bg: colors.primarySoft, fg: colors.primary },
};

export function Badge({
  tone = "neutral",
  children,
  onClick,
  title,
  active = false,
}: {
  tone?: Tone;
  children: ReactNode;
  onClick?: () => void;
  title?: string;
  active?: boolean;
}) {
  const t = TONES[tone];
  const style = {
    display: "inline-flex",
    alignItems: "center",
    gap: space.xs,
    padding: `2px ${space.sm}px`,
    borderRadius: 999,
    background: t.bg,
    color: t.fg,
    fontSize: font.sm,
    border: `1px solid ${active ? t.fg : "transparent"}`,
    whiteSpace: "nowrap" as const,
  };
  if (onClick) {
    return (
      <button type="button" title={title} onClick={onClick} style={{ ...style, cursor: "pointer" }}>
        {children}
      </button>
    );
  }
  return (
    <span title={title} style={style}>
      {children}
    </span>
  );
}
