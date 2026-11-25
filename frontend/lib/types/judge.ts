// 백엔드 a3_judge 응답과 같은 타입. 담당: LSY
import type { DeclarationKey, Evidence } from "@/lib/types/history";

export interface FactoryCandidate {
  code: string;
  name?: string;
  address: string;
  status?: string;
  score?: number;
}

export interface RecordCandidate {
  record_no: string;
  value: string;
  materials: string[];
  factory_code: string;
  approved_on: string | null;
  expires_on: string | null;
  expired: boolean;
  fits: boolean;
}

export interface JudgeDetail {
  row_id: string;
  model: string;
  is_part: boolean;
  locked?: boolean;
  material?: { candidates: string[]; evidence: Evidence[] };
  maker?: { candidates: FactoryCandidate[]; notes: string[]; address: string };
  record?: { candidates: RecordCandidate[] };
  past_row_id?: string | null;
}

export interface ItemSheetPreview {
  ok: boolean;
  reasons: string[];
  headers: string[];
  rows: string[][];
  warnings: string[];
  key: DeclarationKey;
  arrival_date: string | null;
  bl_count: number;
  record_nos: string[];
  missing_record_rows: string[];
}

export interface ItemSheetOut {
  file_id: string;
  filename: string;
  warnings: string[];
}
