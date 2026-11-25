// 백엔드 a2_registry 응답과 같은 타입. 담당: YHS
import type { Evidence } from "@/lib/types/history";
import type { DriveStatus } from "@/lib/types/reader";

export type RecordStatus = "유효" | "만료 임박" | "만료";

export interface SamplePart {
  material: string;
  part: string;
  color: string;
}

export interface RecordUse {
  bl_no: string;
  model: string;
  kind: "정밀" | "서류";
  row_id: string;
}

export interface PreciseRecord {
  record_no: string;
  factory_code: string;
  factory_name: string;
  factory_address: string;
  materials: string[];
  spec_class: string;
  sample_parts: SamplePart[];
  applied_on: string | null;
  approved_on: string | null;
  expires_on: string | null;
  products: string[];
  product_names: string[];
  ntfc_no: string;
  uses: RecordUse[];
  status: RecordStatus;
  evidence: Evidence[];
  memo: string;
}

export type CandidateState = "ok" | "need_check" | "different";

export interface Candidate {
  cand_id: string;
  kind: "수입신고서" | "시험성적서";
  filename: string;
  doc_id: string;
  receipt_no: string;
  model: string;
  product_ko: string;
  product_en: string;
  materials: string[];
  material_codes: string[];
  maker_code: string;
  maker_name: string;
  maker_address: string;
  inspection_type: string;
  applied_on: string;
  approved_on: string;
  sample_parts: (SamplePart & { remark: string })[];
  status: Record<string, CandidateState>;
  previous: Record<string, string>;
  warnings: string[];
  parser: "json" | "llm" | "none";
}

export interface UploadCandidates {
  upload_id: string;
  shipper_id: string;
  candidates: Candidate[];
  drive: DriveStatus;
}

export interface CommitOut {
  shipper_id: string;
  products: number;
  records: string[];
  skipped: string[];
  rejudged: number;
  drive: DriveStatus;
}

export interface AlertItem {
  kind: "record" | "factory_code"; // 실적 · 해외제조업소 코드(A2-5)
  record_no: string; // kind=factory_code면 업소코드
  factory: string;
  materials: string[];
  expires_on: string;
  days_left: number;
  stage: number;
  models: string[];
  alternative: string;
  sent: boolean;
}

export type FactoryStatus = "유효" | "만료 임박" | "만료" | "확인 필요";

export interface FactoryCode {
  code: string;
  name: string;
  address: string;
  registered_on: string | null;
  expires_on: string | null;
  days_left: number | null;
  status: FactoryStatus;
  source: string;
}

export interface AlertsOut {
  items: AlertItem[];
  summary: Record<string, number>;
  mail: { ok: boolean; reason: string };
  today: string;
}

export interface MailPreview {
  subject: string;
  body: string;
  count: number;
}

export interface SendOut {
  sent: number;
  skipped: number;
  reason: string;
}
