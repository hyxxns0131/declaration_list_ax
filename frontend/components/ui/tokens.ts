// 색·간격 토큰. 화면은 이 값만 쓴다 (RULES 5-2, DESIGN 8장). 담당: 공통(KHS 관리)
export const colors = {
  text: "#1e2a44", // 본문·제목: 진한 남색
  muted: "#6b7a90", // 흐린 회청색
  border: "#e1e8f1",
  bg: "#ffffff",
  bgSubtle: "#f4f7fb",
  primary: "#3a9be8", // 유일한 강조색 (하늘색): 주 버튼·지금 탭·링크
  primarySoft: "#e7f2fd", // 연한 하늘색: 고른 줄·사이드바 지금 메뉴
  // 상태 색: 뜻은 그대로(빨강 불일치·노랑 자료 추가 필요·주황 고친 값·초록 정상), 채도만 조금 낮춤
  mismatch: "#d64545", // 빨강: 서류와 다름
  mismatchSoft: "#fdf1f1",
  edited: "#e0731f", // 주황: 담당자가 고친 값이 서류와 다름
  editedSoft: "#fff5ec",
  approved: "#9aa5b5", // 회색 글자: 승인 완료
  needInput: "#fdf6cf", // 노랑 배경: 자료 추가 필요
  needInputText: "#80580f",
  needCheck: "#7357d6", // 보라 글자: 확인 필요(판단 근거 부족)
  needCheckSoft: "#f4f1fd",
  expired: "#9aa5b5", // 취소선 + 회색: 만료 실적
  ok: "#24925a",
  okSoft: "#eef9f2",
  overlay: "rgba(30, 42, 68, 0.32)",
  // 화면 틀 테마 (HS 요청 11/28): 연한 회청 바탕 위 큰 둥근 흰 판, 흰 사이드바, 흰 카드 + 아주 연한 그림자
  brand: "#2f8fe8", // 강조 글자(링크·지금 메뉴 글자·강조 숫자)
  heading: "#1e2a44", // 제목: 진한 남색
  pageBg: "#eef3f9",
  panelBg: "#ffffff",
  panelShadow: "0 10px 40px rgba(30, 58, 110, 0.08)",
  sidebarBg: "#ffffff",
  sidebarText: "#7a879b", // 사이드바 다른 메뉴: 흐린 회청색
  sidebarActive: "#e7f2fd", // 사이드바 지금 메뉴: 연한 하늘색 알약
  sidebarActiveText: "#2f8fe8",
  surface: "#ffffff", // 카드 바탕
  mainBg: "#f5f8fc", // 흰 판 안 내용 칸: 아주 연한 회청(흰 카드가 떠 보이게, 참고 화면 2)
  cardBg: "#edf2f8", // 카드 안 연한 상자
  cardBorder: "#edf1f7",
  cardShadow: "0 2px 14px rgba(30, 58, 110, 0.06)",
  rowHover: "#f1f7fe",
  line: "#edf1f7", // 표 가로줄·머리말 아래 구분선
  thText: "#8a96a8", // 표 머리글
  // 홈(전체 현황) 전용: 위쪽 진한 파랑 띠 (HS 요청 11/28, 포털 대시보드 참고)
  homeBand: "linear-gradient(120deg, #1f5fe0 0%, #2f6fe8 45%, #3b82f6 100%)",
  homeAccent: "#1f5fe0", // 홈 강조 숫자·제목 밑줄
  pillWarnSoft: "#fff1e3",
  pillWarnText: "#c9631a",
} as const;

export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 40 } as const;

export const radius = 8;
export const cardRadius = 16;
export const homeCardRadius = 8; // 홈 카드(포털형)는 모서리를 작게
export const panelRadius = 24;
export const sidebarCurve = 0; // 흰 사이드바: 곡선 없음
export const font = { sm: 12, md: 14, lg: 16, xl: 20, xxl: 28 } as const;
