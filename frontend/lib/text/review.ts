// 서류 검수 패널 문구 (DESIGN 4장). 담당: KHS
export const REVIEW = {
  title: (bl: string, name: string) => `서류 검수 · ${bl} ${name}`,
  mismatch: (n: number) => `불일치 ${n}`,
  edited: (n: number) => `사람 수정 ${n}`,
  openDoc: "원본 서류 보기",
  openDocMenu: "원본 보기",
  shipmentItem: "선적 건 전체 항목 — 한 번 고르면 이 B/L의 모든 품목에 적용됩니다",
  sameItems: (n: number) => `일치하는 항목 ${n}개`,
  stateText: { 일치: "일치", 다름: "다름", "값 없음": "값 없음", 해결됨: "해결됨", 참고: "참고" },
  listDiffLine: "서류끼리는 같고 완성된 리스트 값만 다릅니다 — 쓸 값을 고르세요",
  confirm: "확인함",
  unconfirm: "확인 취소",
  confirmedNote: "확인함: 경고를 해제했습니다(자료 추가 필요는 남습니다)",
  cols: { item: "항목", state: "상태", CI: "인보이스", PL: "패킹리스트", BL: "B/L", UNIPASS: "유니패스", sheet: "완성된 리스트 값" },
  noData: "자료 없음",
  different: "서류끼리 다름",
  editedCell: "담당자가 고친 값",
  warnings: "확인할 칸",
  editedList: "사람이 고친 칸",
  program: "프로그램 값",
  empty: "표에서 행을 고르면 서류 검수 패널이 열립니다.",
  // 검역 리스트 탭 3단계: 값 고르기
  useThis: "이 값 사용",
  manual: "직접 입력",
  memo: "이유 메모(선택)",
  save: "저장",
  saving: "저장 중…",
  saved: (n: number) => `${n}개 항목을 저장했습니다. 완성된 검역 리스트에 '사람이 고름'으로 들어갑니다.`,
  suggest: "추천",
  aiOff: "AI 분석 꺼짐 (코드 대조만)",
  aiLine: (what: string, doc: string, val: string, conf: number) =>
    `${what}${doc ? ` · 오타로 보이는 서류: ${doc}` : ""}${val ? ` · 추천 값 ${val}` : ""} (확신 ${Math.round(conf * 100)}%)`,
  status: { 일치: "일치", 불일치: "불일치", 해결됨: "해결됨", "비어 있음": "비어 있음", 참고: "참고" },
  refLine: "참고 · 유니패스 값을 씁니다(서류 모선과 다름 — 환적 등)",
  chosenLine: (v: string, note: string, memo: string) =>
    `고른 값: ${v || "—"} · ${note.replace("MANUAL: ", "담당자: ")}${memo ? ` · 메모: ${memo}` : ""}`,
  repick: "다시 고르기",
  refTip: "모선명은 유니패스 기준으로 입력합니다. 서류와 달라도 막지 않고 알려만 드립니다(HS 결정 11/27)",
  emptyValue: "비어 있음",
  emptyTip: "서류에 대조할 값(TOTAL 또는 줄 금액)이 없습니다. 막지 않고 알려 드리기만 합니다",
  listValue: "완성된 리스트 값",
  blocked: "검수 필요",
  pickFirst: "고칠 항목에서 값을 고르거나 직접 입력하세요",
} as const;

/** 항목 이름을 초보자가 알아듣는 말로(백엔드 review.friendly_item과 같은 규칙, HS 요청 11/27) */
export function friendlyItem(name: string, ciTotal?: unknown, lineSum?: unknown): string {
  if (name.startsWith("CI 금액 TOTAL")) {
    if (typeof ciTotal === "number" && typeof lineSum === "number")
      return `인보이스 합계 ${ciTotal.toLocaleString("ko-KR")} / 품목 금액 합 ${lineSum.toLocaleString("ko-KR")}`;
    return "인보이스 합계 ↔ 품목 금액 합";
  }
  return name;
}
