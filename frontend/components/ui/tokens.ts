// 색·간격 토큰. 화면은 이 값만 쓴다 (RULES 5-2, DESIGN 8장). 담당: 공통(KHS 관리)
export const colors = {
  text: "#1f2937",
  muted: "#6b7280",
  border: "#d0d7de",
  bg: "#ffffff",
  bgSubtle: "#f6f8fa",
  primary: "#2563c9", // 유일한 강조색 (테마 파랑)
  primarySoft: "#e8f0fc",
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
  // 대시보드 테마 (DESIGN 8장, HS 요청 11/25): 파란 바탕 위 큰 흰 판, 파란 사이드바, 연한 회청색 카드
  brand: "#2563c9", // 바탕·사이드바·강조 카드의 진한 파랑
  pageBg: "#2563c9",
  panelBg: "#ffffff",
  panelShadow: "0 24px 60px rgba(9, 30, 80, 0.35)",
  sidebarBg: "#2563c9",
  sidebarText: "rgba(255, 255, 255, 0.78)",
  sidebarActive: "rgba(255, 255, 255, 0.14)",
  cardBg: "#f1f4fa",
  cardShadow: "0 2px 8px rgba(37, 99, 201, 0.08)",
  rowHover: "#e8f0fc",
  line: "#e9edf3", // 표 가로줄·머리말 아래 구분선
  heading: "#374151", // 작은 대문자 머리글
} as const;

export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 40 } as const;

export const radius = 8;
export const cardRadius = 16;
export const panelRadius = 32;
export const sidebarCurve = 48;
export const font = { sm: 12, md: 14, lg: 16, xl: 20, xxl: 28 } as const;
