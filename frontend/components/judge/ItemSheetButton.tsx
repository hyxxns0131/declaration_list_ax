"use client";
// 품목사항 만들기 (DESIGN 5장). props: shipperId, selectedRowIds, showReasons? → onCreated(fileId). AI 없음. 담당: LSY
// showReasons: 한 신고건이 아니라 막혔을 때 이유를 버튼 아래에 바로 보여 준다(시연 피드백 11/27)
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate } from "@/lib/format";
import { createItemSheet, downloadItemSheet, previewItemSheet } from "@/lib/api/judge";
import { HOME } from "@/lib/text/home";
import { JUDGE } from "@/lib/text/judge";
import type { ItemSheetPreview } from "@/lib/types/judge";

const T = JUDGE.itemSheet;
const SHOW_COLS = [2, 0, 1, 3, 4, 5, 6]; // 대표·제품명·한글명·수량·순중량·과세가격·화물관리번호1

export function ItemSheetButton({
  shipperId,
  selectedRowIds,
  onCreated,
  showReasons = false,
}: {
  shipperId: string;
  selectedRowIds: string[];
  onCreated: (fileId: string) => void;
  showReasons?: boolean;
}) {
  const [check, setCheck] = useState<ItemSheetPreview | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState("");

  const key = selectedRowIds.join(",");
  useEffect(() => {
    setCheck(null);
    if (!selectedRowIds.length) return;
    let alive = true;
    previewItemSheet(selectedRowIds)
      .then((p) => alive && setCheck(p))
      .catch(() => alive && setCheck(null));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, shipperId]);

  const disabled = !selectedRowIds.length || (check !== null && !check.ok);
  const title = !selectedRowIds.length ? T.noneSelected : check && !check.ok ? `${T.notOne}\n${check.reasons.join("\n")}` : "";

  const make = async () => {
    setBusy(true);
    setError(null);
    try {
      const out = await createItemSheet(selectedRowIds);
      await downloadItemSheet(out.file_id, out.filename);
      setDone(T.done(out.filename));
      onCreated(out.file_id);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <span title={title} style={{ display: "inline-flex", flexDirection: "column", alignItems: "flex-end", gap: space.xs }}>
        <Button
          variant="primary"
          disabled={disabled}
          onClick={() => {
            setOpen(true);
            setDone("");
            setError(null);
          }}
        >
          {HOME.buttons.itemSheet}
          {selectedRowIds.length ? ` (${selectedRowIds.length})` : ""}
        </Button>
        {showReasons && check && !check.ok && (
          <span role="status" style={{ color: colors.mismatch, fontSize: font.sm, textAlign: "right", maxWidth: 460 }}>
            {T.blocked} {check.reasons.join(" / ")}
          </span>
        )}
      </span>
      {open && (
        <Modal
          title={T.title}
          width={860}
          onClose={() => setOpen(false)}
          footer={
            <>
              <Button onClick={() => setOpen(false)}>{done ? "닫기" : "취소"}</Button>
              <Button variant="primary" disabled={busy || !check?.ok} onClick={make}>
                {busy ? T.making : error ? T.retry : T.make}
              </Button>
            </>
          }
        >
          {!check && <Skeleton lines={3} />}
          {check && !check.ok && (
            <div role="alert" style={{ color: colors.mismatch }}>
              ■ {T.notOne}
              <ul>
                {check.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          {check?.ok && (
            <>
              <div style={{ fontSize: font.md, marginBottom: space.sm }}>
                <div>{T.declaration(check.key.vessel_key, check.key.factory_code, check.key.material)}</div>
                <div style={{ color: colors.muted }}>
                  {check.arrival_date ? T.arrival(fmtDate(check.arrival_date), check.bl_count) : ""}
                  {check.record_nos.length ? ` · ${T.records(check.record_nos.join(", "))}` : ""}
                </div>
              </div>
              {!check.arrival_date && <Notice tone="warn">{T.noArrival}</Notice>}
              {check.missing_record_rows.length > 0 && (
                <Notice tone="warn">
                  {T.noRecord} {check.missing_record_rows.join(", ")}
                </Notice>
              )}
              <div style={{ overflowX: "auto" }}>
                <table className="grid">
                  <thead>
                    <tr>
                      {SHOW_COLS.map((i) => (
                        <th key={i}>{check.headers[i]}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {check.rows.map((r, idx) => (
                      <tr key={idx}>
                        {SHOW_COLS.map((i) => (
                          <td key={i}>{r[i]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p style={{ fontSize: font.sm, color: colors.muted }}>{T.note}</p>
              {check.warnings.length > 0 && (
                <details>
                  <summary style={{ fontSize: font.sm }}>
                    {T.warnings} ({check.warnings.length})
                  </summary>
                  <ul style={{ fontSize: font.sm }}>
                    {check.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}
          {error !== null && <ErrorLine error={error} onRetry={make} />}
          {done && <Notice>{done}</Notice>}
        </Modal>
      )}
    </>
  );
}
