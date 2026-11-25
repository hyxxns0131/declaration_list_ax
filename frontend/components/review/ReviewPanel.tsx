"use client";
// 서류 검수 패널 (DESIGN 4장). props: rowId → onConfirmed(rowId). 데이터: getReview, confirmRow만. 담당: KHS
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtCell, fmtNumber } from "@/lib/format";
import { confirmRow, getReview } from "@/lib/api/history";
import { openDocument } from "@/lib/api/reader";
import { DOC_LABELS } from "@/lib/text/reader";
import { REVIEW } from "@/lib/text/review";
import type { CellValue, Review, ReviewItem } from "@/lib/types/history";

const DOCS = ["CI", "PL", "BL"] as const;

function Value({ v, red }: { v: CellValue; red: boolean }) {
  if (v === null || v === undefined || v === "") {
    return <span style={{ color: colors.approved }}>{REVIEW.noData}</span>;
  }
  const text = typeof v === "number" ? fmtNumber(v, 3) : String(v);
  return red ? (
    <span style={{ color: colors.mismatch, fontWeight: 600 }} title={REVIEW.different}>
      ■ {text}
    </span>
  ) : (
    <span>{text}</span>
  );
}

function outlier(it: ReviewItem, doc: (typeof DOCS)[number]): boolean {
  if (!it.different) return false;
  const vals = DOCS.map((d) => it[d]).filter((v) => v !== null && v !== "");
  const mine = it[doc];
  if (mine === null || mine === "") return false;
  const same = vals.filter((v) => String(v) === String(mine)).length;
  return same <= vals.length / 2; // 다수와 다른 값만 빨강(둘뿐이면 둘 다)
}

export function ReviewPanel({
  rowId,
  onConfirmed,
  onClose,
}: {
  rowId: string;
  onConfirmed: (rowId: string) => void;
  onClose: () => void;
}) {
  const [data, setData] = useState<Review | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    getReview(rowId).then(setData).catch(setError);
  }, [rowId]);

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

  const toggle = async () => {
    if (!data) return;
    setBusy(true);
    try {
      await confirmRow(rowId, !data.confirmed);
      load();
      onConfirmed(rowId);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const row = data?.row;
  const bl = row ? String(row.cells["B/L Number"]?.ai_value ?? "") : "";
  const nameCell = row?.cells["한글 제품명(모델넘버)"];
  const name = nameCell ? String(nameCell.final_value ?? nameCell.ai_value ?? row?.model ?? "") : row?.model ?? "";

  return (
    <section
      aria-label="서류 검수"
      style={{ borderTop: `2px solid ${colors.border}`, marginTop: space.md, paddingTop: space.md }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
        <strong>{REVIEW.title(bl, name)}</strong>
        {data && <Badge tone={data.mismatch_count ? "mismatch" : "neutral"}>{REVIEW.mismatch(data.mismatch_count)}</Badge>}
        {data && <Badge tone={data.edited_count ? "edited" : "neutral"}>{REVIEW.edited(data.edited_count)}</Badge>}
        <span style={{ marginLeft: "auto", display: "flex", gap: space.sm, flexWrap: "wrap" }}>
          {data?.documents.map((d) => (
            <Button key={d.doc_id} small onClick={() => openDocument(d.doc_id).catch(setError)}>
              {REVIEW.openDoc}: {DOC_LABELS[d.doc_type] ?? d.doc_type}
            </Button>
          ))}
          <Button small variant={data?.confirmed ? "default" : "primary"} disabled={!data || busy} onClick={toggle}>
            {data?.confirmed ? REVIEW.unconfirm : REVIEW.confirm}
          </Button>
          <Button small onClick={onClose} aria-label="닫기">
            ×
          </Button>
        </span>
      </div>

      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {!data && error === null && <Skeleton lines={4} />}
      {data?.confirmed && <Notice>{REVIEW.confirmedNote}</Notice>}

      {data && (
        <table className="grid" style={{ marginTop: space.sm, maxWidth: 820 }}>
          <thead>
            <tr>
              <th>{REVIEW.cols.item}</th>
              {DOCS.map((d) => (
                <th key={d}>{REVIEW.cols[d]}</th>
              ))}
              <th>{REVIEW.cols.sheet}</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => {
              const edited = data.edited.find((e) => e.column === it.cell);
              return (
                <tr key={it.item}>
                  <td>
                    {it.item}
                    {it.different && (
                      <span style={{ color: colors.mismatch, fontSize: font.sm }}> ({REVIEW.different})</span>
                    )}
                  </td>
                  {DOCS.map((d) => (
                    <td key={d}>
                      <Value v={it[d]} red={outlier(it, d)} />
                    </td>
                  ))}
                  <td>
                    {edited ? (
                      <span style={{ color: colors.edited, fontWeight: 600 }} title={edited.memo || REVIEW.editedCell}>
                        ✎ {fmtCell(it.cell, edited.sheet)}
                        {edited.memo && <span style={{ fontWeight: 400 }}> · {edited.memo}</span>}
                      </span>
                    ) : (
                      <Value v={it.sheet} red={false} />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {data && data.warnings.length > 0 && (
        <div style={{ marginTop: space.sm, fontSize: font.sm }}>
          <strong>{REVIEW.warnings}</strong>
          <ul style={{ margin: `${space.xs}px 0`, paddingLeft: space.lg }}>
            {data.warnings.map((w) => (
              <li key={w.column}>
                {w.column}: {w.memo || (w.value === null ? "" : String(w.value))}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data && data.edited.length > 0 && (
        <div style={{ fontSize: font.sm }}>
          <strong>{REVIEW.editedList}</strong>
          <ul style={{ margin: `${space.xs}px 0`, paddingLeft: space.lg }}>
            {data.edited.map((e) => (
              <li key={e.column} style={{ color: colors.edited }}>
                ✎ {e.column}: {fmtCell(e.column, e.sheet)} ({REVIEW.program}: {fmtCell(e.column, e.program) || REVIEW.noData})
                {e.memo ? ` · ${e.memo}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
