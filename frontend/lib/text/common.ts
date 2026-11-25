// 공통 화면 문구 (DESIGN 8장). 영역 문구는 lib/text/<영역>.ts. 담당: KHS
export const T = {
  appName: "기구·용기·포장 검역 신고 관리",
  // 용어 열린 질문(확인 필요 1): "검역" vs "수입신고 검사". 정해질 때까지 이 상수 하나로 쓴다
  inspectionWord: "검역",
  // 탭 4개 = 제안서 가이드라인 1~4번, 1인 1탭 (AGENTS 1장 탭 표)
  tabs: {
    list: "1. 검역 리스트",
    registry: "2. 서류 등록·만료 알림",
    judge: "3. 재질·실적 판단",
    settings: "4. 기업 설정",
  },
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
