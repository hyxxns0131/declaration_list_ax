"use client";
// 탭 3. 검역 리스트 › ③ 완성된 검역 리스트 (메인 화면, DESIGN 3장). 공통 머리(화주·배지·서류 올리기·새로고침)
// + 단계 표시줄 + 화면 높이를 채우는 표 + 오른쪽 검수 서랍. 품목사항은 탭 5에서 만든다. 배치와 상태 연결만. 담당: KHS
// 검역 리스트 탭 0단계(HS 요청 11/26): 머리·단계 표시줄을 ListHeader로 바꿈.
// 4단계: 표를 ListTable(칸 묶음·고정 칸·출처 표시·검수 필요 → ②)로 바꾸고 [등록 정보 채우기](POST /history/fill)를 둠.
import { useCallback, useEffect, useMemo, useState } from "react";

import { CellEditor } from "@/components/home/CellEditor";
import { JudgeEvidence } from "@/components/judge/JudgeEvidence";
import { UploadDialog } from "@/components/reader/UploadDialog";
import { ListHeader, type BadgeFilter } from "@/components/review/ListHeader";
import { ListTable } from "@/components/review/ListTable";
import { pillPrimary, pillSecondary } from "@/components/review/listUi";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { notifyListChanged } from "@/components/review/useListSteps";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { integrations } from "@/lib/api/core";
import { fillFromRegistry, getColumns, getHistory, moveRow } from "@/lib/api/history";
import { getDeclarations } from "@/lib/api/judge";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { Integrations } from "@/lib/types/core";
import type { Columns, Declaration, HistoryRow } from "@/lib/types/history";

/** 표 높이: 화면 높이에서 위 탭 줄·머리·단계 표시줄을 뺀 나머지 */
const TABLE_HEIGHT = "calc(100vh - 300px)";

function matches(r: HistoryRow, f: BadgeFilter | null): boolean {
  const cells = Object.values(r.cells);
  if (f === "need_input") return cells.some((c) => c.flag === "need_input");
  if (f === "mismatch") return !r.confirmed && cells.some((c) => c.flag === "mismatch");
  if (f === "review") return r.status !== "승인" && cells.some((c) => (r.confirmed ? c.flag === "need_input" : ["mismatch", "need_check", "need_input"].includes(c.flag)));
  if (f === "manual") return cells.some((c) => c.final_value !== null && c.final_value !== undefined);
  return true;
}

export default function HistoryPage() {
  const { shipperId, shipperName } = useShipper();
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [decls, setDecls] = useState<Declaration[]>([]);
  const [cols, setCols] = useState<Columns | null>(null);
  const [info, setInfo] = useState<Integrations | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState<BadgeFilter | null>(null);
  const [allCols, setAllCols] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [active, setActive] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<{ row: HistoryRow; column: string } | null>(null);
  const [evidence, setEvidence] = useState<{ row: HistoryRow; column: string } | null>(null);

  useEffect(() => {
    integrations().then(setInfo).catch(() => setInfo(null));
  }, []);

  const load = useCallback(async () => {
    if (!shipperId) return;
    setError(null);
    try {
      const [r, d, c] = await Promise.all([getHistory(shipperId), getDeclarations(shipperId), getColumns(shipperId)]);
      setRows(r);
      setDecls(d);
      setCols(c);
    } catch (e) {
      setError(e); // 이미 보이던 데이터는 남긴다(DESIGN 3-5)
    }
  }, [shipperId]);

  useEffect(() => {
    setRows(null);
    setSelected(new Set());
    setActive(null);
    load();
  }, [shipperId, load]);

  const columns = useMemo(() => {
    if (!cols) return [];
    let list = allCols ? [...cols.columns] : [...cols.default_view];
    if (allCols && !showHidden) list = list.filter((c) => !cols.hidden.includes(c));
    // 색상 열: 화주 설정(group_by_color)으로 켠다. 화주를 모르면 행에 색상이 있을 때만
    const showColor = cols.show_color ?? Boolean(rows?.some((r) => r.cells[cols.color_column]));
    if (showColor) {
      const i = list.findIndex((c) => c.startsWith("재질 ("));
      list.splice(i + 1, 0, cols.color_column);
    }
    return list;
  }, [cols, allCols, showHidden, rows]);

  const visible = useMemo(() => (rows ?? []).filter((r) => matches(r, filter)), [rows, filter]);
  const selectedIds = useMemo(() => (rows ?? []).filter((r) => selected.has(r.row_id)).map((r) => r.row_id), [rows, selected]);

  const [filling, setFilling] = useState(false);
  const fill = async () => {
    setFilling(true);
    try {
      const out = await fillFromRegistry(shipperId);
      setMessage(HOME.listTable.filled(out.judged, out.need_registry));
      await reload();
    } catch (e) {
      setError(e);
    } finally {
      setFilling(false);
    }
  };

  const reload = async () => {
    await load();
    notifyListChanged();
  };

  const onMove = async (rowId: string, dir: -1 | 1) => {
    if (!rows) return;
    const i = rows.findIndex((r) => r.row_id === rowId);
    const before = dir < 0 ? rows[i - 1]?.row_id ?? null : rows[i + 2]?.row_id ?? null;
    if (dir < 0 && i === 0) return;
    try {
      await moveRow(rowId, before);
      await load();
    } catch (e) {
      setError(e);
    }
  };

  return (
    <div>
      <ListHeader
        title={T.side.list.table}
        filter={filter}
        onFilter={setFilter}
        onMessage={setMessage}
        onChanged={async (ids) => {
          await load();
          if (ids?.[0]) setActive(ids[0]);
        }}
      />

      {info && !info.llm.ok && <Notice>{T.integrations.llmOff}</Notice>}
      {info && info.unipass.mode !== "live" && <Notice>{T.integrations.unipassMock}</Notice>}
      {message && <Notice>{message}</Notice>}
      {error !== null && <ErrorLine error={error} onRetry={load} />}

      <div style={{ display: "flex", alignItems: "center", gap: space.md, fontSize: font.sm, margin: `${space.xs}px 0` }}>
        <label style={{ whiteSpace: "nowrap" }}>
          <input type="checkbox" checked={allCols} onChange={(e) => setAllCols(e.target.checked)} /> {HOME.allColumns}
        </label>
        {allCols && (
          <label style={{ whiteSpace: "nowrap" }}>
            <input type="checkbox" checked={showHidden} onChange={(e) => setShowHidden(e.target.checked)} /> {HOME.showHidden}
          </label>
        )}
        {selectedIds.length > 0 && (
          <span>
            {HOME.selectedCount(selectedIds.length)}{" "}
            <Button small variant="ghost" onClick={() => setSelected(new Set())}>
              선택 해제
            </Button>
          </span>
        )}
        <span
          style={{ marginLeft: "auto", color: colors.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}
          title={HOME.listTable.legend}
        >
          {HOME.listTable.legend}
        </span>
        <button type="button" style={{ ...pillSecondary, height: 34 }} disabled={!shipperId || filling} onClick={fill}>
          {filling ? HOME.listTable.filling : HOME.listTable.fill}
        </button>
      </div>

      {!shipperId && <EmptyState text={T.pickShipper} />}
      {shipperId && rows === null && error === null && <Skeleton lines={8} />}
      {rows && rows.length === 0 && (
        <EmptyState
          text={HOME.emptyRows}
          action={
            <button type="button" style={pillPrimary} onClick={() => setUploadOpen(true)}>
              ⇪ {HOME.buttons.upload}
            </button>
          }
        />
      )}
      {rows && rows.length > 0 && (
        <ListTable
          rows={visible}
          columns={columns}
          declarations={decls}
          selected={selected}
          activeRowId={active}
          maxHeight={TABLE_HEIGHT}
          onSelect={(id, on) => {
            const next = new Set(selected);
            if (on) next.add(id);
            else next.delete(id);
            setSelected(next);
          }}
          onSelectGroup={(ids) => setSelected(new Set(ids))}
          onOpenReview={setActive}
          onEdit={(row, column) => setEditing({ row, column })}
          onOpenEvidence={(row, column) => setEvidence({ row, column })}
          onMove={onMove}
        />
      )}

      {active && (
        // 검수 패널은 오른쪽 서랍: 표를 가리지 않고 넓게 두기 위해 (로직 점검 반영 11/25)
        <aside
          aria-label={HOME.review.title}
          style={{
            position: "fixed",
            top: 0,
            right: 0,
            bottom: 0,
            width: "min(560px, 92vw)",
            background: colors.bg,
            boxShadow: "-12px 0 32px rgba(15, 23, 42, 0.18)",
            zIndex: 20,
            overflowY: "auto",
            padding: `${space.sm}px ${space.lg}px ${space.lg}px`,
          }}
        >
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Button small variant="ghost" onClick={() => setActive(null)} aria-label={HOME.closePanel}>
              ✕ {T.close}
            </Button>
          </div>
          <ReviewPanel rowId={active} onConfirmed={() => reload()} onClose={() => setActive(null)} />
        </aside>
      )}

      {uploadOpen && (
        <UploadDialog
          shipperId={shipperId}
          shipperName={shipperName}
          onClose={() => setUploadOpen(false)}
          onUploaded={async (ids) => {
            await reload();
            if (ids[0]) setActive(ids[0]);
          }}
        />
      )}
      {editing && (
        <CellEditor row={editing.row} column={editing.column} onClose={() => setEditing(null)} onSaved={reload} />
      )}
      {evidence && (
        <JudgeEvidence row={evidence.row} column={evidence.column} onClose={() => setEvidence(null)} onChanged={reload} />
      )}
    </div>
  );
}
