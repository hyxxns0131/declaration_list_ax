"use client";
// 탭 3. 검역 리스트 › ② 서류 대조·검수 (DESIGN 3-6, 검역 리스트 탭 3단계).
// 위: 선적 건별 불일치 요약 + 미해결/해결됨 필터 + [다시 대조]. 왼쪽: 불일치·검수 대기 행 목록(B/L·모델·항목 칩).
// 오른쪽: 검수 패널(서류 값 나란히, AI 분석, 값 고르기·직접 입력·메모 → 저장). 담당: KHS
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { ListHeader } from "@/components/review/ListHeader";
import { LIST_BLUE, STATE_STYLE, pillSecondary } from "@/components/review/listUi";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { notifyListChanged } from "@/components/review/useListSteps";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getHistory, getMismatches, runCrosscheck } from "@/lib/api/history";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { HistoryRow, MismatchItem } from "@/lib/types/history";

const R = HOME.reviewPage;
type Filter = "open" | "done" | "all";

function ReviewInner() {
  const params = useSearchParams();
  const { shipperId, error: shipperError } = useShipper();
  const [items, setItems] = useState<MismatchItem[] | null>(null);
  const [attention, setAttention] = useState<HistoryRow[]>([]);
  const [filter, setFilter] = useState<Filter>("open");
  const [active, setActive] = useState<string | null>(params.get("row"));
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    Promise.all([getMismatches(shipperId), getHistory(shipperId, { attention: true })])
      .then(([m, rows]) => {
        setItems(m);
        setAttention(rows);
      })
      .catch(setError);
  }, [shipperId]);

  useEffect(() => {
    setItems(null);
    load();
  }, [load]);

  const recheck = async () => {
    setBusy(true);
    setNote("");
    try {
      const out = await runCrosscheck(shipperId);
      setNote(R.rechecked(out.bls, out.unresolved));
      load();
      notifyListChanged();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  // 선적 건(B/L)별 요약
  const byBl = useMemo(() => {
    const m = new Map<string, { open: number; done: number }>();
    for (const it of items ?? []) {
      const k = it.bl_no || "(B/L 없음)";
      const cur = m.get(k) ?? { open: 0, done: 0 };
      if (it.status === "해결됨") cur.done += 1;
      else cur.open += 1;
      m.set(k, cur);
    }
    return [...m.entries()];
  }, [items]);

  // 행별 목록: 불일치 항목 + 대조 밖 검수 대기(확인 필요·자료 추가 필요) 행
  const rows = useMemo(() => {
    const map = new Map<string, { row_id: string; bl: string; model: string; open: string[]; done: string[]; other: boolean }>();
    for (const it of items ?? []) {
      const cur = map.get(it.row_id) ?? { row_id: it.row_id, bl: it.bl_no, model: it.model + (it.is_part ? " 부분품" : ""), open: [], done: [], other: false };
      (it.status === "해결됨" ? cur.done : cur.open).push(it.item);
      map.set(it.row_id, cur);
    }
    for (const r of attention) {
      if (map.has(r.row_id)) continue;
      const bl = String(r.cells["B/L Number"]?.final_value ?? r.cells["B/L Number"]?.ai_value ?? "");
      map.set(r.row_id, { row_id: r.row_id, bl, model: r.model, open: [], done: [], other: true });
    }
    return [...map.values()].filter((x) =>
      filter === "all" ? true : filter === "open" ? x.open.length > 0 || x.other : x.done.length > 0 && x.open.length === 0,
    );
  }, [items, attention, filter]);

  const openCount = (items ?? []).filter((i) => i.status !== "해결됨").length;
  const doneCount = (items ?? []).filter((i) => i.status === "해결됨").length;

  return (
    <div>
      <ListHeader title={T.side.list.review} onChanged={() => load()} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      {note && <Notice>{note}</Notice>}

      <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap", marginBottom: space.sm }}>
        {(
          [
            ["open", `${R.open} ${openCount}`],
            ["done", `${R.done} ${doneCount}`],
            ["all", R.all],
          ] as [Filter, string][]
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            aria-pressed={filter === k}
            onClick={() => setFilter(k)}
            style={{
              borderRadius: 999,
              padding: `4px ${space.md - 4}px`,
              fontSize: font.md,
              fontWeight: 700,
              border: `1px solid ${filter === k ? LIST_BLUE : colors.border}`,
              background: filter === k ? colors.primarySoft : "#fff",
              color: filter === k ? LIST_BLUE : colors.text,
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
        <span style={{ display: "flex", gap: space.xs, flexWrap: "wrap", marginLeft: space.sm }}>
          {byBl.map(([bl, c]) => (
            <span key={bl} style={{ fontSize: font.sm, background: colors.cardBg, borderRadius: 999, padding: "3px 10px", fontVariantNumeric: "tabular-nums" }}>
              {bl} · <b style={{ color: c.open ? colors.mismatch : colors.ok }}>{R.openShort} {c.open}</b> · {R.done} {c.done}
            </span>
          ))}
        </span>
        <button type="button" onClick={recheck} disabled={busy || !shipperId} style={{ ...pillSecondary, height: 38, marginLeft: "auto" }}>
          ⇆ {busy ? T.loading : R.recheck}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 300px) minmax(0, 1fr)", gap: space.md, alignItems: "start" }}>
        <Card style={{ padding: space.sm, marginBottom: 0 }}>
          {items === null && error === null && <Skeleton lines={5} />}
          {items && rows.length === 0 && <EmptyState text={filter === "open" ? R.noneOpen : R.none} />}
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 4 }}>
            {rows.map((x) => {
              const on = active === x.row_id;
              return (
                <li key={x.row_id}>
                  <button
                    type="button"
                    aria-current={on ? "true" : undefined}
                    onClick={() => setActive(x.row_id)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      border: `1px solid ${on ? LIST_BLUE : "transparent"}`,
                      background: on ? colors.primarySoft : "#fff",
                      borderRadius: 10,
                      padding: `${space.sm}px ${space.sm + 2}px`,
                      cursor: "pointer",
                      font: "inherit",
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: font.md }}>
                      {x.bl || "—"} · {x.model || "모델 미상"}
                    </div>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                      {x.open.map((n) => (
                        <span key={n} style={{ fontSize: 11, fontWeight: 700, borderRadius: 999, padding: "1px 8px", background: STATE_STYLE.mismatch.bg, color: STATE_STYLE.mismatch.color }}>
                          {n}
                        </span>
                      ))}
                      {x.done.map((n) => (
                        <span key={n} style={{ fontSize: 11, fontWeight: 700, borderRadius: 999, padding: "1px 8px", background: STATE_STYLE.manual.bg, color: STATE_STYLE.manual.color }}>
                          ✎ {n}
                        </span>
                      ))}
                      {x.other && (
                        <span style={{ fontSize: 11, fontWeight: 700, borderRadius: 999, padding: "1px 8px", background: STATE_STYLE.review.bg, color: STATE_STYLE.review.color }}>
                          {STATE_STYLE.review.text}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>
        <Card style={{ marginBottom: 0 }}>
          {active ? (
            <ReviewPanel key={active} rowId={active} onConfirmed={() => load()} onClose={() => setActive(null)} />
          ) : (
            <EmptyState text={R.pick} />
          )}
        </Card>
      </div>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<Skeleton lines={6} />}>
      <ReviewInner />
    </Suspense>
  );
}
