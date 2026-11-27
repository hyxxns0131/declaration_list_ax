"use client";
// 탭 5. 품목사항 엑셀 (DESIGN 5-1, HS 요청 11/26: 판단 탭에서 분리). 담당: LSY (품목사항 로직 a3_judge/item_sheet)
// - 신고건마다 [품목사항 만들기] (예전과 같음)
// - [신고용: 신고건별 ZIP]: 검사를 통과한 모든 신고건 → ZIP(신고건마다 xlsx + 검토용 전체 + 제외됨.txt)
// - [검토용 전체 엑셀]: 시트 1장, 신고건 사이 빈 행, 막힌 건도 이유와 함께(신고용 아님, 시연 피드백 11/27)
// - [같은 품목끼리 내려받기]: 재질·제조업소·품목·실적번호로 묶어 고른 묶음만 ZIP. 신고건을 합치지는 않는다
import { useCallback, useEffect, useState } from "react";

import { ItemSheetButton } from "@/components/judge/ItemSheetButton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { createItemBulk, downloadItemBulk, downloadItemReview, getDeclarations, getItemGroups } from "@/lib/api/judge";
import { fmtDate } from "@/lib/format";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { JUDGE } from "@/lib/text/judge";
import type { Declaration } from "@/lib/types/history";
import type { ItemBulkOut, ItemGroup, ItemGroupBasis } from "@/lib/types/judge";

const P = JUDGE.page;
const I = JUDGE.itemSheetPage;
const BASES: ItemGroupBasis[] = ["material", "factory", "product", "record"];

export default function ItemSheetPage() {
  const { shipperId, shipperName, error: shipperError } = useShipper();
  const [decls, setDecls] = useState<Declaration[] | null>(null);
  const [basis, setBasis] = useState<ItemGroupBasis>("material");
  const [groups, setGroups] = useState<ItemGroup[] | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ItemBulkOut | null>(null);
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

  useEffect(() => {
    if (!shipperId) return;
    setGroups(null);
    setPicked(new Set());
    getItemGroups(shipperId, basis).then(setGroups).catch(setError);
  }, [shipperId, basis]);

  const run = async (opts: Parameters<typeof createItemBulk>[1]) => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const out = await createItemBulk(shipperId, opts);
      setResult(out);
      await downloadItemBulk(out.file_id, out.filename);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const review = async () => {
    setBusy(true);
    setError(null);
    try {
      await downloadItemReview(shipperId, I.reviewFile(shipperId));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const toggle = (key: string, on: boolean) => {
    const next = new Set(picked);
    if (on) next.add(key);
    else next.delete(key);
    setPicked(next);
  };

  return (
    <div>
      <PageHeader
        title={I.title}
        sub={I.sub}
        actions={
          <>
            <span style={{ fontSize: font.sm, color: colors.muted }}>
              {T.shipperPick.current}: {shipperName}
            </span>
            <Button disabled={!shipperId || busy || !decls?.length} onClick={review} title={I.reviewHint}>
              ⇩ {I.review}
            </Button>
            <Button variant="primary" disabled={!shipperId || busy || !decls?.length} onClick={() => run({})} title={I.allHint}>
              ⇩ {busy ? I.making : I.all}
            </Button>
          </>
        }
      />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}

      {result && (
        <Card title={I.done(result.included.length, result.excluded.length)}>
          {result.excluded.length > 0 && (
            <>
              <div style={{ fontSize: font.sm, fontWeight: 700, marginBottom: space.xs }}>{I.excludedTitle}</div>
              <ul style={{ margin: 0, paddingLeft: space.lg, fontSize: font.sm }}>
                {result.excluded.map((x) => (
                  <li key={x.declaration_id}>
                    {P.group(x.number)}: <span style={{ color: colors.needCheck }}>{x.reasons.join(" / ")}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {result.excluded.length === 0 && <Notice>{result.filename}</Notice>}
        </Card>
      )}

      <Card title={I.byGroup}>
        <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap", marginBottom: space.sm }}>
          <span style={{ fontSize: font.sm }}>{I.basis}</span>
          {BASES.map((b) => (
            <Badge key={b} tone={b === basis ? "info" : "neutral"} active={b === basis} onClick={() => setBasis(b)}>
              {I.bases[b]}
            </Badge>
          ))}
          <Button
            style={{ marginLeft: "auto" }}
            disabled={!picked.size || busy}
            onClick={() => run({ groupBy: basis, groups: [...picked] })}
          >
            ⇩ {busy ? I.making : I.downloadGroups(picked.size)}
          </Button>
        </div>
        {groups === null && <Skeleton lines={2} />}
        {groups && groups.length === 0 && <EmptyState text={P.empty} />}
        {groups && groups.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: space.sm }}>
            {groups.map((g) => (
              <label
                key={g.key}
                style={{
                  display: "flex",
                  gap: space.sm,
                  alignItems: "flex-start",
                  background: picked.has(g.key) ? colors.primarySoft : colors.bg,
                  border: `1px solid ${picked.has(g.key) ? colors.brand : colors.line}`,
                  borderRadius: 10,
                  padding: `${space.sm}px ${space.md - 4}px`,
                  cursor: "pointer",
                  minWidth: 200,
                }}
              >
                <input type="checkbox" checked={picked.has(g.key)} onChange={(e) => toggle(g.key, e.target.checked)} />
                <span>
                  <strong>{g.label}</strong>
                  <div style={{ fontSize: font.sm, color: colors.muted }}>{I.groupCount(g.count, g.numbers)}</div>
                </span>
              </label>
            ))}
          </div>
        )}
        <p style={{ margin: `${space.sm}px 0 0`, fontSize: font.sm, color: colors.muted }}>{I.groupNote}</p>
      </Card>

      <Card title={I.one}>
        {decls === null && error === null && <Skeleton lines={4} />}
        {decls && decls.length === 0 && <EmptyState text={P.empty} />}
        {decls && decls.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th />
                <th>{P.cols.vessel}</th>
                <th>{P.cols.factory}</th>
                <th>{P.cols.material}</th>
                <th>{P.cols.records}</th>
                <th>{P.cols.rows}</th>
                <th>{P.cols.warnings}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {decls.map((d, i) => (
                <tr key={d.declaration_id}>
                  <td style={{ whiteSpace: "nowrap" }}>{P.group(i + 1)}</td>
                  <td>
                    {d.key.vessel_key.replace(/^모선명:/, "") || <span style={{ color: colors.needCheck }}>? 확인 필요</span>}
                    {d.arrival_date && <div style={{ color: colors.muted, fontSize: font.sm }}>반입 {fmtDate(d.arrival_date)}</div>}
                  </td>
                  <td>{d.key.factory_code || "-"}</td>
                  <td>
                    {d.key.material || "-"} {d.key.color && <Badge>{d.key.color}</Badge>}
                  </td>
                  <td>{d.record_nos.join(", ") || <span style={{ color: colors.needCheck }}>{T.noData}</span>}</td>
                  <td>{d.row_ids.length}</td>
                  <td>
                    {d.warnings.length > 0 ? <Badge tone="needCheck" title={d.warnings.join("\n")}>? {d.warnings.length}</Badge> : "-"}
                  </td>
                  <td>
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
