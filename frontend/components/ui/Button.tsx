"use client";
// 공통 버튼. 담당: 공통(KHS 관리)
import type { ButtonHTMLAttributes, CSSProperties } from "react";

import { colors, font, radius, space } from "@/components/ui/tokens";

type Variant = "primary" | "default" | "danger" | "ghost";

const VARIANTS: Record<Variant, CSSProperties> = {
  primary: { background: colors.primary, color: "#fff", borderColor: colors.primary },
  default: { background: colors.bg, color: colors.text, borderColor: colors.border },
  danger: { background: colors.bg, color: colors.mismatch, borderColor: colors.mismatch },
  ghost: { background: "transparent", color: colors.primary, borderColor: "transparent" },
};

export function Button({
  variant = "default",
  small = false,
  style,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; small?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      style={{
        border: "1px solid",
        borderRadius: radius,
        padding: small ? `2px ${space.sm}px` : `${space.xs + 2}px ${space.md - 2}px`,
        fontSize: small ? font.sm : font.md,
        cursor: rest.disabled ? "not-allowed" : "pointer",
        opacity: rest.disabled ? 0.5 : 1,
        whiteSpace: "nowrap",
        ...VARIANTS[variant],
        ...style,
      }}
    />
  );
}
