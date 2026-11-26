"use client";
// 탭 3. 검역 리스트 › 확인 필요 (DESIGN 3-6). 확인할 행 목록 + 검수 패널. 배치만 한다. 담당: KHS
import { useCallback, useEffect, useState } from "react";

import { ReviewPanel } from "@/components/review/ReviewPanel";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { EmptyState, ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getHistory } from "@/lib/api/history";
import { shown } from "@/lib/format";
import { useShipper } from "@/lib/hooks/useShipper";
import { HOME } from "@/lib/text/home";
import type { Flag, HistoryRow } from "@/lib/types/history";

const R = HOME.review;
const BL = "B/L Number";
const FLAG_LABEL: Partial<Record<Flag, { text: string; tone: "mismatch" | "needCheck" | "needInput" | "edited" }>> = {
  mismatch: { text: "■ 서류와 다름", tone: "mismatch" },
  need_check: { text: "? 확인 필요", tone: "needCheck" },
  need_input: { text: "자료 추가 필요", tone: "needInput" },
  edited: { text: "✎ 수정", tone: "edited" },
};

const th = { textAlign: "left", padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.sm, color: colors.muted } as const;
const td = { padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.md, verticalAlign: "top" } as const;

export default function ReviewListPage() {
  const { shippers, shipperId, setShipperId, error: shipperError } = useShipper();
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    getHistory(shipperId, { attention: true }).then(setRows).catch(setError);
  }, [shipperId]);

  useEffect(() => {
    setRows(null);
    setActive(null);
    load();
  }, [load]);

  const flagsOf = (r: HistoryRow) => {
    const set = new Set(Object.values(r.cells).map((c) => c.flag));
    return (Object.keys(FLAG_LABEL) as Flag[]).filter((f) => set.has(f));
  };

  return (
    <div>
      <PageHeader title={R.title} sub={R.sub} actions={<ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      <Card>
        {rows === null && error === null && <Skeleton lines={4} />}
        {rows && rows.length === 0 && <EmptyState text={R.empty} />}
        {rows && rows.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>{R.cols.bl}</th>
                <th style={th}>{R.cols.model}</th>
                <th style={th}>{R.cols.status}</th>
                <th style={th}>{R.cols.flags}</th>
                <th style={th}>{R.cols.confirmed}</th>
                <th style={th} />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.row_id} style={{ background: active === r.row_id ? colors.primarySoft : undefined }}>
                  <td style={td}>{String(shown(r.cells[BL]) ?? "") || <span style={{ color: colors.needCheck }}>?</span>}</td>
                  <td style={td}>{r.model || "-"}</td>
                  <td style={td}>{r.status}</td>
                  <td style={td}>
                    <span style={{ display: "inline-flex", gap: space.xs, flexWrap: "wrap" }}>
                      {flagsOf(r).map((f) => (
                        <Badge key={f} tone={FLAG_LABEL[f]?.tone}>
                          {FLAG_LABEL[f]?.text}
                        </Badge>
                      ))}
                    </span>
                  </td>
                  <td style={td}>{r.confirmed ? <Badge tone="ok">✓ {R.done}</Badge> : "-"}</td>
                  <td style={td}>
                    <Button small onClick={() => setActive(r.row_id)}>
                      {R.open}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {active && <ReviewPanel rowId={active} onConfirmed={load} onClose={() => setActive(null)} />}
    </div>
  );
}
