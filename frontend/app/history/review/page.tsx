"use client";
// 탭 3. 검역 리스트 › ② 서류 대조·검수 (DESIGN 3-6, 검역 리스트 탭 3단계).
// 위: 선적 건별 요약(항목 수) + 미해결/해결됨/전체 필터(행 수, GET /history/review-rows 한 결과로) + [다시 대조].
// 왼쪽: 행 목록(B/L·모델·항목 칩·입력/확인 이유). HS 요청 11/27: 해결됨 필터가 비던 문제 고침.
// 오른쪽: 검수 패널(서류 값 나란히, AI 분석, 값 고르기·직접 입력·메모 → 저장). 담당: KHS
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { ListHeader } from "@/components/review/ListHeader";
import { LIST_BLUE, pillSecondary } from "@/components/review/listUi";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { notifyListChanged } from "@/components/review/useListSteps";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getReviewRows, runCrosscheck } from "@/lib/api/history";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { ReviewRows } from "@/lib/types/history";

const R = HOME.reviewPage;
type Filter = "open" | "done" | "all";

function ReviewInner() {
  const params = useSearchParams();
  const { shipperId, error: shipperError } = useShipper();
  const [data, setData] = useState<ReviewRows | null>(null);
  const [filter, setFilter] = useState<Filter>("open");
  const [active, setActive] = useState<string | null>(params.get("row"));
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    getReviewRows(shipperId).then(setData).catch(setError);
  }, [shipperId]);

  useEffect(() => {
    setData(null);
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

  // 필터 숫자·목록은 같은 결과(review-rows)에서 센다 — 숫자와 목록 개수가 항상 같다
  const all = data?.rows ?? [];
  const rows = all.filter((x) => (filter === "all" ? true : filter === "open" ? x.open_row : x.done_row));

  return (
    <div>
      <ListHeader title={T.side.list.review} onChanged={() => load()} showBadges={false} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      {note && <Notice>{note}</Notice>}

      <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap", marginBottom: space.sm }}>
        {(
          [
            ["open", `${R.open} ${data?.counts.open ?? 0}`],
            ["done", `${R.done} ${data?.counts.done ?? 0}`],
            ["all", `${R.all} ${data?.counts.all ?? 0}`],
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
        <button type="button" onClick={recheck} disabled={busy || !shipperId} style={{ ...pillSecondary, height: 38, marginLeft: "auto" }}>
          ⇆ {busy ? T.loading : R.recheck}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 300px) minmax(0, 1fr)", gap: space.md, alignItems: "start" }}>
        <Card style={{ padding: space.sm, marginBottom: 0 }}>
          {data === null && error === null && <Skeleton lines={5} />}
          {data && rows.length === 0 && <EmptyState text={filter === "open" ? R.noneOpen : R.none} />}
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
                      {x.name || x.model}
                      {x.name && x.model && (
                        <span style={{ fontWeight: 600, color: colors.muted }}>
                          {" "}· <span style={{ fontSize: 11 }}>{R.modelTag}</span> {x.model}
                        </span>
                      )}
                      {x.parts > 0 && <span style={{ fontSize: 12, color: colors.muted }}> ({R.partsCount(x.parts)})</span>}
                    </div>
                    <div style={{ fontSize: 12, color: x.bl ? colors.muted : colors.needInputText }}>
                      {x.bl_text}
                      {x.hint && <span style={{ color: colors.muted }}> · {x.hint}</span>}
                    </div>
                    {/* 칸 이름 칩 대신 할 일 한 줄. 자세한 칸은 오른쪽 패널에서(HS 11/27) */}
                    <div style={{ fontSize: 13, marginTop: 4, color: x.open.length ? colors.mismatch : x.open_row ? colors.needInputText : colors.ok }}>
                      {x.open_row ? "▸ " : "✓ "}
                      {x.todo}
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
