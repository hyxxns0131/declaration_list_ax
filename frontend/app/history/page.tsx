"use client";
// 탭 3. 검역 리스트 › 검역이력 표 (DESIGN 3장). 부품 배치와 상태 연결만 한다 — 데이터는 각 담당 API에서. 담당: KHS
import { useCallback, useEffect, useMemo, useState } from "react";

import { CellEditor } from "@/components/home/CellEditor";
import { HistoryTable } from "@/components/home/HistoryTable";
import { TopBar, type HomeFilter } from "@/components/home/TopBar";
import { ItemSheetButton } from "@/components/judge/ItemSheetButton";
import { JudgeEvidence } from "@/components/judge/JudgeEvidence";
import { UploadDialog } from "@/components/reader/UploadDialog";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { integrations, shippers as getShippers } from "@/lib/api/core";
import { getBadges, getColumns, getHistory, moveRow, refreshHistory } from "@/lib/api/history";
import { getDeclarations } from "@/lib/api/judge";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { Integrations, Shipper } from "@/lib/types/core";
import type { Badges, Columns, Declaration, HistoryRow } from "@/lib/types/history";
import { SHIPPER_KEY, rememberShipper } from "@/lib/hooks/useShipper";


/** 표 높이: 화면 높이에서 위 탭 줄·여백·도구 줄을 뺀 나머지(1366×768에서 약 15행 이상) */
const TABLE_HEIGHT = "calc(100vh - 230px)";

export default function HistoryPage() {
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [shipperId, setShipperId] = useState("");
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [decls, setDecls] = useState<Declaration[]>([]);
  const [badges, setBadges] = useState<Badges | null>(null);
  const [cols, setCols] = useState<Columns | null>(null);
  const [info, setInfo] = useState<Integrations | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState<HomeFilter>("all");
  const [allCols, setAllCols] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [active, setActive] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<{ row: HistoryRow; column: string } | null>(null);
  const [evidence, setEvidence] = useState<{ row: HistoryRow; column: string } | null>(null);

  useEffect(() => {
    getShippers()
      .then((list) => {
        setShippers(list);
        const saved = window.localStorage.getItem(SHIPPER_KEY);
        const pick = list.find((s) => s.shipper_id === saved)?.shipper_id ?? list[0]?.shipper_id ?? "";
        setShipperId(pick);
      })
      .catch(setError);
    getColumns().then(setCols).catch(setError);
    integrations().then(setInfo).catch(() => setInfo(null));
  }, []);

  const load = useCallback(async () => {
    if (!shipperId) return;
    setError(null);
    try {
      const [r, b, d] = await Promise.all([getHistory(shipperId), getBadges(shipperId), getDeclarations(shipperId)]);
      setRows(r);
      setBadges(b);
      setDecls(d);
    } catch (e) {
      setError(e); // 이미 보이던 데이터는 남긴다(DESIGN 3-5)
    }
  }, [shipperId]);

  useEffect(() => {
    setRows(null);
    setSelected(new Set());
    setActive(null);
    load();
    if (shipperId) rememberShipper(shipperId);
  }, [shipperId, load]);

  const shipperName = shippers.find((s) => s.shipper_id === shipperId)?.display_name ?? shipperId;

  const columns = useMemo(() => {
    if (!cols) return [];
    let list = allCols ? [...cols.columns] : [...cols.default_view];
    if (allCols && !showHidden) list = list.filter((c) => !cols.hidden.includes(c));
    // B사 등 색상을 쓰는 화주: 재질 다음에 색상 열(DESIGN 3-2)
    const hasColor = rows?.some((r) => r.cells[cols.color_column]);
    if (hasColor) {
      const i = list.findIndex((c) => c.startsWith("재질 ("));
      list.splice(i + 1, 0, cols.color_column);
    }
    return list;
  }, [cols, allCols, showHidden, rows]);

  const visible = useMemo(() => {
    if (!rows) return [];
    if (filter === "attention") {
      return rows.filter(
        (r) => r.status !== "승인" && Object.values(r.cells).some((c) => (r.confirmed ? c.flag === "need_input" : ["mismatch", "need_check", "need_input"].includes(c.flag))),
      );
    }
    if (filter === "ready") return rows.filter((r) => r.status === "신청 전");
    if (filter === "progress") {
      const ids = new Set(decls.flatMap((d) => d.row_ids));
      return rows.filter((r) => ids.has(r.row_id));
    }
    return rows;
  }, [rows, filter, decls]);

  const selectedIds = useMemo(() => (rows ?? []).filter((r) => selected.has(r.row_id)).map((r) => r.row_id), [rows, selected]);

  const onRefresh = async () => {
    setRefreshing(true);
    setMessage("");
    try {
      const out = await refreshHistory(shipperId);
      setMessage(HOME.refreshDone(out.rows, out.bls));
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setRefreshing(false);
    }
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
      {/* 메인 화면 = 표 중심(제안서 가이드라인 ④): 얇은 도구 줄 + 화면 높이를 채우는 표. 큰 제목·숫자 카드 없음 */}
      <TopBar
        shipperId={shipperId}
        shipperName={shipperName}
        badges={badges}
        filter={filter}
        onFilter={setFilter}
        onUpload={() => setUploadOpen(true)}
        onRefresh={onRefresh}
        refreshing={refreshing}
        itemSheet={
          <ItemSheetButton
            shipperId={shipperId}
            selectedRowIds={selectedIds}
            onCreated={() => setMessage("")}
          />
        }
      />

      {info && !info.llm.ok && <Notice>{T.integrations.llmOff}</Notice>}
      {info && info.unipass.mode !== "live" && <Notice>{T.integrations.unipassMock}</Notice>}
      {message && <Notice>{message}</Notice>}
      {uploading && <Notice>판독 중… (끝나면 표에 행이 나타납니다)</Notice>}
      {error !== null && <ErrorLine error={error} onRetry={load} />}

      <div style={{ display: "flex", alignItems: "center", gap: space.md, fontSize: font.sm, margin: `${space.xs}px 0` }}>
        <label>
          <input type="checkbox" checked={allCols} onChange={(e) => setAllCols(e.target.checked)} /> {HOME.allColumns}
        </label>
        {allCols && (
          <label>
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
          title={HOME.legend}
        >
          {HOME.legend}
        </span>
      </div>

      {!shipperId && <EmptyState text={T.pickShipper} />}
      {shipperId && rows === null && error === null && <Skeleton lines={8} />}
      {rows && rows.length === 0 && (
        <EmptyState
          text={HOME.emptyRows}
          action={
            <Button variant="primary" onClick={() => setUploadOpen(true)}>
              {HOME.buttons.upload}
            </Button>
          }
        />
      )}
      {rows && rows.length > 0 && (
        <HistoryTable
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
          <ReviewPanel rowId={active} onConfirmed={() => load()} onClose={() => setActive(null)} />
        </aside>
      )}

      {uploadOpen && (
        <UploadDialog
          shipperId={shipperId}
          shipperName={shipperName}
          onClose={() => setUploadOpen(false)}
          onStart={() => setUploading(true)}
          onEnd={() => setUploading(false)}
          onUploaded={async (ids) => {
            await load();
            if (ids[0]) setActive(ids[0]);
          }}
        />
      )}
      {editing && (
        <CellEditor row={editing.row} column={editing.column} onClose={() => setEditing(null)} onSaved={load} />
      )}
      {evidence && (
        <JudgeEvidence row={evidence.row} column={evidence.column} onClose={() => setEvidence(null)} onChanged={load} />
      )}
    </div>
  );
}
