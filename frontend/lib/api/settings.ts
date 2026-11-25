// 화주 설정 API (A4). 담당: JUJ
import { api } from "@/lib/api/client";
import type { Shipper } from "@/lib/types/core";
import type { Catalog, DryRunOut, ShipperDetail, ShipperValues } from "@/lib/types/settings";

export const getRules = () => api<{ catalog: Catalog; default: ShipperValues }>("/settings/rules");

export const listShippers = () => api<Shipper[]>("/settings/shippers");

export const getShipper = (id: string) => api<ShipperDetail>(`/settings/shippers/${encodeURIComponent(id)}`);

export const saveShipper = (id: string, settings: ShipperValues) =>
  api<ShipperDetail>(`/settings/shippers/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });

export const createShipper = (shipperId: string, displayName: string, requiredDocs: string[]) =>
  api<ShipperDetail>("/settings/shippers", {
    method: "POST",
    body: JSON.stringify({ shipper_id: shipperId, display_name: displayName, required_docs: requiredDocs }),
  });

export const dryRun = (id: string, settings: ShipperValues, blNo?: string) =>
  api<DryRunOut>(`/settings/shippers/${encodeURIComponent(id)}/dry-run`, {
    method: "POST",
    body: JSON.stringify({ settings, bl_no: blNo ?? null }),
  });

/** 화주 삭제(기본 화주 A·B는 409). 파일은 지우지 않고 백업 폴더로 옮긴다. HS 요청 11/25 */
export const deleteShipper = (id: string) =>
  api<{ ok: boolean; shipper_id: string; backup: string }>(`/settings/shippers/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
