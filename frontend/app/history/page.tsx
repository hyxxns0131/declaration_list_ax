"use client";
// 탭 3. 검역 리스트 › ③ 완성된 검역 리스트 (메인 화면, DESIGN 3장). 공통 머리(화주·배지·서류 올리기·새로고침)
// + 단계 표시줄 + 화면 높이를 채우는 표 + 오른쪽 검수 서랍. 품목사항은 탭 5에서 만든다. 배치와 상태 연결만. 담당: KHS
// 검역 리스트 탭 0단계(HS 요청 11/26): 머리·단계 표시줄을 ListHeader로 바꿈.
// 4단계: 표를 ListTable(칸 묶음·고정 칸·출처 표시·검수 필요 → ②)로 바꾸고 [등록 정보 채우기](POST /history/fill)를 둠.
import { useCallback, useEffect, useMemo, useState } from "react";

import { JudgeEvidence } from "@/components/judge/JudgeEvidence";
import { UploadDialog } from "@/components/reader/UploadDialog";
import { ListHeader, type BadgeFilter } from "@/components/review/ListHeader";
import { ListTable, originOf } from "@/components/review/ListTable";
import { pillPrimary, pillSecondary } from "@/components/review/listUi";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { notifyListChanged } from "@/components/review/useListSteps";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { integrations } from "@/lib/api/core";
import { createManualRow, deleteRow, fillFromRegistry, fillIfChanged, getColumns, getHistory, moveRow, patchCell, restoreRow } from "@/lib/api/history";
import { getDeclarations } from "@/lib/api/judge";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { Integrations } from "@/lib/types/core";
import type { CellValue, Columns, Declaration, HistoryRow } from "@/lib/types/history";

/** 표 높이: 화면 높이에서 위 탭 줄·머리·단계 표시줄을 뺀 나머지 */
const TABLE_HEIGHT = "calc(100vh - 300px)";

type LocalFilter = "need_input_cells" | "registry_cells" | null;

const ADD_FIELDS = ["한글 제품명(모델넘버)", "영문 제품명", "제조사", "입수", "카톤 수", "순중량", "가격(수출국)", "CI 통화", "재질 (재질 코드명으로 작성, 가나다 순으로 기재)"];

function localMatch(r: HistoryRow, f: LocalFilter): boolean {
  if (f === "need_input_cells") return Object.entries(r.cells).some(([c, x]) => ["needInput", "blocked"].includes(originOf(x, c)));
  if (f === "registry_cells") return Object.entries(r.cells).some(([c, x]) => originOf(x, c) === "registry");
  return true;
}

function AddRowForm({ shipperId, bls, onDone, onClose }: { shipperId: string; bls: string[]; onDone: (msg: string) => void; onClose: () => void }) {
  const [bl, setBl] = useState(bls[0] ?? "");
  const [vals, setVals] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const L = HOME.listTable;
  const submit = async () => {
    setBusy(true);
    setErr("");
    try {
      const values: Record<string, CellValue> = {};
      for (const [k, v] of Object.entries(vals)) {
        if (v.trim() === "") continue;
        values[k] = ["입수", "카톤 수", "순중량", "가격(수출국)"].includes(k) && !Number.isNaN(Number(v)) ? Number(v) : v.trim();
      }
      await createManualRow(shipperId, bl, values);
      onDone(L.saved);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div role="dialog" aria-label={L.addRowTitle} style={{ background: colors.cardBg, borderRadius: 16, padding: space.md, margin: `${space.sm}px 0` }}>
      <div style={{ fontWeight: 800 }}>{L.addRowTitle}</div>
      <div style={{ fontSize: font.sm, color: colors.muted, margin: `2px 0 ${space.sm}px` }}>{L.addRowHelp}</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: space.sm }}>
        <label style={{ fontSize: font.sm }}>
          {L.addRowBl}
          <input list="add-row-bls" value={bl} onChange={(e) => setBl(e.target.value)} style={{ display: "block", width: "100%", height: 38, borderRadius: 8, border: `1px solid ${colors.border}`, padding: "0 8px" }} />
          <datalist id="add-row-bls">
            {bls.map((b) => (
              <option key={b} value={b} />
            ))}
          </datalist>
        </label>
        {ADD_FIELDS.map((f) => (
          <label key={f} style={{ fontSize: font.sm }}>
            {f.split(" (")[0]}
            <input
              value={vals[f] ?? ""}
              onChange={(e) => setVals({ ...vals, [f]: e.target.value })}
              placeholder={f === "한글 제품명(모델넘버)" ? "예: 전기밥솥(RC-100)" : ""}
              style={{ display: "block", width: "100%", height: 38, borderRadius: 8, border: `1px solid ${colors.border}`, padding: "0 8px" }}
            />
          </label>
        ))}
      </div>
      {err && <div style={{ color: colors.mismatch, fontSize: font.sm, marginTop: space.xs }}>{err}</div>}
      <div style={{ display: "flex", gap: space.sm, marginTop: space.sm }}>
        <button type="button" style={{ ...pillPrimary, height: 40 }} disabled={busy} onClick={submit}>
          {L.addRowSave}
        </button>
        <button type="button" style={{ ...pillSecondary, height: 40 }} onClick={onClose}>
          {L.addRowCancel}
        </button>
      </div>
    </div>
  );
}

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
  const [local, setLocal] = useState<LocalFilter>(null);
  const [howTo, setHowTo] = useState(false);
  const [adding, setAdding] = useState(false);
  const [undo, setUndo] = useState<HistoryRow | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [active, setActive] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [evidence, setEvidence] = useState<{ row: HistoryRow; column: string } | null>(null);

  useEffect(() => {
    integrations().then(setInfo).catch(() => setInfo(null));
  }, []);

  const load = useCallback(async () => {
    if (!shipperId) return;
    setError(null);
    try {
      // 2번 탭 등록 정보가 바뀌었으면 먼저 자동으로 다시 채운다(실패해도 표는 보인다)
      const auto = await fillIfChanged(shipperId).catch(() => null);
      if (auto?.changed) setMessage(HOME.listTable.autoFilled(auto.judged ?? 0));
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

  const visible = useMemo(() => (rows ?? []).filter((r) => matches(r, filter) && localMatch(r, local)), [rows, filter, local]);
  // 지금 할 일 요약: 입력 필요 칸·서류끼리 다른 칸(승인 행 제외)
  const todoCounts = useMemo(() => {
    let need = 0;
    let blocked = 0;
    for (const r of rows ?? []) {
      if (r.status === "승인") continue;
      for (const [c, x] of Object.entries(r.cells)) {
        const o = originOf(x, c);
        if (o === "needInput") need += 1;
        if (o === "blocked") blocked += 1;
      }
    }
    return { need, blocked };
  }, [rows]);
  const bls = useMemo(
    () => [...new Set((rows ?? []).map((r) => String(r.cells["B/L Number"]?.final_value ?? r.cells["B/L Number"]?.ai_value ?? "")).filter(Boolean))],
    [rows],
  );
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
        <button type="button" style={{ ...pillSecondary, height: 34, marginLeft: "auto" }} aria-expanded={howTo} onClick={() => setHowTo(!howTo)}>
          {HOME.listTable.howTo} {howTo ? "▾" : "▸"}
        </button>
        <button type="button" style={{ ...pillSecondary, height: 34 }} onClick={() => setAdding(true)} disabled={!shipperId}>
          {HOME.listTable.addRow}
        </button>
        <button type="button" style={{ ...pillSecondary, height: 34 }} disabled={!shipperId || filling} onClick={fill}>
          {filling ? HOME.listTable.filling : HOME.listTable.fill}
        </button>
      </div>

      {howTo && (
        <ul style={{ background: colors.cardBg, borderRadius: 12, margin: `${space.xs}px 0`, padding: `${space.sm}px ${space.lg}px`, fontSize: font.sm, lineHeight: 1.7 }}>
          {HOME.listTable.howToItems.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}
      {rows && rows.length > 0 && (
        <div
          role="status"
          style={{
            display: "flex",
            alignItems: "center",
            gap: space.sm,
            flexWrap: "wrap",
            padding: `${space.sm}px ${space.md}px`,
            borderRadius: 12,
            margin: `${space.xs}px 0`,
            background: todoCounts.need + todoCounts.blocked ? colors.needInput : colors.okSoft,
            fontWeight: 700,
            fontSize: font.md,
          }}
        >
          <span>{HOME.listTable.todo(todoCounts.need, todoCounts.blocked)}</span>
          <span style={{ marginLeft: "auto", display: "flex", gap: space.xs }}>
            {(
              [
                ["need_input_cells", HOME.listTable.onlyNeedInput],
                ["registry_cells", HOME.listTable.onlyRegistry],
              ] as [LocalFilter, string][]
            ).map(([k, label]) => (
              <button
                key={String(k)}
                type="button"
                aria-pressed={local === k}
                onClick={() => setLocal(local === k ? null : k)}
                style={{ ...pillSecondary, height: 32, fontSize: font.sm, background: local === k ? colors.primarySoft : "#fff" }}
              >
                {local === k ? `✓ ${label}` : label}
              </button>
            ))}
          </span>
        </div>
      )}
      {undo && (
        <Notice>
          {HOME.listTable.deleted}{" "}
          <button
            type="button"
            style={{ border: "none", background: "none", color: colors.primary, cursor: "pointer", fontWeight: 700 }}
            onClick={async () => {
              try {
                await restoreRow(undo);
                setUndo(null);
                setMessage(HOME.listTable.restored);
                await reload();
              } catch (e) {
                setError(e);
              }
            }}
          >
            {HOME.listTable.undo}
          </button>
        </Notice>
      )}
      {adding && (
        <AddRowForm
          shipperId={shipperId}
          bls={bls}
          onClose={() => setAdding(false)}
          onDone={async (msg) => {
            setAdding(false);
            setMessage(msg);
            await reload();
          }}
        />
      )}

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
          onSave={async (row, column, value) => {
            await patchCell(row.row_id, { column, value });
            await reload();
          }}
          onDeleteRow={async (row) => {
            try {
              const out = await deleteRow(row.row_id);
              setUndo(out.row);
              await reload();
            } catch (e) {
              setError(e);
            }
          }}
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
            width: "min(920px, 94vw)",
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
          <ReviewPanel key={active} rowId={active} onConfirmed={() => reload()} onClose={() => setActive(null)} />
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
      {evidence && (
        <JudgeEvidence row={evidence.row} column={evidence.column} onClose={() => setEvidence(null)} onChanged={reload} />
      )}
    </div>
  );
}
