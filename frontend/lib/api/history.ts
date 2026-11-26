// 검역이력 API (A1). 담당: KHS
import { api, qs } from "@/lib/api/client";
import type { Shipment } from "@/lib/types/reader";
import type {
  Badges,
  CellValue,
  Columns,
  HistoryRow,
  ListSteps,
  MismatchItem,
  RefreshResult,
  ResolveChoice,
  Review,
} from "@/lib/types/history";

export const getHistory = (shipperId: string, opts: { status?: string; attention?: boolean } = {}) =>
  api<HistoryRow[]>(`/history${qs({ shipper_id: shipperId, status: opts.status, attention: opts.attention })}`);

export const getBadges = (shipperId: string) => api<Badges>(`/history/badges${qs({ shipper_id: shipperId })}`);

export const getColumns = (shipperId?: string) => api<Columns>(`/history/columns${qs({ shipper_id: shipperId })}`);

/** 단계 표시줄 완료 판단 (검역 리스트 탭 0단계) */
export const getSteps = (shipperId: string) => api<ListSteps>(`/history/steps${qs({ shipper_id: shipperId })}`);

// ── 검역 리스트 탭 1~4단계 ──
/** 1단계: 선적 건 목록과 서류별 추출값 */
export const getShipments = (shipperId: string) => api<Shipment[]>(`/reader/shipments${qs({ shipper_id: shipperId })}`);
/** 2단계: 다시 대조(코드 + OpenAI) */
export const runCrosscheck = (shipperId: string) =>
  api<{ rows: number; bls: number; unresolved: number }>(`/history/crosscheck${qs({ shipper_id: shipperId })}`, { method: "POST" });
/** 2단계: 대조 결과. status 없으면 불일치·해결됨만 */
export const getMismatches = (shipperId: string, status?: string) =>
  api<MismatchItem[]>(`/history/mismatches${qs({ shipper_id: shipperId, status })}`);
/** 3단계: 검수 패널에서 고른 값 저장 → final_value(근거 MANUAL) */
export const resolveRow = (rowId: string, choices: ResolveChoice[]) =>
  api<HistoryRow>(`/history/${encodeURIComponent(rowId)}/resolve`, { method: "PATCH", body: JSON.stringify({ choices }) });
/** 4단계: 서류 등록 탭 정보로 제조사·재질·실적 채우기 */
export const fillFromRegistry = (shipperId: string) =>
  api<{ judged: number; need_registry: number }>(`/history/fill${qs({ shipper_id: shipperId })}`, { method: "POST" });
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
