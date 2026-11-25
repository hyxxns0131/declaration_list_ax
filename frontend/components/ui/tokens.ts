// 색·간격 토큰. 화면은 이 값만 쓴다 (RULES 5-2, DESIGN 8장). 담당: 공통(KHS 관리)
export const colors = {
  text: "#1f2328",
  muted: "#6b7280",
  border: "#d0d7de",
  bg: "#ffffff",
  bgSubtle: "#f6f8fa",
  primary: "#2563eb",
  primarySoft: "#eff6ff",
  mismatch: "#dc2626", // 빨강: 서류와 다름
  mismatchSoft: "#fef2f2",
  edited: "#ea580c", // 주황: 담당자가 고친 값이 서류와 다름
  editedSoft: "#fff7ed",
  approved: "#9ca3af", // 회색 글자: 승인 완료
  needInput: "#fef9c3", // 노랑 배경: 자료 추가 필요
  needInputText: "#854d0e",
  needCheck: "#7c3aed", // 보라 글자: 확인 필요(판단 근거 부족)
  needCheckSoft: "#f5f3ff",
  expired: "#9ca3af", // 취소선 + 회색: 만료 실적
  ok: "#15803d",
  okSoft: "#f0fdf4",
  overlay: "rgba(15, 23, 42, 0.35)",
} as const;

export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 40 } as const;

export const radius = 6;
export const font = { sm: 12, md: 14, lg: 16, xl: 20 } as const;
