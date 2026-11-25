"use client";
// 규칙 묶음 4+1개(접수·행 구성·재질·실적·신고 묶음·제조사 코드) (DESIGN 7장). 이름·설명은 catalog에서. 담당: JUJ
import { Badge } from "@/components/ui/Badge";
import { colors, font, space } from "@/components/ui/tokens";
import { SETTINGS } from "@/lib/text/settings";
import type { Catalog, RuleDef, RuleValue, ShipperException, ShipperValues } from "@/lib/types/settings";

function RuleInput({
  rule,
  value,
  onChange,
}: {
  rule: RuleDef;
  value: RuleValue;
  onChange: (v: RuleValue) => void;
}) {
  if (rule.type === "bool") {
    return (
      <input
        type="checkbox"
        disabled={rule.fixed}
        checked={rule.fixed ? true : Boolean(value)}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={rule.label}
      />
    );
  }
  if (rule.type === "int") {
    return (
      <input
        type="number"
        min={1}
        value={typeof value === "number" ? value : ""}
        placeholder={SETTINGS.noLimit}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        style={{ width: 90, padding: 2 }}
        aria-label={rule.label}
      />
    );
  }
  if (rule.type === "select") {
    return (
      <select
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
        aria-label={rule.label}
      >
        {(rule.options ?? []).map((o) => (
          <option key={String(o.value)} value={o.value ?? ""}>
            {o.label}
          </option>
        ))}
      </select>
    );
  }
  if (rule.type === "multi") {
    const list = Array.isArray(value) ? (value as string[]) : [];
    return (
      <span style={{ display: "inline-flex", flexWrap: "wrap", gap: space.sm }}>
        {(rule.options ?? []).map((o) => {
          const v = String(o.value);
          return (
            <label key={v}>
              <input
                type="checkbox"
                checked={list.includes(v)}
                onChange={(e) => onChange(e.target.checked ? [...list, v] : list.filter((x) => x !== v))}
              />
              {o.label}
            </label>
          );
        })}
      </span>
    );
  }
  if (rule.type === "order") {
    const list = Array.isArray(value) ? (value as string[]) : [];
    const label = (v: string) => rule.options?.find((o) => o.value === v)?.label ?? v;
    const move = (i: number, d: -1 | 1) => {
      const next = [...list];
      const j = i + d;
      if (j < 0 || j >= next.length) return;
      [next[i], next[j]] = [next[j], next[i]];
      onChange(next);
    };
    return (
      <span style={{ display: "inline-flex", gap: space.xs, flexWrap: "wrap" }}>
        {list.map((v, i) => (
          <span key={v} style={{ border: `1px solid ${colors.border}`, borderRadius: 4, padding: "0 4px" }}>
            {i + 1}. {label(v)}{" "}
            <button type="button" className="mini" onClick={() => move(i, -1)} aria-label="앞으로">
              {SETTINGS.orderUp}
            </button>
            <button type="button" className="mini" onClick={() => move(i, 1)} aria-label="뒤로">
              {SETTINGS.orderDown}
            </button>
          </span>
        ))}
      </span>
    );
  }
  // select_list: 정렬 기준 — 지금은 '서류 순서'만
  return <span style={{ color: colors.muted }}>{rule.options?.[0]?.label}</span>;
}

export function RuleGroups({
  catalog,
  values,
  defaults,
  onChange,
}: {
  catalog: Catalog;
  values: ShipperValues;
  defaults: ShipperValues;
  onChange: (key: string, value: RuleValue, exception?: ShipperException) => void;
}) {
  const exceptions = (Array.isArray(values.exceptions) ? values.exceptions : []) as ShipperException[];

  const change = (rule: RuleDef, v: RuleValue) => {
    const differs = JSON.stringify(v) !== JSON.stringify(defaults[rule.key]);
    if (rule.exception && differs && !exceptions.some((e) => e.key === rule.key)) {
      const reason = window.prompt(SETTINGS.reasonPrompt(rule.label), SETTINGS.reasonDefault);
      if (!reason) return; // 이유 없이는 예외를 켜지 않는다(RULES 11-12)
      onChange(rule.key, v, { key: rule.key, reason, basis: "확인 필요", since: new Date().toISOString().slice(0, 10) });
      return;
    }
    onChange(rule.key, v);
  };

  return (
    <div>
      {catalog.groups.map((g) => (
        <fieldset key={g.id} style={{ border: `1px solid ${colors.border}`, borderRadius: 6, marginBottom: space.md }}>
          <legend style={{ fontWeight: 600 }}>▸ {g.label}</legend>
          {g.rules.map((r) => {
            const v = values[r.key];
            const differs = !r.fixed && JSON.stringify(v) !== JSON.stringify(defaults[r.key]);
            const ex = exceptions.find((e) => e.key === r.key);
            return (
              <div key={r.key} style={{ padding: `${space.xs}px 0`, borderBottom: `1px dashed ${colors.bgSubtle}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
                  <RuleInput rule={r} value={v ?? null} onChange={(nv) => change(r, nv)} />
                  <span>{r.label}</span>
                  {r.fixed && <Badge>{SETTINGS.fixed}</Badge>}
                  {r.proposal && <span style={{ fontSize: font.sm, color: colors.muted }}>{SETTINGS.proposal}</span>}
                  {r.advanced && <Badge>{SETTINGS.advanced}</Badge>}
                  {differs && !r.exception && <Badge tone="info">{SETTINGS.differs}</Badge>}
                  {r.exception && (differs || ex) && (
                    <Badge tone="edited" title={ex ? `${ex.reason} (${ex.since ?? ""})` : ""}>
                      {SETTINGS.exception}
                    </Badge>
                  )}
                </div>
                <div style={{ fontSize: font.sm, color: colors.muted, marginLeft: 22 }}>{r.description}</div>
              </div>
            );
          })}
        </fieldset>
      ))}
    </div>
  );
}
