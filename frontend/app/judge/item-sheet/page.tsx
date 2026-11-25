"use client";
// 탭 3. 재질·실적 판단 › 품목사항 엑셀 (DESIGN 5-1). 신고건마다 [품목사항 만들기]. 배치만 한다. 담당: LSY
import { useCallback, useEffect, useState } from "react";

import { ItemSheetButton } from "@/components/judge/ItemSheetButton";
import { Badge } from "@/components/ui/Badge";
import { Card, PageHeader } from "@/components/ui/Card";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { EmptyState, ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getDeclarations } from "@/lib/api/judge";
import { fmtDate } from "@/lib/format";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { JUDGE } from "@/lib/text/judge";
import type { Declaration } from "@/lib/types/history";

const P = JUDGE.page;
const I = JUDGE.itemSheetPage;

const th = { textAlign: "left", padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.sm, color: colors.muted } as const;
const td = { padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.md, verticalAlign: "top" } as const;

export default function ItemSheetPage() {
  const { shippers, shipperId, setShipperId, error: shipperError } = useShipper();
  const [decls, setDecls] = useState<Declaration[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    getDeclarations(shipperId).then(setDecls).catch(setError);
  }, [shipperId]);

  useEffect(() => {
    setDecls(null);
    load();
  }, [load]);

  return (
    <div>
      <PageHeader title={I.title} sub={I.sub} actions={<ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      <Card>
        {decls === null && error === null && <Skeleton lines={4} />}
        {decls && decls.length === 0 && <EmptyState text={P.empty} />}
        {decls && decls.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th} />
                <th style={th}>{P.cols.vessel}</th>
                <th style={th}>{P.cols.factory}</th>
                <th style={th}>{P.cols.material}</th>
                <th style={th}>{P.cols.records}</th>
                <th style={th}>{P.cols.rows}</th>
                <th style={th}>{P.cols.warnings}</th>
                <th style={th} />
              </tr>
            </thead>
            <tbody>
              {decls.map((d, i) => (
                <tr key={d.declaration_id}>
                  <td style={td}>{P.group(i + 1)}</td>
                  <td style={td}>
                    {d.key.vessel_key.replace(/^모선명:/, "") || "-"}
                    {d.arrival_date && <div style={{ color: colors.muted, fontSize: font.sm }}>반입 {fmtDate(d.arrival_date)}</div>}
                  </td>
                  <td style={td}>{d.key.factory_code || "-"}</td>
                  <td style={td}>
                    {d.key.material || "-"} {d.key.color && <Badge>{d.key.color}</Badge>}
                  </td>
                  <td style={td}>{d.record_nos.join(", ") || <span style={{ color: colors.needCheck }}>{T.noData}</span>}</td>
                  <td style={td}>{d.row_ids.length}</td>
                  <td style={td}>
                    {d.warnings.length > 0 ? <Badge tone="needCheck" title={d.warnings.join("\n")}>? {d.warnings.length}</Badge> : "-"}
                  </td>
                  <td style={td}>
                    <ItemSheetButton shipperId={shipperId} selectedRowIds={d.row_ids} onCreated={() => undefined} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
