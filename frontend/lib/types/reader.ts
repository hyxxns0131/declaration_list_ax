// 백엔드 a0_reader 응답과 같은 타입. 담당: KHS
export interface PreviewOut {
  files: { filename: string; doc_type: string | null }[];
  required: { doc_type: string; label: string; present: boolean }[];
  missing: string[];
}

export interface DriveStatus {
  ok: boolean;
  reason: string;
}

export interface UploadOut {
  folder_id: string;
  bl_no: string;
  documents: { doc_id: string; doc_type: string; parser: string; warnings: string[]; filename: string }[];
  created: string[];
  updated: string[];
  reupload: boolean;
  missing_docs: string[];
  warnings: string[];
  drive: DriveStatus;
}

// 선적 건 목록 (GET /reader/shipments, 검역 리스트 탭 1단계)
export interface ShipmentDoc {
  doc_id: string;
  doc_type: string;
  filename: string;
  parser: string;
  warnings: string[];
  sources: Record<string, string>;
  values: {
    bl_no: string;
    invoice_no: string;
    doc_date: string;
    vessel: string;
    manufacturer_name: string;
    currency: string;
    total_amount: number | null;
    total_cartons: number | null;
    total_gross_kg: number | null;
    line_count: number;
  };
  lines: {
    model: string;
    description: string;
    qty_per_carton: number | null;
    quantity?: number | null; // 수량(PCS 합계)
    cartons: number | null;
    net_kg: number | null;
    amount: number | null;
    is_part?: boolean;
  }[];
}

export interface Shipment {
  bl_no: string;
  folder_ids: string[];
  documents: Record<string, ShipmentDoc>;
  missing: string[];
  missing_marks: string[];
  status: "자료 추가 필요" | "확인 필요" | "추출 완료";
  uploaded_at: string;
  // 화면 ① 정리(HS 요청 11/27): 서류 상태 글자·다음 할 일
  files: string[];
  row_count: number;
  attention_rows: number;
  locked: boolean;
  doc_states: Record<string, DocState>;
  next: NextStep;
  /** "모델|0·1(부분품)" → 검역 리스트 row_id (품목 표에서 ② 그 행으로) */
  row_ids: Record<string, string>;
}

/** ok 읽음 · missing 없음 · unreadable 값을 못 읽음 · unknown 종류를 모름 · check 일부 확인 필요 */
export type DocState = "ok" | "missing" | "unreadable" | "unknown" | "check";
/** 카드의 버튼 하나: B/L 번호 입력 → 빠진 서류 올리기 → 서류 다시 보기 → 대조 결과 보기 → 끝 */
export type NextStep = "enter_bl" | "upload_missing" | "fix_docs" | "review" | "done";

