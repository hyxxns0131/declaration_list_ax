"use client";
// 실적 표 (DESIGN 6장): 만료 실적은 취소선 + 회색. 행 수정·승인일 조회·서류검사 내역 펼치기. 담당: YHS
import { Fragment, useState } from "react";

import { Badge, type Tone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate } from "@/lib/format";
import { lookupApproval, patchRecord } from "@/lib/api/registry";
import { REGISTRY } from "@/lib/text/registry";
import type { PreciseRecord, RecordStatus } from "@/lib/types/registry";

const TONE: Record<RecordStatus, Tone> = { 유효: "ok", "만료 임박": "edited", 만료: "neutral" };
const C = REGISTRY.cols;

function EditDialog({ rec, onClose, onSaved }: { rec: PreciseRecord; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    factory_code: rec.factory_code,
    factory_name: rec.factory_name,
    factory_address: rec.factory_address,
    materials: rec.materials.join(", "),
    spec_class: rec.spec_class,
    applied_on: rec.applied_on ?? "",
    approved_on: rec.approved_on ?? "",
    products: rec.products.join(", "),
    product_names: rec.product_names.join(", "),
    memo: rec.memo,
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

  const save = async () => {
    setBusy(true);
    try {
      await patchRecord(rec.record_no, {
        ...form,
        materials: list(form.materials).sort((a, b) => a.localeCompare(b, "ko")),
        products: list(form.products),
        product_names: list(form.product_names),
        applied_on: form.applied_on || null,
        approved_on: form.approved_on || null,
      });
      onSaved();
      onClose();
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  const field = (key: keyof typeof form, label: string) => (
    <label key={key} style={{ display: "block", marginBottom: space.sm }}>
      <span style={{ fontSize: font.sm, color: colors.muted }}>{label}</span>
      <input
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        style={{ display: "block", width: "100%", padding: space.xs }}
      />
    </label>
  );

  return (
    <Modal
      title={`${REGISTRY.edit} · ${rec.record_no}`}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>취소</Button>
          <Button variant="primary" disabled={busy} onClick={save}>
            저장
          </Button>
        </>
      }
    >
      {field("factory_code", "해외제조업소 코드")}
      {field("factory_name", "해외제조업소 회사명")}
      {field("factory_address", "해외제조업소 주소")}
      {field("materials", "재질(재질 코드명, 쉼표로 구분 — 가나다 순으로 저장)")}
      {field("spec_class", "재질 구분(유리제·도자기제·법랑·옹기류)")}
      {field("applied_on", "신청일 YYYY-MM-DD")}
      {field("approved_on", "승인일 YYYY-MM-DD (만료일 = 승인일 + 5년)")}
      {field("products", "실적 인정 모델(쉼표)")}
      {field("product_names", "품명(쉼표, 예: 전기밥솥)")}
      {field("memo", REGISTRY.memo)}
      {error !== null && <ErrorLine error={error} />}
    </Modal>
  );
}

export function RecordTable({ records, onChanged }: { records: PreciseRecord[]; onChanged: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [edit, setEdit] = useState<PreciseRecord | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const lookup = async (no: string) => {
    setBusy(no);
    setError(null);
    try {
      await lookupApproval(no);
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      {error !== null && <ErrorLine error={error} />}
      <div style={{ overflowX: "auto" }}>
        <table className="grid">
          <thead>
            <tr>
              <th>{C.no}</th>
              <th>{C.status}</th>
              <th>{C.factory}</th>
              <th>{C.material}</th>
              <th>{C.applied}</th>
              <th>{C.approved}</th>
              <th>{C.expires}</th>
              <th>{C.report}</th>
              <th>{C.uses}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {records.map((r) => {
              const expired = r.status === "만료";
              const cls = expired ? "strike" : undefined;
              return (
                <Fragment key={r.record_no}>
                  <tr style={{ color: expired ? colors.expired : undefined }}>
                    <td className={cls}>{r.record_no}</td>
                    <td>
                      <Badge tone={TONE[r.status]}>{r.status}</Badge>
                    </td>
                    <td className={cls}>
                      {r.factory_name} {r.factory_code && `(${r.factory_code})`}
                    </td>
                    <td className={cls}>{r.materials.join(", ")}</td>
                    <td>{fmtDate(r.applied_on)}</td>
                    <td>
                      {fmtDate(r.approved_on) || (
                        <span style={{ color: colors.needCheck }}>? 확인 필요</span>
                      )}
                    </td>
                    <td className={cls}>{fmtDate(r.expires_on)}</td>
                    <td style={{ fontSize: font.sm }}>
                      {r.sample_parts.length
                        ? r.sample_parts.map((s) => `${s.part || "-"}: ${s.material}${s.color ? ` (${s.color})` : ""}`).join(" / ")
                        : "—"}
                    </td>
                    <td>
                      <Button small variant="ghost" onClick={() => setOpen(open === r.record_no ? null : r.record_no)}>
                        {r.products.length}모델 {open === r.record_no ? "▼" : "▶"}
                      </Button>
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <Button small onClick={() => setEdit(r)}>
                        {REGISTRY.edit}
                      </Button>{" "}
                      {!r.approved_on && (
                        <Button small title={REGISTRY.approvalHint} disabled={busy === r.record_no} onClick={() => lookup(r.record_no)}>
                          {REGISTRY.approvalLookup}
                        </Button>
                      )}
                    </td>
                  </tr>
                  {open === r.record_no && (
                    <tr>
                      <td colSpan={10} style={{ background: colors.bgSubtle, fontSize: font.sm }}>
                        <div>
                          {REGISTRY.products}: {r.products.join(", ") || "—"} · 품명: {r.product_names.join(", ") || "—"}
                        </div>
                        {r.uses.length > 0 && (
                          <ul style={{ margin: 0 }}>
                            {r.uses.map((u) => (
                              <li key={u.row_id || u.bl_no + u.model}>
                                {u.bl_no} {u.model} · {u.kind}
                              </li>
                            ))}
                          </ul>
                        )}
                        {r.evidence.map((e) => (
                          <div key={e.ref} style={{ color: colors.muted }}>
                            근거: {e.note}
                          </div>
                        ))}
                        {r.memo && <div style={{ color: colors.needCheck }}>{r.memo}</div>}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {edit && <EditDialog rec={edit} onClose={() => setEdit(null)} onSaved={onChanged} />}
    </>
  );
}
