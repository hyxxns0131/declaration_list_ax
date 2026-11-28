// 서류 판독 API (A0). 담당: KHS
import { api, apiBlob, qs, saveBlob } from "@/lib/api/client";
import type { PreviewOut, UploadOut } from "@/lib/types/reader";

export const previewFiles = (shipperId: string, filenames: string[]) =>
  api<PreviewOut>("/reader/preview", {
    method: "POST",
    body: JSON.stringify({ shipper_id: shipperId, filenames }),
  });

export function uploadDocs(shipperId: string, files: File[], folderId?: string): Promise<UploadOut> {
  const form = new FormData();
  form.set("shipper_id", shipperId);
  if (folderId) form.set("folder_id", folderId); // 그 선적 건에 서류 더 올리기
  for (const f of files) form.append("files", f, f.name);
  return api<UploadOut>("/reader/upload", { method: "POST", body: form });
}

/** 원본 서류를 새 창에서 연다. */
export async function openDocument(docId: string): Promise<void> {
  saveBlob(await apiBlob(`/reader/documents/${encodeURIComponent(docId)}/file`), null);
}

export interface InboxScanOut {
  ok: boolean;
  enabled: boolean;
  reason: string;
  imported: { folder: string; bl_no: string; rows: number }[];
}

/** 드라이브 접수 폴더에서 가져오기(화주 설정 inbox). 드라이브 미연결이면 ok=false + 이유. 로직 점검 반영 11/25 */
export const scanInbox = (shipperId: string) =>
  api<InboxScanOut>(`/reader/inbox/scan${qs({ shipper_id: shipperId })}`, { method: "POST" });


/** B/L 번호를 못 읽은 선적 건에 번호 직접 입력 (HS 요청 11/27) */
export const setShipmentBl = (shipperId: string, folderIds: string[], blNo: string) =>
  api<{ bl_no: string; created: string[]; updated: string[] }>("/reader/shipments/bl", {
    method: "PUT",
    body: JSON.stringify({ shipper_id: shipperId, folder_ids: folderIds, bl_no: blNo }),
  });

/** 선적 건 삭제(서류·행을 PC에 백업한 뒤 지움, 승인 행이 있으면 거부) */
export const deleteShipment = (shipperId: string, folderIds: string[]) =>
  api<{ deleted_documents: number; deleted_rows: number; kept_human_values: number; backup: string }>(
    "/reader/shipments/delete",
    { method: "POST", body: JSON.stringify({ shipper_id: shipperId, folder_ids: folderIds }) },
  );

/** 선적 건 다시 읽기: 올려 둔 원본을 지금 판독 규칙으로 다시 읽는다 */
export const rereadShipment = (shipperId: string, folderIds: string[]) =>
  api<{ bl_no: string; documents: number; created: string[]; updated: string[] }>("/reader/shipments/reread", {
    method: "POST",
    body: JSON.stringify({ shipper_id: shipperId, folder_ids: folderIds }),
  });
