// 판단·신고건·품목사항 API (A3). 담당: LSY
import { api, apiBlob, qs, saveBlob } from "@/lib/api/client";
import type { Declaration } from "@/lib/types/history";
import type {
  ItemBulkOut,
  ItemGroup,
  ItemGroupBasis,
  ItemSheetOut,
  ItemSheetPreview,
  JudgeDetail,
} from "@/lib/types/judge";

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

/** 같은 품목끼리 묶음(재질·제조업소·품목·실적번호). 고르기만 하고 신고건을 합치지 않는다. HS 요청 11/26 */
export const getItemGroups = (shipperId: string, groupBy: ItemGroupBasis) =>
  api<ItemGroup[]>(`/judge/item-sheet-groups${qs({ shipper_id: shipperId, group_by: groupBy })}`);

/** 전체(아무것도 안 주면) / 고른 신고건 / 고른 묶음 → ZIP(신고건마다 xlsx + 검토용 합본 + 제외됨.txt) */
export const createItemBulk = (
  shipperId: string,
  opts: { declarationIds?: string[]; groupBy?: ItemGroupBasis; groups?: string[] } = {},
) =>
  api<ItemBulkOut>("/judge/item-sheet/bulk", {
    method: "POST",
    body: JSON.stringify({
      shipper_id: shipperId,
      declaration_ids: opts.declarationIds ?? null,
      group_by: opts.groupBy ?? null,
      groups: opts.groups ?? null,
    }),
  });

export async function downloadItemBulk(fileId: string, filename: string): Promise<void> {
  saveBlob(await apiBlob(`/judge/item-sheet/bulk/${encodeURIComponent(fileId)}`), filename);
}

