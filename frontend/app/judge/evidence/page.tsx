"use client";
// 탭 4. 재질·실적 판단 › 판단 근거 (DESIGN 5-2). 행별 재질·실적·제조사 + 근거 팝오버. 배치만 한다. 담당: LSY
import { useCallback, useEffect, useMemo, useState } from "react";

import { JUDGE_COLUMNS, JudgeEvidence } from "@/components/judge/JudgeEvidence";
import { Badge } from "@/components/ui/Badge";
import { Card, PageHeader } from "@/components/ui/Card";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { EmptyState, ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getHistory } from "@/lib/api/history";
import { shown } from "@/lib/format";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { JUDGE } from "@/lib/text/judge";
import type { HistoryRow } from "@/lib/types/history";

const E = JUDGE.evidencePage;
const P = JUDGE.page;
const MODEL_COLUMN = "한글 제품명(모델넘버)";
const KINDS = [JUDGE_COLUMNS.material, JUDGE_COLUMNS.record, JUDGE_COLUMNS.maker] as const;

const th = { textAlign: "left", padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.sm, color: colors.muted } as const;
const td = { padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.md, verticalAlign: "top" } as const;

export default function EvidencePage() {
  const { shippers, shipperId, setShipperId, error: shipperError } = useShipper();
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [onlyCheck, setOnlyCheck] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [evidence, setEvidence] = useState<{ row: HistoryRow; column: string } | null>(null);

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    getHistory(shipperId).then(setRows).catch(setError);
  }, [shipperId]);

  useEffect(() => {
    setRows(null);
    load();
  }, [load]);

  const needsCheck = (r: HistoryRow) => KINDS.some((k) => ["need_check", "need_input"].includes(r.cells[k]?.flag ?? "ok") || !shown(r.cells[k]));
  const visible = useMemo(() => (rows ?? []).filter((r) => !onlyCheck || needsCheck(r)), [rows, onlyCheck]);

  const cell = (row: HistoryRow, column: string) => {
    const value = String(shown(row.cells[column]) ?? "");
    const flag = row.cells[column]?.flag;
    return (
      <span style={{ display: "inline-flex", gap: space.xs, alignItems: "baseline" }}>
        <span style={{ color: flag === "need_check" ? colors.needCheck : undefined }}>
          {value || <span style={{ color: colors.needCheck }}>{T.noData}</span>}
        </span>
        <button
          type="button"
          title={JUDGE.evidence.open}
          onClick={() => setEvidence({ row, column })}
          style={{ border: "none", background: "none", cursor: "pointer", color: colors.primary, padding: 0 }}
        >
          ⓘ
        </button>
      </span>
    );
  };

  return (
    <div>
      <PageHeader title={E.title} sub={E.sub} actions={<ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      <Card
        actions={
          <label style={{ fontSize: font.sm }}>
            <input type="checkbox" checked={onlyCheck} onChange={(e) => setOnlyCheck(e.target.checked)} /> {E.onlyCheck}
          </label>
        }
      >
        {rows === null && error === null && <Skeleton lines={4} />}
        {rows && visible.length === 0 && <EmptyState text={E.empty} />}
        {visible.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>{P.rowCols.model}</th>
                <th style={th}>{P.rowCols.material}</th>
                <th style={th}>{P.rowCols.record}</th>
                <th style={th}>{P.rowCols.maker}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.row_id} style={{ color: row.status === "승인" ? colors.approved : colors.text }}>
                  <td style={td}>
                    {String(shown(row.cells[MODEL_COLUMN]) ?? row.model)}
                    {row.is_part && <Badge>{P.part}</Badge>}
                  </td>
                  <td style={td}>{cell(row, JUDGE_COLUMNS.material)}</td>
                  <td style={td}>{cell(row, JUDGE_COLUMNS.record)}</td>
                  <td style={td}>{cell(row, JUDGE_COLUMNS.maker)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {evidence && (
        <JudgeEvidence row={evidence.row} column={evidence.column} onClose={() => setEvidence(null)} onChanged={load} />
      )}
    </div>
  );
}
