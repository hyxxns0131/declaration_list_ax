"use client";
// 화면 ① 선적 건 카드 (검역 리스트 탭 1단계, HS 요청 11/27 "보기 편하게, 초보자도 쉽게"). 담당: KHS
// - 서류 칩은 약어 + 쉬운 이름 + 상태 글자('?' 쓰지 않음, 색만으로 구분하지 않음)
// - 카드마다 '할 일' 한 줄과 버튼 하나(B/L 번호 입력 · 이 건에 서류 더 올리기 · 대조 결과 보기 · 완성된 리스트 보기)
// - 펼치면 서류별 읽은 값, [이 건 삭제]는 화면 안에서 한 번 더 확인(백업 후 삭제)
// 데이터는 GET /reader/shipments. 버튼 동작은 부모(upload page)가 넘긴 콜백·API만 부른다.
import { useState } from "react";

import { LIST_BLUE, pillPrimary, pillSecondary } from "@/components/review/listUi";
import { colors, font, space } from "@/components/ui/tokens";
import { deleteShipment, openDocument, rereadShipment, setShipmentBl } from "@/lib/api/reader";
import { fmtNumber } from "@/lib/format";
import { CARDS, DOC_LABELS } from "@/lib/text/reader";
import type { DocState, Shipment, ShipmentDoc } from "@/lib/types/reader";

const MAIN = ["CI", "PL", "BL"] as const;
const FIELDS: { key: keyof ShipmentDoc["values"]; label: string; num?: boolean }[] = [
  { key: "bl_no", label: "B/L 번호" },
  { key: "invoice_no", label: "인보이스 번호" },
  { key: "doc_date", label: "서류 날짜" },
  { key: "vessel", label: "모선" },
  { key: "manufacturer_name", label: "제조사" },
  { key: "currency", label: "통화" },
  { key: "total_amount", label: "총 금액", num: true },
  { key: "total_cartons", label: "총 카톤", num: true },
  { key: "total_gross_kg", label: "총중량(kg)", num: true },
];
/** 상태 → 색(글자와 함께 쓴다) */
const TONE: Record<DocState, { fg: string; bg: string; border: string }> = {
  ok: { fg: colors.ok, bg: colors.okSoft, border: colors.okSoft },
  check: { fg: colors.needCheck, bg: colors.needCheckSoft, border: colors.needCheckSoft },
  missing: { fg: colors.needInputText, bg: colors.needInput, border: colors.needInput },
  unreadable: { fg: colors.mismatch, bg: colors.mismatchSoft, border: colors.mismatch },
  unknown: { fg: colors.mismatch, bg: colors.mismatchSoft, border: colors.mismatch },
};
const num = { textAlign: "right" as const, fontVariantNumeric: "tabular-nums" as const };
const METRICS = ["pcs", "cartons", "net_kg", "amount"] as const;
type Metric = (typeof METRICS)[number];
type Line = ShipmentDoc["lines"][number];

function pcs(ln: Line): number | null {
  if (ln.quantity !== null && ln.quantity !== undefined) return ln.quantity;
  if (ln.qty_per_carton !== null && ln.cartons !== null) return ln.qty_per_carton * ln.cartons;
  return null;
}

/** 서류별 품목(모델) 표: 행 = 모델, 열 = 서류 × (수량·카톤·순중량·금액). 다르면 글자로 '다름'. */
function ItemsTable({ s, docs, onRow }: { s: Shipment; docs: string[]; onRow: (rowId: string) => void }) {
  type Cell = Partial<Record<Metric, number>>;
  const keys: string[] = [];
  const by: Record<string, Record<string, Cell>> = {};
  const unnamed: { doc: string; desc: string }[] = [];
  for (const t of docs) {
    for (const ln of s.documents[t]?.lines ?? []) {
      if (!ln.model.trim()) {
        unnamed.push({ doc: t, desc: ln.description });
        continue;
      }
      const k = `${ln.model.trim().toUpperCase()}|${ln.is_part ? 1 : 0}`;
      if (!by[k]) {
        by[k] = {};
        keys.push(k);
      }
      const cur: Cell = (by[k][t] ??= {});
      const add = (m: Metric, v: number | null | undefined) => {
        if (v === null || v === undefined) return;
        cur[m] = (cur[m] ?? 0) + v;
      };
      add("pcs", pcs(ln));
      add("cartons", ln.cartons);
      add("net_kg", ln.net_kg);
      add("amount", ln.amount);
    }
  }
  const currency = s.documents.CI?.values.currency ?? "";
  if (!keys.length && !unnamed.length) return <div style={{ fontSize: font.sm, color: colors.muted }}>{CARDS.noItems}</div>;
  const differs = (k: string, m: Metric) => {
    const vals = docs.map((t) => by[k][t]?.[m]).filter((v): v is number => v !== undefined);
    return vals.length > 1 && Math.max(...vals) - Math.min(...vals) > 0.005;
  };
  const th = { textAlign: "left" as const, fontSize: 12, color: colors.muted, padding: "4px 6px", whiteSpace: "nowrap" as const };
  const td = { padding: "4px 6px", borderTop: `1px solid ${colors.border}`, fontSize: 13 };
  const sep = `2px solid ${colors.border}`;
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", minWidth: "100%" }}>
        <thead>
          <tr>
            <th style={th} rowSpan={2}>
              {CARDS.model}
            </th>
            {docs.map((t) => (
              <th key={t} style={{ ...th, textAlign: "center", borderLeft: sep }} colSpan={METRICS.length}>
                {DOC_LABELS[t] ?? t}
              </th>
            ))}
            <th style={th} rowSpan={2} />
          </tr>
          <tr>
            {docs.map((t) =>
              METRICS.map((m, i) => (
                <th key={`${t}-${m}`} style={{ ...th, borderLeft: i === 0 ? sep : undefined }}>
                  {m === "amount" && currency ? `${CARDS.metrics[m]}(${currency})` : CARDS.metrics[m]}
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => {
            const [model, part] = k.split("|");
            const rowId = s.row_ids[k];
            return (
              <tr key={k}>
                <td style={{ ...td, fontWeight: 700, whiteSpace: "nowrap" }}>
                  {model}
                  {part === "1" && <span style={{ marginLeft: 6, fontSize: 11, color: colors.muted }}>({CARDS.part})</span>}
                </td>
                {docs.map((t) => {
                  const c = by[k][t];
                  if (!s.documents[t])
                    return (
                      <td key={t} colSpan={METRICS.length} style={{ ...td, color: colors.muted, borderLeft: sep }}>
                        {CARDS.noDoc}
                      </td>
                    );
                  if (!c)
                    return (
                      <td key={t} colSpan={METRICS.length} style={{ ...td, color: colors.mismatch, fontWeight: 700, borderLeft: sep }}>
                        ■ {CARDS.notInDoc}
                      </td>
                    );
                  return METRICS.map((m, i) => {
                    const v = c[m];
                    const diff = differs(k, m);
                    return (
                      <td
                        key={`${t}-${m}`}
                        style={{
                          ...td,
                          ...num,
                          borderLeft: i === 0 ? sep : undefined,
                          color: diff ? colors.mismatch : undefined,
                          fontWeight: diff ? 700 : undefined,
                        }}
                      >
                        {v === undefined ? <span style={{ color: colors.muted }}>—</span> : fmtNumber(v, 3)}
                        {diff && <span style={{ fontSize: 11, marginLeft: 3 }}>({CARDS.differs})</span>}
                      </td>
                    );
                  });
                })}
                <td style={td}>
                  {rowId && (
                    <button
                      type="button"
                      onClick={() => onRow(rowId)}
                      style={{ border: "none", background: "none", color: LIST_BLUE, cursor: "pointer", fontSize: 12, whiteSpace: "nowrap" }}
                    >
                      {CARDS.openRow} →
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
          {unnamed.map((u, i) => (
            <tr key={`u-${i}`}>
              <td colSpan={2 + docs.length * METRICS.length} style={{ ...td, color: colors.needCheck }}>
                {DOC_LABELS[u.doc] ?? u.doc}: {CARDS.noModel(u.desc)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Chip({ type, state }: { type: string; state: DocState }) {
  const t = TONE[state];
  return (
    <span
      title={CARDS.stateHelp[state]}
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        gap: 6,
        borderRadius: 999,
        padding: `3px ${space.sm + 2}px`,
        fontSize: font.sm,
        background: t.bg,
        color: t.fg,
        border: `1px solid ${t.border}`,
        whiteSpace: "nowrap",
      }}
    >
      <b>{CARDS.short[type] ?? type}</b>
      <span style={{ opacity: 0.85 }}>{DOC_LABELS[type] ?? type}</span>
      <span style={{ fontWeight: 700 }}>{CARDS.state[state]}</span>
    </span>
  );
}

function Card({
  s,
  shipperId,
  onChanged,
  onAddMore,
  onGo,
}: {
  s: Shipment;
  shipperId: string;
  onChanged: (note: string) => void;
  onAddMore: (folderId: string) => void;
  onGo: (where: "review" | "list", rowId?: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [bl, setBl] = useState("");
  const [busy, setBusy] = useState<"" | "bl" | "reread" | "del">("");
  const [askDel, setAskDel] = useState(false);
  const [err, setErr] = useState("");
  const extra = Object.keys(s.documents).filter((t) => !MAIN.includes(t as (typeof MAIN)[number]));
  const problems = Object.entries(s.doc_states).filter(([, st]) => st !== "ok");
  const todo = s.next !== "done";

  const saveBl = async () => {
    setBusy("bl");
    setErr("");
    try {
      const out = await setShipmentBl(shipperId, s.folder_ids, bl);
      onChanged(CARDS.blSaved(out.bl_no));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };
  const del = async () => {
    setBusy("del");
    setErr("");
    try {
      const out = await deleteShipment(shipperId, s.folder_ids);
      onChanged(CARDS.delDone(out.deleted_documents, out.deleted_rows));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setAskDel(false);
    } finally {
      setBusy("");
    }
  };
  const reread = async () => {
    setBusy("reread");
    setErr("");
    try {
      const out = await rereadShipment(shipperId, s.folder_ids);
      onChanged(CARDS.rereadDone(out.documents, out.bl_no));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };
  const main = () => {
    if (s.next === "upload_missing" || s.next === "fix_docs") onAddMore(s.folder_ids[0]);
    else if (s.next === "review") onGo("review");
    else if (s.next === "done") onGo("list");
  };

  return (
    <section
      style={{
        background: "#fff",
        borderRadius: 16,
        padding: `${space.md - 2}px ${space.md}px`,
        border: `1px solid ${todo ? colors.border : colors.okSoft}`,
        borderLeft: `6px solid ${todo ? colors.needCheck : colors.ok}`,
      }}
    >
      {/* 머리: B/L 번호 · 서류 칩 */}
      <div style={{ display: "flex", alignItems: "center", gap: space.md, flexWrap: "wrap" }}>
        <span style={{ fontWeight: 800, fontSize: font.lg, minWidth: 150 }}>{s.bl_no || CARDS.noBl}</span>
        <span style={{ display: "flex", gap: space.xs + 2, flexWrap: "wrap" }}>
          {MAIN.map((t) => (
            <Chip key={t} type={t} state={s.doc_states[t] ?? "missing"} />
          ))}
          {extra.map((t) => (
            <Chip key={t} type={t} state={s.doc_states[t] ?? "ok"} />
          ))}
        </span>
        {s.row_count > 0 && (
          <span style={{ marginLeft: "auto", fontSize: font.sm, color: colors.muted }}>{CARDS.rows(s.row_count)}</span>
        )}
      </div>

      {/* 할 일 한 줄 */}
      <div style={{ marginTop: space.sm, fontWeight: 700, color: todo ? colors.text : colors.ok }}>
        {CARDS.nextLine[s.next]}
      </div>
      {!s.bl_no && <div style={{ fontSize: font.sm, color: colors.muted, marginTop: 2 }}>{CARDS.noBlHelp}</div>}
      {problems.length > 0 && (
        <ul style={{ margin: `${space.xs}px 0 0`, paddingLeft: 18, fontSize: font.sm, color: colors.muted }}>
          {problems.map(([t, st]) => (
            <li key={t}>
              <b>{DOC_LABELS[t] ?? t}</b>: {CARDS.stateHelp[st]}
            </li>
          ))}
        </ul>
      )}

      {/* 버튼: 할 일 하나 + 보조 */}
      <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap", marginTop: space.sm }}>
        {s.next === "enter_bl" ? (
          <>
            <input
              aria-label={CARDS.blPlaceholder}
              placeholder={CARDS.blPlaceholder}
              value={bl}
              onChange={(e) => setBl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && bl.trim()) void saveBl();
              }}
              style={{ height: 40, minWidth: 240, borderRadius: 10, border: `1px solid ${colors.border}`, padding: `0 ${space.sm + 2}px`, fontSize: font.md }}
            />
            <button type="button" style={{ ...pillPrimary, height: 40 }} disabled={busy !== "" || !bl.trim()} onClick={saveBl}>
              {busy === "bl" ? CARDS.savingBl : CARDS.saveBl}
            </button>
            <button type="button" style={{ ...pillSecondary, height: 40 }} onClick={() => onAddMore(s.folder_ids[0])}>
              {CARDS.addMore}
            </button>
          </>
        ) : (
          <button type="button" style={{ ...pillPrimary, height: 40 }} onClick={main}>
            {CARDS.next[s.next]}
          </button>
        )}
        {(s.next === "fix_docs" || s.next === "enter_bl" || problems.length > 0) && (
          <button type="button" style={{ ...pillSecondary, height: 40 }} title={CARDS.rereadHelp} disabled={busy !== ""} onClick={reread}>
            {busy === "reread" ? CARDS.rereading : CARDS.reread}
          </button>
        )}
        <button type="button" style={{ ...pillSecondary, height: 40 }} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? CARDS.hideDetails : CARDS.details}
        </button>
        {askDel ? (
          <span role="alertdialog" style={{ display: "inline-flex", alignItems: "center", gap: space.xs + 2, fontSize: font.sm, background: colors.mismatchSoft, borderRadius: 10, padding: `4px ${space.sm}px` }}>
            {CARDS.delAsk(s.row_count)}
            <button type="button" style={{ ...pillSecondary, height: 32, color: colors.mismatch }} disabled={busy !== ""} onClick={del}>
              {CARDS.delYes}
            </button>
            <button type="button" style={{ ...pillSecondary, height: 32 }} onClick={() => setAskDel(false)}>
              {CARDS.delNo}
            </button>
          </span>
        ) : (
          <button
            type="button"
            style={{ border: "none", background: "none", color: s.locked ? colors.muted : colors.mismatch, cursor: s.locked ? "not-allowed" : "pointer", fontSize: font.sm, marginLeft: "auto" }}
            disabled={s.locked}
            title={s.locked ? CARDS.locked : undefined}
            onClick={() => setAskDel(true)}
          >
            {CARDS.del}
          </button>
        )}
      </div>
      {err && <div style={{ color: colors.mismatch, fontSize: font.sm, marginTop: space.xs }}>{err}</div>}

      {/* 받은 파일 */}
      <div style={{ fontSize: 12, color: colors.muted, marginTop: space.sm }}>
        {CARDS.files}: {s.files.join(" · ")}
      </div>

      {open && (
        <div style={{ marginTop: space.sm }}>
          <div style={{ fontWeight: 700 }}>{CARDS.items}</div>
          <div style={{ fontSize: font.sm, color: colors.muted, margin: `2px 0 ${space.xs}px` }}>{CARDS.itemsHelp}</div>
          <ItemsTable s={s} docs={[...MAIN]} onRow={(rid) => onGo("review", rid)} />
          <div style={{ fontWeight: 700, marginTop: space.md }}>{CARDS.headValues}</div>
        </div>
      )}
      {open && (
        <div style={{ overflowX: "auto", marginTop: space.xs }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, background: colors.cardBg, borderRadius: 10 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>항목</th>
                {[...MAIN, ...extra].map((t) => (
                  <th key={t} style={{ textAlign: "left" }}>
                    {DOC_LABELS[t] ?? t}
                    {s.documents[t] && (
                      <button
                        type="button"
                        onClick={() => openDocument(s.documents[t].doc_id)}
                        style={{ marginLeft: 6, border: "none", background: "none", color: LIST_BLUE, cursor: "pointer", fontSize: 12 }}
                      >
                        원본
                      </button>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {FIELDS.map((f) => (
                <tr key={f.key}>
                  <td style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{f.label}</td>
                  {[...MAIN, ...extra].map((t) => {
                    const d = s.documents[t];
                    const v = d?.values[f.key];
                    const src = d?.sources[f.key];
                    const empty = !d || v === null || v === "" || v === undefined;
                    return (
                      <td key={t} style={f.num ? num : undefined} title={src ? `출처: ${src}` : undefined}>
                        {empty ? <span style={{ color: colors.muted }}>—</span> : f.num ? fmtNumber(v as number) : String(v)}
                        {src?.startsWith("llm") && <span style={{ marginLeft: 4, fontSize: 11, color: colors.needCheck }}>AI</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ShipmentCards({
  shipments,
  shipperId,
  onChanged,
  onAddMore,
  onGo,
}: {
  shipments: Shipment[];
  shipperId: string;
  onChanged: (note: string) => void;
  onAddMore: (folderId: string) => void;
  onGo: (where: "review" | "list", rowId?: string) => void;
}) {
  const todo = shipments.filter((s) => s.next !== "done");
  const done = shipments.filter((s) => s.next === "done");
  const section = (title: string, list: Shipment[]) =>
    list.length > 0 && (
      <>
        <h3 style={{ margin: `${space.md}px 0 ${space.xs}px`, fontSize: font.md, color: colors.muted }}>{title}</h3>
        <div style={{ display: "grid", gap: space.sm }}>
          {list.map((s) => (
            <Card key={s.folder_ids.join(",")} s={s} shipperId={shipperId} onChanged={onChanged} onAddMore={onAddMore} onGo={onGo} />
          ))}
        </div>
      </>
    );
  return (
    <div>
      {section(CARDS.groupTodo(todo.length), todo)}
      {section(CARDS.groupDone(done.length), done)}
    </div>
  );
}
