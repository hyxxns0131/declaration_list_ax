// 검역 리스트 탭 안에서만 쓰는 모양 상수 (공통 tokens.ts는 고치지 않는다). 담당: KHS (검역 리스트 탭 0단계)
import type { CSSProperties } from "react";

import { colors, font, space } from "@/components/ui/tokens";

/** 주 버튼 파랑(#1a73e8 근처). 테마 파랑과 맞춘다 */
export const LIST_BLUE = colors.brand;
export const PILL_HEIGHT = 44;

const pillBase: CSSProperties = {
  height: PILL_HEIGHT,
  padding: `0 ${space.lg - 2}px`,
  borderRadius: 999,
  fontSize: font.md,
  fontWeight: 700,
  display: "inline-flex",
  alignItems: "center",
  gap: space.xs + 2,
  cursor: "pointer",
  whiteSpace: "nowrap",
  textDecoration: "none",
};

export const pillPrimary: CSSProperties = { ...pillBase, background: LIST_BLUE, color: "#fff", border: `1px solid ${LIST_BLUE}` };
export const pillSecondary: CSSProperties = { ...pillBase, background: "#fff", color: colors.text, border: `1px solid ${colors.border}` };
export const pillDisabled: CSSProperties = { opacity: 0.5, cursor: "not-allowed" };

/** 칸 상태: 색 + 짧은 글자를 함께 */
export const STATE_STYLE = {
  mismatch: { color: colors.mismatch, bg: colors.mismatchSoft, text: "불일치" },
  manual: { color: colors.edited, bg: colors.editedSoft, text: "사람이 고름" },
  needInput: { color: colors.needInputText, bg: colors.needInput, text: "자료 추가 필요" },
  review: { color: colors.needCheck, bg: colors.needCheckSoft, text: "검수 대기" },
} as const;
