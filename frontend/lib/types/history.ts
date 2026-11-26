// 백엔드 core/schema(fields·history·declaration)와 같은 타입. 담당: KHS
export type CellValue = string | number | null;

export type EvidenceSource =
  | "CI"
  | "PL"
  | "BL"
  | "CO"
  | "INTAKE_LIST"
  | "IMPORT_DECL"
  | "TEST_REPORT"
  | "HISTORY"
  | "PHOTO"
  | "LABEL"
  | "UNIPASS"
  | "FX"
  | "RULE"
  | "MANUAL";

export type Flag = "ok" | "mismatch" | "edited" | "need_input" | "need_check";

export interface Evidence {
  source: EvidenceSource;
  ref: string;
  note: string;
}

export interface Field {
  ai_value: CellValue;
  final_value: CellValue;
  evidence: Evidence[];
  flag: Flag;
  memo: string;
}

export type RowStatus = "자료 추가 필요" | "확인 필요" | "반입 전" | "신청 전" | "승인";

export interface HistoryRow {
  row_id: string;
  shipper_id: string;
  declaration_id: string | null;
  is_part: boolean;
  parent_row_id: string | null;
  model: string;
  part_lines: string[];
  status: RowStatus;
  source_doc_ids: string[];
  cells: Record<string, Field>;
  confirmed: boolean;
  pending: boolean;
}

export interface Badges {
  need_check: number;
  in_progress: number;
  ready: number;
  mismatch: number;
  edited: number;
  approved: number;
  total: number;
  // 검역 리스트 탭 헤더 배지 (0단계)
  need_input: number;
  review_waiting: number;
  manual: number;
}

/** 단계 표시줄(GET /history/steps). key 순서 = 업무 순서 */
export interface ListStep {
  key: "upload" | "review" | "list";
  done: boolean;
  remaining: number;
  label: string;
}

export interface ListSteps {
  shipments: number;
  rows: number;
  steps: ListStep[];
}

export interface Columns {
  columns: string[];
  color_column: string;
  show_color: boolean | null; // 화주 설정 group_by_color. null = 화주 모름
  hidden: string[];
  default_view: string[];
}

export interface DeclarationKey {
  vessel_key: string;
  factory_code: string;
  material: string;
  color: string | null;
}

export interface Declaration {
  declaration_id: string;
  shipper_id: string;
  key: DeclarationKey;
  row_ids: string[];
  record_nos: string[];
  arrival_date: string | null;
  warnings: string[];
}

export interface ReviewItem {
  item: string;
  CI: CellValue;
  PL: CellValue;
  BL: CellValue;
  UNIPASS?: CellValue; // 모선 항목에만: 유니패스 모선명
  sheet: CellValue;
  cell: string;
  different: boolean;
  // 검역 리스트 탭 2·3단계 (없으면 예전 대조 결과)
  code_different?: boolean;
  ai?: AiCheck | null;
  status?: "일치" | "불일치" | "해결됨" | "비어 있음";
  chosen?: { source: PickKey | "manual"; value: CellValue; memo: string; note: string };
}

export interface Review {
  row: HistoryRow;
  items: ReviewItem[];
  mismatch_count: number;
  edited_count: number;
  edited: { column: string; sheet: CellValue; program: CellValue; memo: string }[];
  warnings: { column: string; flag: Flag; memo: string; value: CellValue }[];
  documents: { doc_id: string; doc_type: string; filename: string; warnings: string[] }[];
  confirmed: boolean;
}

export interface RefreshResult {
  rows: number;
  judged: number;
  bls: number;
}

// 대조 결과 (GET /history/mismatches, 검역 리스트 탭 2·3단계)
export type DocKey = "CI" | "PL" | "BL";
/** 담당자가 고를 수 있는 값의 출처: 서류 3종 + 유니패스(모선 항목, HS 결정 11/26) */
export type PickKey = DocKey | "UNIPASS";

export interface AiCheck {
  same: boolean;
  what: string;
  typo_doc: DocKey | "";
  suggested: string;
  reason: string;
  confidence: number;
}

export interface MismatchItem {
  row_id: string;
  bl_no: string;
  model: string;
  is_part: boolean;
  item: string;
  cell: string;
  CI: CellValue;
  PL: CellValue;
  BL: CellValue;
  sheet: CellValue;
  code_different: boolean;
  ai: AiCheck | null;
  different: boolean;
  status: "일치" | "불일치" | "해결됨";
  chosen?: { source: PickKey | "manual"; value: CellValue; memo: string; note: string };
}

export interface ResolveChoice {
  item: string;
  source: PickKey | "manual";
  value?: CellValue;
  memo?: string;
}

