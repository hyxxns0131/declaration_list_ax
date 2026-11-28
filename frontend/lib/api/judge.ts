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
  ModelDocs,
} from "@/lib/types/judge";

export const getJudge = (rowId: string) => api<JudgeDetail>(`/judge/${encodeURIComponent(rowId)}`);

export const computeDeclarations = (shipperId: string) =>
  api<Declaration[]>(`/judge/declarations${qs({ shipper_id: shipperId })}`, { method: "POST" });

/** 기업 설정을 바꾼 뒤 재질·제조사·실적 다시 판단(확정 값 유지) */
export const rejudgeShipper = (shipperId: string) =>
  api<{ rejudged: number }>(`/judge/rejudge?shipper_id=${encodeURIComponent(shipperId)}`, { method: "POST" });

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

/** 전체(아무것도 안 주면) / 고른 신고건 / 고른 묶음 → ZIP(신고건마다 xlsx + 검토용 전체 + 제외됨.txt) */
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


/** 검토용 전체 엑셀 1개: 시트 1장에 신고건 사이 빈 행, 막힌 신고건도 이유와 함께. 신고용이 아님(시연 피드백 11/27) */
export async function downloadItemReview(
  shipperId: string,
  filename: string,
  declarationIds: string[] = [],
): Promise<void> {
  const q = qs({ shipper_id: shipperId, declaration_ids: declarationIds.join(",") || null });
  saveBlob(await apiBlob(`/judge/item-sheet/review${q}`), filename);
}

/** 모델 자료 목록(드라이브 읽기만). 드라이브가 연결되지 않았으면 ok=false + 이유 */
export const getModelDocs = (rowId: string) =>
  api<ModelDocs>(`/judge/${encodeURIComponent(rowId)}/model-docs`);

export async function downloadModelDoc(fileId: string, filename: string): Promise<void> {
  saveBlob(await apiBlob(`/judge/model-docs/file/${encodeURIComponent(fileId)}`), filename);
}
