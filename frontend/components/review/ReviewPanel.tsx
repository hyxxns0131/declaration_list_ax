"use client";
// 서류 검수 패널 (DESIGN 4장, 검역 리스트 탭 3단계). props: rowId → onConfirmed(rowId).
// 표: 항목 × [인보이스 | 패킹리스트 | B/L | 완성된 리스트 값 | 고르기]. 서류끼리 다른 칸은 빨강 + '불일치'.
// 항목마다 AI 분석 한 줄(무엇이 다른지·오타로 보이는 서류·추천 값·확신). 추천 값은 미리 고르지 않고 '추천' 표시만.
// [이 값 사용](라디오) · [직접 입력] · 이유 메모 → [저장] = PATCH /history/{row_id}/resolve(final_value, 근거 MANUAL).
// 담당: KHS
import { useCallback, useEffect, useState } from "react";

import { LIST_BLUE, STATE_STYLE, pillDisabled, pillPrimary } from "@/components/review/listUi";
import { notifyListChanged } from "@/components/review/useListSteps";
import { Button } from "@/components/ui/Button";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { confirmRow, getReview, resolveRow } from "@/lib/api/history";
import { openDocument } from "@/lib/api/reader";
import { fmtCell, fmtNumber } from "@/lib/format";
import { DOC_LABELS } from "@/lib/text/reader";
import { REVIEW } from "@/lib/text/review";
import type { CellValue, DocKey, PickKey, ResolveChoice, Review, ReviewItem } from "@/lib/types/history";

const DOCS: DocKey[] = ["CI", "PL", "BL"];
/** 모선 항목에 유니패스 값이 있으면 유니패스 칸을 서류 옆에 하나 더 둔다(HS 결정 11/26) */
const WITH_UNIPASS: PickKey[] = [...DOCS, "UNIPASS"];
type Pick = { source: PickKey | "manual"; value: string; memo: string };

function show(v: CellValue): string {
  if (v === null || v === undefined || v === "") return "";
  return typeof v === "number" ? fmtNumber(v, 3) : String(v);
}

function outlier(it: ReviewItem, doc: PickKey, cols: PickKey[]): boolean {
  if (!it.different) return false;
  const vals = cols.map((d) => it[d] ?? null).filter((v) => v !== null && v !== "");
  const mine = it[doc] ?? null;
  if (mine === null || mine === "") return false;
  const same = vals.filter((v) => String(v) === String(mine)).length;
  return same <= vals.length / 2; // 다수와 다른 값만 빨강(둘뿐이면 둘 다)
}

const numCell = { textAlign: "right" as const, fontVariantNumeric: "tabular-nums" as const };

export function ReviewPanel({
  rowId,
  onConfirmed,
  onClose,
}: {
  rowId: string;
  onConfirmed: (rowId: string) => void;
  onClose: () => void;
}) {
  const [data, setData] = useState<Review | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [picks, setPicks] = useState<Record<string, Pick>>({});
  const [note, setNote] = useState("");

  const load = useCallback(() => {
    setError(null);
    getReview(rowId).then(setData).catch(setError);
  }, [rowId]);

  useEffect(() => {
    setData(null);
    setPicks({});
    setNote("");
    load();
  }, [load]);

  const toggle = async () => {
    if (!data) return;
    setBusy(true);
    try {
      await confirmRow(rowId, !data.confirmed);
      load();
      notifyListChanged();
      onConfirmed(rowId);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const cols: PickKey[] = data?.items.some((i) => i.UNIPASS !== undefined && i.UNIPASS !== null) ? WITH_UNIPASS : DOCS;

  const setPick = (item: string, p: Partial<Pick>) =>
    setPicks((cur) => {
      const base: Pick = cur[item] ?? { source: "manual", value: "", memo: "" };
      return { ...cur, [item]: { ...base, ...p } };
    });

  const save = async () => {
    const choices: ResolveChoice[] = Object.entries(picks)
      .filter(([, p]) => p.source !== "manual" || p.value.trim() !== "")
      .map(([item, p]) => ({ item, source: p.source, value: p.source === "manual" ? p.value : undefined, memo: p.memo }));
    if (!choices.length) {
      setNote(REVIEW.pickFirst);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resolveRow(rowId, choices);
      setNote(REVIEW.saved(choices.length));
      setPicks({});
      load();
      notifyListChanged();
      onConfirmed(rowId);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const row = data?.row;
  const bl = row ? String(row.cells["B/L Number"]?.final_value ?? row.cells["B/L Number"]?.ai_value ?? "") : "";
  const nameCell = row?.cells["한글 제품명(모델넘버)"];
  const name = nameCell ? String(nameCell.final_value ?? nameCell.ai_value ?? row?.model ?? "") : row?.model ?? "";
  const open = data?.items.filter((it) => it.different) ?? [];

  return (
    <section aria-label="서류 검수" style={{ marginTop: space.sm }}>
      <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
        <strong style={{ fontSize: font.lg }}>{REVIEW.title(bl, name)}</strong>
        {data && (
          <span style={{ borderRadius: 999, padding: "2px 10px", fontSize: font.sm, fontWeight: 700, background: STATE_STYLE.mismatch.bg, color: STATE_STYLE.mismatch.color }}>
            {REVIEW.mismatch(data.items.filter((i) => i.status === "불일치" || (!i.status && i.different)).length)}
          </span>
        )}
        {data && (
          <span style={{ borderRadius: 999, padding: "2px 10px", fontSize: font.sm, fontWeight: 700, background: STATE_STYLE.manual.bg, color: STATE_STYLE.manual.color }}>
            {REVIEW.edited(data.edited_count)}
          </span>
        )}
        <span style={{ marginLeft: "auto", display: "flex", gap: space.xs, flexWrap: "wrap" }}>
          {data?.documents.map((d) => (
            <Button key={d.doc_id} small onClick={() => openDocument(d.doc_id).catch(setError)}>
              {REVIEW.openDoc}: {DOC_LABELS[d.doc_type] ?? d.doc_type}
            </Button>
          ))}
          <Button small variant={data?.confirmed ? "default" : "primary"} disabled={!data || busy} onClick={toggle}>
            {data?.confirmed ? REVIEW.unconfirm : REVIEW.confirm}
          </Button>
          <Button small onClick={onClose} aria-label="닫기">
            ×
          </Button>
        </span>
      </div>

      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {!data && error === null && <Skeleton lines={4} />}
      {data?.confirmed && <Notice>{REVIEW.confirmedNote}</Notice>}
      {note && <Notice>{note}</Notice>}

      {data && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ marginTop: space.sm, width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                <th>{REVIEW.cols.item}</th>
                {cols.map((d) => (
                  <th key={d}>{REVIEW.cols[d]}</th>
                ))}
                <th>{REVIEW.cols.sheet}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => {
                const p = picks[it.item];
                const st = it.status ?? (it.different ? "불일치" : "일치");
                const can = it.different && !data.row.status.includes("승인");
                const listCell = it.cell ? data.row.cells[it.cell] : undefined;
                const human = listCell?.final_value !== null && listCell?.final_value !== undefined;
                return (
                  <tr key={it.item} style={{ verticalAlign: "top" }}>
                    <td style={{ minWidth: 130 }}>
                      <div style={{ fontWeight: 600 }}>{it.item}</div>
                      {it.different && (
                        <span style={{ fontSize: 12, fontWeight: 700, color: st === "해결됨" ? STATE_STYLE.manual.color : colors.mismatch }}>
                          {st === "해결됨" ? "✎ 해결됨" : "■ 불일치"}
                        </span>
                      )}
                      {st === "비어 있음" && (
                        <span style={{ fontSize: 12, fontWeight: 700, color: colors.muted }} title={REVIEW.emptyTip}>
                          □ {REVIEW.emptyValue}
                        </span>
                      )}
                      {it.different && it.ai && (
                        <div style={{ fontSize: 12, color: colors.needCheck, marginTop: 2 }} title={it.ai.reason}>
                          <span aria-label="AI 분석" style={{ fontWeight: 800 }}>AI </span>
                          {REVIEW.aiLine(it.ai.what, it.ai.typo_doc, it.ai.suggested, it.ai.confidence)}
                        </div>
                      )}
                      {it.different && it.ai === null && <div style={{ fontSize: 12, color: colors.muted }}>{REVIEW.aiOff}</div>}
                    </td>
                    {cols.map((d) => {
                      const v = it[d] ?? null;
                      const has = v !== null && v !== undefined && v !== "";
                      const red = outlier(it, d, cols);
                      const suggested = Boolean(it.ai?.suggested) && show(v) !== "" && String(it.ai?.suggested) === String(v);
                      return (
                        <td key={d} style={{ ...numCell, textAlign: typeof v === "number" ? "right" : "left" }}>
                          {has ? (
                            <span style={red ? { color: colors.mismatch, fontWeight: 700 } : undefined}>
                              {red ? "■ " : ""}
                              {show(v)}
                            </span>
                          ) : (
                            <span style={{ color: colors.approved }}>—</span>
                          )}
                          {suggested && (
                            <span style={{ marginLeft: 4, fontSize: 11, fontWeight: 800, color: LIST_BLUE }}>{REVIEW.suggest}</span>
                          )}
                          {can && has && (
                            <label style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 4, fontSize: 12, cursor: "pointer", justifyContent: "flex-start" }}>
                              <input
                                type="radio"
                                name={`pick-${rowId}-${it.item}`}
                                checked={p?.source === d}
                                onChange={() => setPick(it.item, { source: d })}
                              />
                              {REVIEW.useThis}
                            </label>
                          )}
                        </td>
                      );
                    })}
                    <td style={{ minWidth: 160 }}>
                      {it.cell ? (
                        human ? (
                          <span style={{ color: STATE_STYLE.manual.color, fontWeight: 700 }} title={listCell?.memo || REVIEW.editedCell}>
                            ✎ {fmtCell(it.cell, listCell?.final_value ?? null)}
                          </span>
                        ) : listCell?.flag === "mismatch" ? (
                          <span style={{ color: colors.mismatch, fontWeight: 700 }}>{REVIEW.blocked}</span>
                        ) : (
                          <span>{fmtCell(it.cell, listCell?.ai_value ?? null) || "—"}</span>
                        )
                      ) : (
                        <span style={{ color: colors.muted }}>
                          {it.chosen ? `✎ ${show(it.chosen.value)}` : st === "비어 있음" ? REVIEW.emptyValue : "—"}
                        </span>
                      )}
                      {can && (
                        <div style={{ display: "grid", gap: 4, marginTop: 4 }}>
                          <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
                            <input
                              type="radio"
                              name={`pick-${rowId}-${it.item}`}
                              checked={p?.source === "manual"}
                              onChange={() => setPick(it.item, { source: "manual" })}
                            />
                            {REVIEW.manual}
                          </label>
                          {p?.source === "manual" && (
                            <input
                              aria-label={`${it.item} ${REVIEW.manual}`}
                              value={p.value}
                              onChange={(e) => setPick(it.item, { value: e.target.value })}
                              style={{ padding: "4px 8px", fontSize: 13 }}
                            />
                          )}
                          {p && (
                            <input
                              aria-label={`${it.item} ${REVIEW.memo}`}
                              placeholder={REVIEW.memo}
                              value={p.memo}
                              onChange={(e) => setPick(it.item, { memo: e.target.value })}
                              style={{ padding: "4px 8px", fontSize: 12 }}
                            />
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {data && open.length > 0 && (
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: space.sm }}>
          <button type="button" onClick={save} disabled={busy} style={{ ...pillPrimary, ...(busy ? pillDisabled : {}) }}>
            {busy ? REVIEW.saving : REVIEW.save}
          </button>
        </div>
      )}

      {data && data.warnings.length > 0 && (
        <div style={{ marginTop: space.sm, fontSize: font.sm }}>
          <strong>{REVIEW.warnings}</strong>
          <ul style={{ margin: `${space.xs}px 0`, paddingLeft: space.lg }}>
            {data.warnings.map((w) => (
              <li key={w.column}>
                {w.column}: {w.memo || (w.value === null ? "" : String(w.value))}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
