// 서류 올리기 대화상자 문구 (DESIGN 3-1-1). 담당: KHS
export const READER = {
  title: (shipper: string) => `서류 올리기 · ${shipper}`,
  guide: "선적서류 1건(B/L 1건)씩 올려 주세요.",
  drop: "여기로 파일을 끌어 놓거나",
  pick: "파일 고르기",
  kinds: "PDF · 엑셀 · 사진",
  recognized: "인식한 서류",
  required: (labels: string) => `(필요 서류: ${labels})`,
  unknownType: "종류 확인 필요",
  submit: "올리고 판독",
  uploading: "올리고 판독하는 중… (대화상자를 닫아도 됩니다)",
  done: (created: number, updated: number) => `판독 완료: 새 행 ${created}개, 고친 행 ${updated}개`,
  reupload: "이미 있는 B/L입니다. 바뀐 칸만 고칩니다.",
  missing: (labels: string) => `빠진 서류: ${labels} → 행에 "자료 추가 필요"로 표시됩니다`,
  readFail: "서류 판독 실패 - 파일 확인 필요",
  noFiles: "파일을 골라 주세요.",
  remove: "빼기",
} as const;

export const DOC_LABELS: Record<string, string> = {
  CI: "인보이스",
  PL: "포장명세서",
  BL: "B/L",
  CO: "원산지증명서",
  INTAKE_LIST: "입고리스트",
  IMPORT_DECL: "수입신고서",
  TEST_REPORT: "시험성적서",
  PHOTO: "현품사진",
  LABEL: "한글표시",
};
