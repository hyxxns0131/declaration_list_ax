// 판단·신고건·품목사항 API (A3). 담당: LSY
import { api, apiBlob, qs, saveBlob } from "@/lib/api/client";
import type { Declaration } from "@/lib/types/history";
import type { ItemSheetOut, ItemSheetPreview, JudgeDetail } from "@/lib/types/judge";

export const getJudge = (rowId: string) => api<JudgeDetail>(`/judge/${encodeURIComponent(rowId)}`);

export const computeDeclarations = (shipperId: string) =>
  api<Declaration[]>(`/judge/declarations${qs({ shipper_id: shipperId })}`, { method: "POST" });

export const getDeclarations = (shipperId: string) =>
  api<Declaration[]>(`/judge/declarations${qs({ shipper_id: shipperId })}`);

export const previewItemSheet = (rowIds: string[]) =>
  api<ItemSheetPreview>("/judge/item-sheet/preview", {
    method: "POST",
    body: JSON.stringify({ row_ids: rowIds }),
  });

export const createItemSheet = (rowIds: string[]) =>
  api<ItemSheetOut>("/judge/item-sheet", { method: "POST", body: JSON.stringify({ row_ids: rowIds }) });

export async function downloadItemSheet(fileId: string, filename: string): Promise<void> {
  saveBlob(await apiBlob(`/judge/item-sheet/${encodeURIComponent(fileId)}`), filename);
}
