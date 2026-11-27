"use client";
// 규칙 묶음 4+1개(접수·행 구성·재질·실적·신고 묶음·제조사 코드) (DESIGN 7장). 이름·설명은 catalog에서. 담당: JUJ
// 묶음마다 흰 카드 + 규칙 사이 구분선, 재질 근거 순서는 세로 행(UI 개편 11/26). 규칙 값·로직은 그대로.
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { colors, font, radius, space } from "@/components/ui/tokens";
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
    // 세로 행: 1. 검역 이력 [↑][↓] … (UI 개편 11/26, 순서 바꾸기 로직은 그대로)
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: space.xs + 2, width: "100%", maxWidth: 460 }}>
        {list.map((v, i) => (
          <div
            key={v}
            style={{
              display: "flex",
              alignItems: "center",
              gap: space.xs,
              padding: `${space.xs + 2}px ${space.sm + 2}px`,
              background: colors.bgSubtle,
              border: `1px solid ${colors.line}`,
              borderRadius: 4,
            }}
          >
            <span style={{ flex: 1, minWidth: 0 }}>
              {i + 1}. {label(v)}
            </span>
            <Button small onClick={() => move(i, -1)} disabled={i === 0} aria-label={SETTINGS.orderUpLabel(label(v))}>
              {SETTINGS.orderUp}
            </Button>
            <Button
              small
              onClick={() => move(i, 1)}
              disabled={i === list.length - 1}
              aria-label={SETTINGS.orderDownLabel(label(v))}
            >
              {SETTINGS.orderDown}
            </Button>
          </div>
        ))}
      </div>
    );
  }
  // select_list: 정렬 기준(앞이 우선). 비우면 서류 순서 (로직 점검 반영 11/25)
  const list = Array.isArray(value) ? (value as string[]) : [];
  const label = (v: string) => rule.options?.find((o) => o.value === v)?.label ?? v;
  const rest = (rule.options ?? []).filter((o) => !list.includes(String(o.value)));
  return (
    <span style={{ display: "inline-flex", gap: space.xs, flexWrap: "wrap", alignItems: "center" }}>
      {list.length === 0 && <span style={{ color: colors.muted }}>{SETTINGS.docOrder}</span>}
      {list.map((v, i) => (
        <span key={v} style={{ border: `1px solid ${colors.border}`, borderRadius: 4, padding: "0 4px" }}>
          {i + 1}. {label(v)}{" "}
          <button
            type="button"
            className="mini"
            onClick={() => onChange(list.filter((x) => x !== v))}
            aria-label={`${label(v)} ${SETTINGS.removeSort}`}
          >
            ✕
          </button>
        </span>
      ))}
      {rest.length > 0 && (
        <select
          value=""
          onChange={(e) => e.target.value && onChange([...list, e.target.value])}
          aria-label={rule.label}
        >
          <option value="">{SETTINGS.addSort}</option>
          {rest.map((o) => (
            <option key={String(o.value)} value={String(o.value)}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </span>
  );
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

  // 묶음마다 흰 카드, 규칙 사이 얇은 구분선 (UI 개편 11/26, 프로토타입 화면 구조)
  return (
    <div>
      {catalog.groups.map((g) => (
        <section
          key={g.id}
          aria-label={g.label}
          style={{
            background: colors.bg,
            border: `1px solid ${colors.border}`,
            borderRadius: radius,
            padding: `${space.md}px ${space.md + 2}px ${space.xs}px`,
            marginBottom: space.md,
          }}
        >
          <h3 style={{ margin: 0, paddingBottom: space.sm + 4, fontSize: font.lg, fontWeight: 700, color: colors.text }}>
            {g.label}
          </h3>

          {g.id === "intake" && (
            // 표시 전용: 폴더 선택 기능 없음(폴더 ID는 .env). 저장 값이 아니다
            <Row>
              <label style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
                <span>{SETTINGS.driveFolder}</span>
                <select disabled aria-describedby="drive-folder-note" style={disabledSelect}>
                  <option>{SETTINGS.driveFolderUnset}</option>
                </select>
              </label>
              <Note id="drive-folder-note">
                {SETTINGS.driveFolderNote} {SETTINGS.driveFolderNoSelect}
              </Note>
            </Row>
          )}

          {g.id === "grouping" && (
            // 표시 전용: 동일 모선은 공통 반드시 조건(RULES 11-6). 설정 키가 아니며 로직은 기존 그대로
            <Row>
              <label style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
                <input type="checkbox" checked disabled readOnly />
                <span>{SETTINGS.sameVessel}</span>
                <Badge>{SETTINGS.fixed}</Badge>
              </label>
              <Note indent>{SETTINGS.sameVesselNote}</Note>
            </Row>
          )}

          {g.rules.map((r) => {
            const v = values[r.key];
            const differs = !r.fixed && JSON.stringify(v) !== JSON.stringify(defaults[r.key]);
            const ex = exceptions.find((e) => e.key === r.key);
            const isBool = r.type === "bool";
            const below = r.type === "multi" || r.type === "order"; // 이름 아래 줄에 입력
            const input = <RuleInput rule={r} value={v ?? null} onChange={(nv) => change(r, nv)} />;
            return (
              <Row key={r.key}>
                <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
                  {isBool && input}
                  <span>{r.label}</span>
                  {!isBool && !below && input}
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
                {below && <div style={{ marginTop: space.sm }}>{input}</div>}
                <Note indent={isBool}>{r.description}</Note>
                {SETTINGS.effects[r.key] && (
                  <Note indent={isBool} tone="effect">
                    {SETTINGS.effectLabel} {SETTINGS.effects[r.key]}
                  </Note>
                )}
              </Row>
            );
          })}
        </section>
      ))}
    </div>
  );
}

const disabledSelect = {
  padding: `${space.xs + 1}px ${space.sm}px`,
  border: `1px solid ${colors.border}`,
  borderRadius: 4,
  background: colors.bgSubtle,
  color: colors.muted,
  cursor: "not-allowed",
} as const;

/** 규칙 한 줄: 위쪽 얇은 구분선 + 여백 */
function Row({ children }: { children: ReactNode }) {
  return <div style={{ padding: `${space.sm + 4}px 0`, borderTop: `1px solid ${colors.line}` }}>{children}</div>;
}

/** 설명 한 줄(체크박스 규칙은 체크박스만큼 들여씀) */
function Note({
  children,
  indent = false,
  tone = "muted",
  id,
}: {
  children: ReactNode;
  indent?: boolean;
  tone?: "muted" | "effect";
  id?: string;
}) {
  return (
    <div
      id={id}
      style={{
        fontSize: font.sm,
        color: tone === "effect" ? colors.brand : colors.muted,
        marginTop: space.xs,
        marginLeft: indent ? 22 : 0,
      }}
    >
      {children}
    </div>
  );
}
