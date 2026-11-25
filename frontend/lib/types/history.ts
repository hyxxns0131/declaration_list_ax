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
}

export interface Columns {
  columns: string[];
  color_column: string;
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
  sheet: CellValue;
  cell: string;
  different: boolean;
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
