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
  // 근거 패널용(11/26 백엔드 [개선]): 검사별 통과 여부·빠진 재질·상태·제외 이유
  checks?: Record<string, boolean>;
  missing_materials?: string[];
  status?: "선택" | "후보" | "제외";
  reason?: string;
}

export interface JudgeDetail {
  row_id: string;
  model: string;
  is_part: boolean;
  locked?: boolean;
  material?: { candidates: string[]; evidence: Evidence[]; order?: string[] };
  maker?: { candidates: FactoryCandidate[]; notes: string[]; address: string };
  record?: { candidates: RecordCandidate[]; basis_date?: string };
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

// 품목사항 한꺼번에 내려받기 (HS 요청 11/26)
export type ItemGroupBasis = "material" | "factory" | "product" | "record";

export interface ItemGroup {
  key: string;
  label: string;
  count: number;
  declaration_ids: string[];
  numbers: number[];
}

export interface ItemBulkOut {
  file_id: string;
  filename: string;
  included: { declaration_id: string; number: number; filename: string; rows: number; warnings: string[] }[];
  excluded: { declaration_id: string; number: number; reasons: string[] }[];
}
