// 공통 화면 문구 (DESIGN 8장). 영역 문구는 lib/text/<영역>.ts. 담당: KHS
export const T = {
  appName: "기구·용기·포장 검역 신고 관리",
  // 용어 열린 질문(확인 필요 1): "검역" vs "수입신고 검사". 정해질 때까지 이 상수 하나로 쓴다
  inspectionWord: "검역",
  // 홈 + 탭 5개(1인 1탭). 탭 순서 변경: HS 요청 11/25 21시 (AGENTS 1장 탭 표)
  home: "홈",
  tabs: {
    settings: "1. 기업 설정",
    registry: "2. 서류 등록·만료 알림",
    judge: "3. 재질·실적 판단",
    list: "4. 검역 리스트",
    connections: "5. 연결 설정", // 가이드라인 밖, HS 요청 11/25
  },
  // 탭별 사이드바 메뉴 (DESIGN 2장 사이드바 표). 경로는 lib/nav.ts
  side: {
    home: { overview: "전체 현황" },
    registry: { records: "실적 현황", factories: "해외제조업소 코드", alerts: "만료 알림" },
    list: { table: "검역이력 표", review: "확인 필요", upload: "서류 올리기" },
    judge: { groups: "신고건 묶음", evidence: "판단 근거", itemSheet: "품목사항 엑셀" },
    settings: { shippers: "화주 선택·관리", rules: "규칙 설정" },
    connections: { all: "전체 연결", ai: "AI 모델" },
  },
  // 작업 화주 (탭 1 기업 설정 첫 화면에서 고름, 모든 탭 공용. HS 요청 11/25)
  shipperPick: {
    current: "작업 화주",
    none: "아직 안 고름",
    change: "화주 바꾸기",
    goPick: "기업 설정에서 화주 고르기",
    needFirst: "기업 설정에서 화주를 먼저 고르세요. 고른 화주의 자료만 이 화면에 보입니다.",
  },
  // 사이드바 접기 버튼 (☰). 상태는 브라우저 localStorage "dl_sidebar_open"
  sidebar: { open: "사이드바 열기", close: "사이드바 닫기" },
  login: {
    username: "아이디",
    password: "비밀번호",
    submit: "로그인",
    submitting: "로그인 중…",
    help: "아이디·비밀번호를 모르면 관리자에게 문의하세요.",
  },
  logout: "로그아웃",
  loading: "불러오는 중…",
  saving: "저장 중…",
  retry: "다시 시도",
  cancel: "취소",
  close: "닫기",
  save: "저장",
  noData: "자료 없음",
  shipper: "화주",
  pickShipper: "화주를 고르세요",
  networkError: "서버에 연결할 수 없습니다. 백엔드가 켜져 있는지 확인하세요.",
  unknownError: "알 수 없는 오류가 났습니다. 다시 시도해 주세요.",
  integrations: {
    llmOff: "AI 판독 꺼짐: 엑셀·글자 PDF만 자동 판독",
    unipassMock: "유니패스 가상 자료(mock) 모드",
    driveOff: "드라이브 연동 꺼짐: 서류는 이 PC에만 저장",
  },
} as const;
