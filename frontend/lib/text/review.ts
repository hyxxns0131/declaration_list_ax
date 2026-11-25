// 서류 검수 패널 문구 (DESIGN 4장). 담당: KHS
export const REVIEW = {
  title: (bl: string, name: string) => `서류 검수 · ${bl} ${name}`,
  mismatch: (n: number) => `불일치 ${n}`,
  edited: (n: number) => `사람 수정 ${n}`,
  openDoc: "원본 서류 보기",
  confirm: "확인함",
  unconfirm: "확인 취소",
  confirmedNote: "확인함: 경고를 해제했습니다(자료 추가 필요는 남습니다)",
  cols: { item: "항목", CI: "인보이스", PL: "포장명세서", BL: "B/L", sheet: "시트" },
  noData: "자료 없음",
  different: "서류끼리 다름",
  editedCell: "담당자가 고친 값",
  warnings: "확인할 칸",
  editedList: "사람이 고친 칸",
  program: "프로그램 값",
  empty: "표에서 행을 고르면 서류 검수 패널이 열립니다.",
} as const;
