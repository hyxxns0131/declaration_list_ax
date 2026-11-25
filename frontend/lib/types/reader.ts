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
