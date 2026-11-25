// 검역이력 API (A1). 담당: KHS
import { api, qs } from "@/lib/api/client";
import type { Badges, CellValue, Columns, HistoryRow, RefreshResult, Review } from "@/lib/types/history";

export const getHistory = (shipperId: string, opts: { status?: string; attention?: boolean } = {}) =>
  api<HistoryRow[]>(`/history${qs({ shipper_id: shipperId, status: opts.status, attention: opts.attention })}`);

export const getBadges = (shipperId: string) => api<Badges>(`/history/badges${qs({ shipper_id: shipperId })}`);

export const getColumns = () => api<Columns>("/history/columns");

export const patchCell = (
  rowId: string,
  body: { column: string; value?: CellValue; memo?: string; clear?: boolean },
) => api<HistoryRow>(`/history/${encodeURIComponent(rowId)}`, { method: "PATCH", body: JSON.stringify(body) });

export const refreshHistory = (shipperId: string) =>
  api<RefreshResult>(`/history/refresh${qs({ shipper_id: shipperId })}`, { method: "POST" });

export const archiveReady = (shipperId: string) =>
  api<{ ready: string[]; moved: string[]; drive: { ok: boolean; reason: string } }>(
    `/history/archive${qs({ shipper_id: shipperId })}`,
    { method: "POST" },
  );

export const getReview = (rowId: string) => api<Review>(`/history/${encodeURIComponent(rowId)}/review`);

export const confirmRow = (rowId: string, on: boolean) =>
  api<HistoryRow>(`/history/${encodeURIComponent(rowId)}/confirm`, {
    method: "POST",
    body: JSON.stringify({ on }),
  });

export const deleteRow = (rowId: string) =>
  api<{ ok: boolean }>(`/history/${encodeURIComponent(rowId)}`, { method: "DELETE" });

export const moveRow = (rowId: string, beforeRowId: string | null) =>
  api<{ ok: boolean }>(`/history/${encodeURIComponent(rowId)}/move`, {
    method: "POST",
    body: JSON.stringify({ before_row_id: beforeRowId }),
  });
