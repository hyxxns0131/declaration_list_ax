// 서류 판독 API (A0). 담당: KHS
import { api, apiBlob, qs, saveBlob } from "@/lib/api/client";
import type { PreviewOut, UploadOut } from "@/lib/types/reader";

export const previewFiles = (shipperId: string, filenames: string[]) =>
  api<PreviewOut>("/reader/preview", {
    method: "POST",
    body: JSON.stringify({ shipper_id: shipperId, filenames }),
  });

export function uploadDocs(shipperId: string, files: File[]): Promise<UploadOut> {
  const form = new FormData();
  form.set("shipper_id", shipperId);
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

