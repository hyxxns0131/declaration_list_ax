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
  lines: { model: string; description: string; qty_per_carton: number | null; cartons: number | null; net_kg: number | null; amount: number | null }[];
}

export interface Shipment {
  bl_no: string;
  folder_ids: string[];
  documents: Record<string, ShipmentDoc>;
  missing: string[];
  missing_marks: string[];
  status: "자료 추가 필요" | "확인 필요" | "추출 완료";
  uploaded_at: string;
}

