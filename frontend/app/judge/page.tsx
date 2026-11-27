"use client";
// 탭 4. 재질·실적 판단 › 신고건 묶음 (DESIGN 5장). 부품 배치와 상태 연결만 한다 — 데이터는 judge·history API에서. 담당: LSY
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";

import { ItemSheetButton } from "@/components/judge/ItemSheetButton";
import { JUDGE_COLUMNS, JudgeEvidence } from "@/components/judge/JudgeEvidence";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { shippers as getShippers } from "@/lib/api/core";
import { getHistory } from "@/lib/api/history";
import { computeDeclarations, getDeclarations } from "@/lib/api/judge";
import { fmtDate, shown } from "@/lib/format";
import { T } from "@/lib/text/common";
import { JUDGE } from "@/lib/text/judge";
import type { Shipper } from "@/lib/types/core";
import type { Declaration, HistoryRow } from "@/lib/types/history";
import { SHIPPER_KEY, rememberShipper } from "@/lib/hooks/useShipper";

const P = JUDGE.page;
const MODEL_COLUMN = "한글 제품명(모델넘버)";

const th = { textAlign: "left", padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.sm } as const;
const td = { padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.md, verticalAlign: "top" } as const;

export default function JudgePage() {
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [shipperId, setShipperId] = useState("");
  const [decls, setDecls] = useState<Declaration[] | null>(null);
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [evidence, setEvidence] = useState<{ row: HistoryRow; column: string } | null>(null);
  // 행 체크박스는 '고르기'만 한다. 품목사항은 도구 줄의 별도 버튼으로 만든다(시연 피드백 11/27)
  const [picked, setPicked] = useState<Set<string>>(new Set());

  useEffect(() => {
    getShippers()
      .then((list) => {
        setShippers(list);
        const saved = window.localStorage.getItem(SHIPPER_KEY);
        setShipperId(list.find((s) => s.shipper_id === saved)?.shipper_id ?? list[0]?.shipper_id ?? "");
      })
      .catch(setError);
  }, []);

  const load = useCallback(async () => {
    if (!shipperId) return;
    setError(null);
    try {
      const [d, r] = await Promise.all([getDeclarations(shipperId), getHistory(shipperId)]);
      setDecls(d);
      setRows(r);
    } catch (e) {
      setError(e);
    }
  }, [shipperId]);

  useEffect(() => {
    setDecls(null);
    setOpen(new Set());
    setPicked(new Set());
    setMessage("");
    load();
    if (shipperId) rememberShipper(shipperId);
  }, [shipperId, load]);

  const byId = useMemo(() => new Map(rows.map((r) => [r.row_id, r])), [rows]);

  const recompute = async () => {
    setBusy(true);
    setMessage("");
    try {
      const d = await computeDeclarations(shipperId);
      setMessage(P.recomputed(d.length));
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const allRowIds = useMemo(() => (decls ?? []).flatMap((d) => d.row_ids), [decls]);
  // 화면(표) 순서를 지켜서 넘긴다 — 첫 행이 대표품목
  const pickedIds = useMemo(() => allRowIds.filter((id) => picked.has(id)), [allRowIds, picked]);
  const pick = (ids: string[], on: boolean) => {
    const next = new Set(picked);
    ids.forEach((id) => (on ? next.add(id) : next.delete(id)));
    setPicked(next);
  };
  const pickGroup = (d: Declaration) => {
    setPicked(new Set(d.row_ids));
    setOpen(new Set([...open, d.declaration_id]));
  };

  const toggle = (id: string) => {
    const next = new Set(open);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpen(next);
  };

  const cell = (row: HistoryRow, column: string) => {
    const value = String(shown(row.cells[column]) ?? "");
    return (
      <span style={{ display: "inline-flex", gap: space.xs, alignItems: "baseline" }}>
        <span>{value || <span style={{ color: colors.needCheck }}>{T.noData}</span>}</span>
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
      <PageHeader
        title={P.title}
        sub={P.sub}
        actions={
          <>
            <ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />
            <Button onClick={recompute} disabled={!shipperId || busy}>
              ⟳ {busy ? P.recomputing : P.recompute}
            </Button>
          </>
        }
      />
      {message && <Notice>{message}</Notice>}
      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {!shipperId && <EmptyState text={T.pickShipper} />}
      {shipperId && decls === null && error === null && <Skeleton lines={4} />}
      {decls && decls.length === 0 && <EmptyState text={P.empty} />}

      {decls && decls.length > 0 && (
        <Card>
          <div
            style={{
              display: "flex",
              gap: space.sm,
              alignItems: "flex-start",
              justifyContent: "space-between",
              flexWrap: "wrap",
              marginBottom: space.sm,
            }}
          >
            <div style={{ display: "flex", gap: space.xs, alignItems: "center", flexWrap: "wrap" }}>
              <Button small onClick={() => setPicked(new Set(allRowIds))}>
                {P.selectAll}
              </Button>
              <Button small variant="ghost" onClick={() => setPicked(new Set())} disabled={!picked.size}>
                {P.clearAll}
              </Button>
              <span style={{ color: colors.muted, fontSize: font.sm }}>{P.pickedCount(pickedIds.length)}</span>
            </div>
            <ItemSheetButton
              shipperId={shipperId}
              selectedRowIds={pickedIds}
              onCreated={() => setPicked(new Set())}
              showReasons
            />
          </div>
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
            {decls.map((d, i) => {
              const isOpen = open.has(d.declaration_id);
              return (
                <Fragment key={d.declaration_id}>
                  <tr style={{ background: colors.bgSubtle }}>
                    <td style={td}>
                      <Button small variant="ghost" onClick={() => toggle(d.declaration_id)}>
                        {isOpen ? "▾" : "▸"} {P.group(i + 1)}
                      </Button>
                    </td>
                    <td style={td}>
                      {d.key.vessel_key.replace(/^모선명:/, "") || "-"}
                      {d.arrival_date && (
                        <div style={{ color: colors.muted, fontSize: font.sm }}>반입 {fmtDate(d.arrival_date)}</div>
                      )}
                    </td>
                    <td style={td}>{d.key.factory_code || "-"}</td>
                    <td style={td}>
                      {d.key.material || "-"} {d.key.color && <Badge>{d.key.color}</Badge>}
                    </td>
                    <td style={td}>{d.record_nos.join(", ") || <span style={{ color: colors.needCheck }}>{T.noData}</span>}</td>
                    <td style={td}>{d.row_ids.length}</td>
                    <td style={td}>
                      {d.warnings.map((w) => (
                        <Badge key={w} tone="needCheck" title={w}>
                          ? {w}
                        </Badge>
                      ))}
                    </td>
                    <td style={td}>
                      <Button small onClick={() => pickGroup(d)}>
                        {P.pickGroup}
                      </Button>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr>
                      <td colSpan={8} style={{ padding: `${space.xs}px ${space.lg}px ${space.md}px` }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr>
                              <th style={{ ...th, width: 28 }}>
                                <input
                                  type="checkbox"
                                  aria-label={P.pickGroup}
                                  checked={d.row_ids.every((id) => picked.has(id))}
                                  onChange={(e) => pick(d.row_ids, e.target.checked)}
                                />
                              </th>
                              <th style={th}>{P.rowCols.model}</th>
                              <th style={th}>{P.rowCols.material}</th>
                              <th style={th}>{P.rowCols.record}</th>
                              <th style={th}>{P.rowCols.maker}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {d.row_ids.map((id) => {
                              const row = byId.get(id);
                              if (!row) {
                                return (
                                  <tr key={id}>
                                    <td colSpan={5} style={{ ...td, color: colors.muted }}>
                                      {id} · {P.rowMissing}
                                    </td>
                                  </tr>
                                );
                              }
                              return (
                                <tr key={id} style={{ color: row.status === "승인" ? colors.approved : colors.text }}>
                                  <td style={td}>
                                    <input
                                      type="checkbox"
                                      aria-label={P.pickRow(String(shown(row.cells[MODEL_COLUMN]) ?? row.model))}
                                      checked={picked.has(id)}
                                      onChange={(e) => pick([id], e.target.checked)}
                                    />
                                  </td>
                                  <td style={td}>
                                    {String(shown(row.cells[MODEL_COLUMN]) ?? row.model)}
                                    {row.is_part && <Badge>{P.part}</Badge>}
                                  </td>
                                  <td style={td}>{cell(row, JUDGE_COLUMNS.material)}</td>
                                  <td style={td}>{cell(row, JUDGE_COLUMNS.record)}</td>
                                  <td style={td}>{cell(row, JUDGE_COLUMNS.maker)}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        </Card>
      )}

      {evidence && (
        <JudgeEvidence row={evidence.row} column={evidence.column} onClose={() => setEvidence(null)} onChanged={load} />
      )}
    </div>
  );
}
