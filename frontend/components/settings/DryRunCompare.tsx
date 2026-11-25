"use client";
// 시험 실행 결과: 바꾸기 전/후 신고건을 나란히 (DESIGN 7장, 제안서 4번 시연). 담당: JUJ
import { Modal } from "@/components/ui/Modal";
import { colors, font, space } from "@/components/ui/tokens";
import { SETTINGS } from "@/lib/text/settings";
import type { DryRunDecl, DryRunOut, RuleValue } from "@/lib/types/settings";

const D = SETTINGS.dry;

function show(v: RuleValue): string {
  if (v === true) return D.on;
  if (v === false) return D.off;
  if (v === null || v === undefined) return D.none;
  if (Array.isArray(v)) return v.map((x) => (typeof x === "string" ? x : x.key)).join(", ") || D.none;
  return String(v);
}

function Column({ title, decls }: { title: string; decls: DryRunDecl[] }) {
  return (
    <div style={{ flex: 1, minWidth: 260 }}>
      <h4 style={{ margin: `0 0 ${space.sm}px` }}>{title}</h4>
      {decls.map((d, i) => (
        <div key={d.declaration_id} style={{ border: `1px solid ${colors.border}`, borderRadius: 4, padding: space.sm, marginBottom: space.sm }}>
          <strong>{D.decl(i + 1)}</strong>
          <ul style={{ margin: `${space.xs}px 0`, paddingLeft: space.lg, fontSize: font.md }}>
            {d.rows.map((r, j) => (
              <li key={`${r}-${j}`}>{r}</li>
            ))}
          </ul>
          {d.records.length > 0 && <div style={{ fontSize: font.sm, color: colors.muted }}>실적 {Array.from(new Set(d.records)).join(", ")}</div>}
          {d.warnings.map((w) => (
            <div key={w} style={{ fontSize: font.sm, color: colors.needCheck }}>
              ? {w}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export function DryRunCompare({ result, onClose }: { result: DryRunOut; onClose: () => void }) {
  return (
    <Modal title={D.title(result.source)} onClose={onClose} width={900}>
      <div style={{ display: "flex", gap: space.md, flexWrap: "wrap" }}>
        <Column title={`${D.before} (${result.row_count.before}행)`} decls={result.before} />
        <Column title={`${D.after} (${result.row_count.after}행)`} decls={result.after} />
      </div>
      <h4>{D.changed}</h4>
      {result.changed.length === 0 ? (
        <p style={{ color: colors.muted }}>{D.noChange}</p>
      ) : (
        <ul>
          {result.changed.map((c) => (
            <li key={c.key}>
              {c.label} ({show(c.before)} → {show(c.after)})
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
