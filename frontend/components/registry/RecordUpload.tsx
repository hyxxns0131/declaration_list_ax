"use client";
// 수입신고서·성적서 올리기 → 등록 후보 → 등록 (DESIGN 6장, 시나리오 b). 담당: YHS
import { useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine, Notice } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate } from "@/lib/format";
import { commitRegistry, uploadRegistry } from "@/lib/api/registry";
import { T } from "@/lib/text/common";
import { REGISTRY } from "@/lib/text/registry";
import type { Candidate, CandidateState, UploadCandidates } from "@/lib/types/registry";

const R = REGISTRY.candidates;

function mark(state: CandidateState | undefined, prev?: string) {
  if (state === "different")
    return { style: { color: colors.edited, background: colors.editedSoft }, text: "✎", title: prev ? R.previous(prev) : R.different };
  if (state === "need_check")
    return { style: { color: colors.needCheck, background: colors.needCheckSoft }, text: "?", title: R.needCheck };
  return { style: {}, text: "✓", title: "" };
}

type Edit = Partial<Candidate> & { cand_id: string; skip?: boolean };

export function RecordUpload({
  shipperId,
  shipperName,
  onClose,
  onDone,
}: {
  shipperId: string;
  shipperName: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<UploadCandidates | null>(null);
  const [edits, setEdits] = useState<Record<string, Edit>>({});
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const pick = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    setError(null);
    try {
      setData(await uploadRegistry(shipperId, Array.from(files)));
      setEdits({});
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const val = (c: Candidate, k: keyof Candidate): string => {
    const e = edits[c.cand_id];
    const v = e && k in e ? e[k] : c[k];
    return Array.isArray(v) ? v.join(", ") : String(v ?? "");
  };

  const set = (c: Candidate, k: keyof Candidate, v: string) => {
    const value = k === "materials" ? v.split(",").map((x) => x.trim()).filter(Boolean) : v;
    setEdits({ ...edits, [c.cand_id]: { ...edits[c.cand_id], cand_id: c.cand_id, [k]: value } });
  };

  const register = async () => {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      const out = await commitRegistry(data.upload_id, Object.values(edits));
      setDone(R.done(out.products, out.records.length, out.rejudged));
      onDone();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const inputCell = (c: Candidate, k: keyof Candidate, width = 140) => {
    const m = mark(c.status[k as string], c.previous[k as string]);
    return (
      <span style={{ display: "flex", gap: 2, alignItems: "center", ...m.style }} title={m.title}>
        <span aria-hidden>{m.text}</span>
        <input value={val(c, k)} onChange={(e) => set(c, k, e.target.value)} style={{ width, padding: 2, fontSize: font.sm }} />
      </span>
    );
  };

  return (
    <Modal
      title={R.title(data ? `${shipperName} · ${data.candidates.length}건` : shipperName)}
      width={1080}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>{done ? T.close : T.cancel}</Button>
          <Button variant="primary" disabled={!data || busy || Boolean(done)} onClick={register}>
            {busy && data ? R.registering : R.register}
          </Button>
        </>
      }
    >
      {!data && (
        <div style={{ textAlign: "center", padding: space.lg, border: `2px dashed ${colors.border}`, borderRadius: 8 }}>
          <p>{R.drop}</p>
          <Button onClick={() => input.current?.click()} disabled={busy}>
            {busy ? R.reading : "파일 고르기"}
          </Button>
          <input ref={input} type="file" multiple hidden accept=".pdf,.json" onChange={(e) => pick(e.target.files)} />
        </div>
      )}
      {data && (
        <>
          <p style={{ fontSize: font.sm, color: colors.muted, marginTop: 0 }}>{R.hint}</p>
          <div style={{ overflowX: "auto" }}>
            <table className="grid">
              <thead>
                <tr>
                  <th>{R.cols.kind}</th>
                  <th>{R.cols.product}</th>
                  <th>{R.cols.material}</th>
                  <th>{R.cols.maker}</th>
                  <th>{R.cols.inspection}</th>
                  <th>{R.cols.record}</th>
                  <th>{R.cols.approved}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.candidates.map((c) => {
                  const skip = edits[c.cand_id]?.skip;
                  return (
                    <tr key={c.cand_id} style={{ opacity: skip ? 0.4 : 1 }}>
                      <td style={{ fontSize: font.sm }}>
                        {c.kind}
                        <div style={{ color: colors.muted }}>{c.filename}</div>
                        {c.warnings.map((w) => (
                          <div key={w} style={{ color: colors.needCheck }}>
                            ? {w}
                          </div>
                        ))}
                      </td>
                      <td>
                        {c.kind === "수입신고서" ? inputCell(c, "product_ko", 160) : inputCell(c, "model", 100)}
                        {c.model && <div style={{ fontSize: font.sm, color: colors.muted }}>{c.model}</div>}
                      </td>
                      <td>{inputCell(c, "materials", 200)}</td>
                      <td>
                        {inputCell(c, "maker_code", 110)}
                        <div style={{ fontSize: font.sm, color: colors.muted }}>{c.maker_name}</div>
                      </td>
                      <td>{inputCell(c, "inspection_type", 60)}</td>
                      <td>{inputCell(c, "receipt_no", 120)}</td>
                      <td>{c.approved_on ? fmtDate(c.approved_on) : <span style={{ color: colors.needCheck }}>?</span>}</td>
                      <td>
                        <Button
                          small
                          variant="ghost"
                          onClick={() => setEdits({ ...edits, [c.cand_id]: { ...edits[c.cand_id], cand_id: c.cand_id, skip: !skip } })}
                        >
                          {skip ? "되살리기" : R.skip}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!data.drive.ok && <Notice>{T.integrations.driveOff}</Notice>}
        </>
      )}
      {error !== null && <ErrorLine error={error} />}
      {done && <Notice>{done}</Notice>}
    </Modal>
  );
}
