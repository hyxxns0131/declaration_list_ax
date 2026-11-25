"use client";
// 판단 근거 팝오버 (DESIGN 5장): 근거 목록 + 다른 후보(만료 실적은 취소선), 고르면 PATCH. 담당: LSY
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate, shown } from "@/lib/format";
import { patchCell } from "@/lib/api/history";
import { getJudge } from "@/lib/api/judge";
import { JUDGE } from "@/lib/text/judge";
import type { HistoryRow } from "@/lib/types/history";
import type { JudgeDetail } from "@/lib/types/judge";

export const JUDGE_COLUMNS = {
  material: "재질 (재질 코드명으로 작성, 가나다 순으로 기재)",
  maker: "제조사",
  record: "실적접수번호 (승인일)",
} as const;

type Kind = keyof typeof JUDGE_COLUMNS;

export function kindOf(column: string): Kind | null {
  const hit = (Object.keys(JUDGE_COLUMNS) as Kind[]).find((k) => JUDGE_COLUMNS[k] === column);
  return hit ?? null;
}

interface Option {
  value: string;
  label: string;
  note?: string;
  strike?: boolean;
  disabled?: boolean;
}

function options(kind: Kind, d: JudgeDetail, row: HistoryRow): Option[] {
  if (kind === "material") return (d.material?.candidates ?? []).map((v) => ({ value: v, label: v }));
  if (kind === "maker") {
    const name = String(shown(row.cells[JUDGE_COLUMNS.maker]) ?? "").replace(/\s*\([^)]*\)\s*$/, "");
    return (d.maker?.candidates ?? []).map((c) => ({
      value: `${name || c.name || ""} (${c.code})`.trim(),
      label: `${c.code}: ${c.address}`,
      note: typeof c.score === "number" ? JUDGE.evidence.score(c.score) : c.status,
    }));
  }
  return (d.record?.candidates ?? []).map((c) => ({
    value: c.value,
    label: `${c.value} · ${c.materials.join(", ")}`,
    note: c.expired
      ? `${JUDGE.evidence.expired} ${fmtDate(c.expires_on)}`
      : c.fits
        ? `~${fmtDate(c.expires_on)}`
        : JUDGE.evidence.notFit,
    strike: c.expired,
    disabled: c.expired,
  }));
}

export function JudgeEvidence({
  row,
  column,
  onClose,
  onChanged,
}: {
  row: HistoryRow;
  column: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const kind = kindOf(column) ?? "material";
  const [detail, setDetail] = useState<JudgeDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [choice, setChoice] = useState<string>("");
  const [direct, setDirect] = useState("");
  const [busy, setBusy] = useState(false);
  const cell = row.cells[column];
  const current = String(shown(cell) ?? "");

  useEffect(() => {
    getJudge(row.row_id).then(setDetail).catch(setError);
  }, [row.row_id]);

  useEffect(() => setChoice(current), [current]);

  const apply = async () => {
    const value = choice === "__direct__" ? direct.trim() : choice;
    if (!value) return;
    setBusy(true);
    try {
      await patchCell(row.row_id, { column, value });
      onChanged();
      onClose();
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  const name = String(shown(row.cells["한글 제품명(모델넘버)"]) ?? row.model);
  const opts = detail ? options(kind, detail, row) : [];
  const evidence = cell?.evidence ?? [];

  return (
    <Modal
      title={JUDGE.evidence.title(column.split(" (")[0], name)}
      onClose={onClose}
      width={620}
      footer={
        <>
          <Button onClick={onClose}>닫기</Button>
          <Button variant="primary" disabled={busy || row.status === "승인"} onClick={apply}>
            {JUDGE.evidence.apply}
          </Button>
        </>
      }
    >
      <h4 style={{ margin: 0 }}>{JUDGE.evidence.basis}</h4>
      {evidence.length === 0 ? (
        <p style={{ color: colors.needCheck }}>? {JUDGE.evidence.noEvidence}</p>
      ) : (
        <ol style={{ paddingLeft: space.lg, fontSize: font.md }}>
          {evidence.map((e, i) => (
            <li key={`${e.ref}-${i}`}>
              <strong>{JUDGE.sources[e.source] ?? e.source}</strong> {e.note}
            </li>
          ))}
        </ol>
      )}
      {cell?.memo && <p style={{ color: colors.needCheck, fontSize: font.sm }}>? {cell.memo}</p>}
      {kind === "maker" && detail?.maker && (
        <div style={{ fontSize: font.sm, color: colors.muted }}>
          <div>{JUDGE.evidence.docAddress(detail.maker.address)}</div>
          {detail.maker.notes.map((n) => (
            <div key={n}>· {n}</div>
          ))}
        </div>
      )}

      <h4 style={{ marginBottom: space.xs }}>{JUDGE.evidence.candidates}</h4>
      {error !== null && <ErrorLine error={error} />}
      {!detail && error === null && <Skeleton lines={3} />}
      {detail && (
        <div role="radiogroup" style={{ display: "grid", gap: space.xs }}>
          {opts.map((o) => (
            <label
              key={o.value + o.label}
              style={{ display: "flex", gap: space.sm, alignItems: "baseline", color: o.disabled ? colors.expired : colors.text }}
            >
              <input
                type="radio"
                name="cand"
                disabled={o.disabled}
                checked={choice === o.value}
                onChange={() => setChoice(o.value)}
              />
              <span style={{ textDecoration: o.strike ? "line-through" : "none" }}>{o.label}</span>
              {o.note && <span style={{ fontSize: font.sm, color: colors.muted }}>{o.note}</span>}
            </label>
          ))}
          <label style={{ display: "flex", gap: space.sm, alignItems: "center" }}>
            <input type="radio" name="cand" checked={choice === "__direct__"} onChange={() => setChoice("__direct__")} />
            {JUDGE.evidence.direct}
            <input
              value={direct}
              onFocus={() => setChoice("__direct__")}
              onChange={(e) => setDirect(e.target.value)}
              style={{ flex: 1, padding: space.xs }}
            />
          </label>
        </div>
      )}
    </Modal>
  );
}
