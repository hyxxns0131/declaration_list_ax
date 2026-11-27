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

/** 신규 화주 미리 검사 결과(형식·중복). 서버는 통관고유부호를 되돌려주지 않는다. A4-1 개편 11/26 */
export interface NewShipperField {
  ok: boolean;
  reason: string | null; // required · format · duplicate · deleted_code · prod_test_blocked · prod_not_ready
  message: string;
}

export interface NewShipperCheck {
  mode: "dev" | "prod";
  code: NewShipperField;
  alias: NewShipperField;
}

/** 신규 화주 등록: 통관고유부호 + 화주 별칭만 보낸다. 내부 id는 서버가 만든다(응답 settings.shipper_id). */
export const createShipper = (customsCode: string, alias: string) =>
  api<ShipperDetail>("/settings/shippers", {
    method: "POST",
    body: JSON.stringify({ customs_code: customsCode, alias }),
  });

/** 추가 전 미리 검사. 부호가 URL·접근 로그에 남지 않게 본문(POST)으로 보낸다. */
export const checkNewShipper = (customsCode: string, alias: string, signal?: AbortSignal) =>
  api<NewShipperCheck>("/settings/shippers/check", {
    method: "POST",
    body: JSON.stringify({ customs_code: customsCode, alias }),
    signal,
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
