// 실적·서류 등록·만료 알림 API (A2). 담당: YHS
import { api, qs } from "@/lib/api/client";
import type {
  AlertsOut,
  Candidate,
  CommitOut,
  FactoryCode,
  MailPreview,
  PreciseRecord,
  SendOut,
  UploadCandidates,
} from "@/lib/types/registry";

export const getRecords = (filters: { shipperId?: string; maker?: string; model?: string; status?: string }) =>
  api<PreciseRecord[]>(
    `/registry/records${qs({ shipper_id: filters.shipperId, maker: filters.maker, model: filters.model, status: filters.status })}`,
  );

export const patchRecord = (recordNo: string, changes: Partial<PreciseRecord>) =>
  api<PreciseRecord>(`/registry/records/${encodeURIComponent(recordNo)}`, {
    method: "PATCH",
    body: JSON.stringify({ changes }),
  });

export const lookupApproval = (recordNo: string) =>
  api<PreciseRecord>(`/registry/records/${encodeURIComponent(recordNo)}/approval`, { method: "POST" });

export function uploadRegistry(shipperId: string, files: File[]): Promise<UploadCandidates> {
  const form = new FormData();
  form.set("shipper_id", shipperId);
  for (const f of files) form.append("files", f, f.name);
  return api<UploadCandidates>("/registry/upload", { method: "POST", body: form });
}

export const commitRegistry = (uploadId: string, edits: (Partial<Candidate> & { cand_id: string; skip?: boolean })[]) =>
  api<CommitOut>(`/registry/upload/${encodeURIComponent(uploadId)}/commit`, {
    method: "POST",
    body: JSON.stringify({ edits }),
  });

export const getAlerts = (shipperId: string, withinDays?: number) =>
  api<AlertsOut>(`/registry/alerts${qs({ shipper_id: shipperId, within_days: withinDays })}`);

export const previewAlertMail = (shipperId: string) =>
  api<MailPreview>(`/registry/alerts/preview${qs({ shipper_id: shipperId })}`);

// 해외제조업소 코드 갱신 (A2-5)
export const getFactories = (withinDays?: number) =>
  api<FactoryCode[]>(`/registry/factories${qs({ within_days: withinDays })}`);

export const patchFactory = (code: string, registeredOn: string | null) =>
  api<FactoryCode>(`/registry/factories/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify({ registered_on: registeredOn }),
  });

export const sendAlerts = (shipperId: string) =>
  api<SendOut>(`/registry/alerts/send${qs({ shipper_id: shipperId })}`, { method: "POST" });
