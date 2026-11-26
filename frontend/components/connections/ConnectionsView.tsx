"use client";
// 탭 6. 연결 설정 화면 본문. part="external" → 전체 연결 표(/connections), part="ai" → AI 모델 카드(/connections/ai).
// 두 화면이 같은 상태·[연결 검사] 동작을 쓰므로 한 파일에 둔다. 담당: KHS (HS 요청 11/25)
import { useCallback, useEffect, useState } from "react";

import { Badge, type Tone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { checkConnections, connections, setAiChoice } from "@/lib/api/core";
import { CONN } from "@/lib/text/connections";
import { T } from "@/lib/text/common";
import type { AiModelOption, ConnRow, Connections } from "@/lib/types/core";

function stateOf(row: ConnRow): { tone: Tone; text: string; detail: string } {
  if (row.last) {
    const tone: Tone = row.last.state === "ok" ? "ok" : row.last.state === "fail" ? "mismatch" : "needInput";
    return { tone, text: CONN.state[row.last.state], detail: row.last.message };
  }
  if (!row.configured) return { tone: "needInput", text: CONN.state.off, detail: row.config_reason };
  return { tone: "info", text: CONN.state.ready, detail: "" };
}

function fmtTime(iso: string | undefined): string {
  if (!iso) return CONN.never;
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/.exec(iso);
  return m ? `${m[1]}.${m[2]}.${m[3]} ${m[4]}:${m[5]}:${m[6]}` : iso;
}

const th = { textAlign: "left" as const };
const td = { verticalAlign: "middle" as const };

const CUSTOM = "__custom__";

function optionText(m: AiModelOption): string {
  const tier = m.tier && m.group === "recommended" ? ` · ${m.tier}` : "";
  const na = m.available === false ? ` (${CONN.notAvailable})` : "";
  return `${m.id}${tier}${na}`;
}

function AiCard({
  row,
  busy,
  onCheck,
  onModel,
}: {
  row: ConnRow;
  busy: boolean;
  onCheck: () => void;
  onModel: (m: string) => void;
}) {
  const [custom, setCustom] = useState<string | null>(null); // null = 직접 입력 칸 닫힘
  const ai = row.ai;
  if (!ai) return null;
  const st = stateOf(row);
  const groups: { key: AiModelOption["group"]; label: string }[] = [
    { key: "recommended", label: CONN.groupRecommended },
    { key: "account", label: CONN.groupAccount },
    { key: "custom", label: CONN.groupCustom },
  ];
  const pick = (v: string) => {
    if (v === CUSTOM) {
      setCustom("");
      return;
    }
    setCustom(null);
    onModel(v);
  };
  const applyCustom = () => {
    const v = (custom ?? "").trim();
    if (!v) return;
    setCustom(null);
    onModel(v);
  };
  return (
    <div
      style={{
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        padding: space.md,
        background: colors.bg,
        maxWidth: 640,
        minWidth: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap" }}>
        <strong style={{ fontSize: font.lg }}>{row.label}</strong>
        <span style={{ fontSize: font.sm, color: colors.muted }}>{CONN.onlyOpenai}</span>
        <span style={{ marginLeft: "auto" }}>
          <Badge tone={st.tone}>{st.text}</Badge>
        </span>
      </div>

      <div style={{ marginTop: space.sm, fontSize: font.sm, color: colors.muted }}>{CONN.nowUsing}</div>
      <div style={{ fontSize: font.xl, fontWeight: 700, wordBreak: "break-all" }}>{ai.model}</div>

      <div style={{ marginTop: space.sm }}>
        <label
          htmlFor={`model-${row.key}`}
          style={{ display: "block", fontSize: font.md, fontWeight: 600, marginBottom: space.xs }}
        >
          {CONN.version}
        </label>
        <div style={{ display: "flex", gap: space.sm, flexWrap: "wrap", alignItems: "center" }}>
          <select
            id={`model-${row.key}`}
            value={custom !== null ? CUSTOM : ai.model}
            disabled={busy}
            onChange={(e) => pick(e.target.value)}
            style={{ padding: `${space.xs + 2}px ${space.sm}px`, fontSize: font.md, flex: "1 1 260px", minWidth: 0 }}
          >
            {groups.map((g) => {
              const items = ai.models.filter((m) => m.group === g.key);
              return items.length ? (
                <optgroup key={g.key} label={g.label}>
                  {items.map((m) => (
                    <option key={`${g.key}-${m.id}`} value={m.id}>
                      {optionText(m)}
                    </option>
                  ))}
                </optgroup>
              ) : null;
            })}
            <option value={CUSTOM}>{CONN.customOption}</option>
          </select>
          <Button small variant="primary" onClick={onCheck} disabled={busy}>
            {busy ? CONN.checking : CONN.check}
          </Button>
        </div>
        {custom !== null && (
          <div style={{ display: "flex", gap: space.sm, marginTop: space.sm }}>
            <input
              autoFocus
              value={custom}
              placeholder={CONN.customPlaceholder}
              onChange={(e) => setCustom(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applyCustom()}
              style={{ flex: 1, minWidth: 0, padding: `${space.xs + 2}px ${space.sm}px`, fontSize: font.md }}
            />
            <Button small variant="primary" onClick={applyCustom} disabled={busy || !custom.trim()}>
              {CONN.apply}
            </Button>
            <Button small onClick={() => setCustom(null)}>
              {T.cancel}
            </Button>
          </div>
        )}
      </div>

      {!ai.account_list && (
        <Notice tone="warn">{CONN.noAccountList}</Notice>
      )}
      <div style={{ marginTop: space.sm, fontSize: font.sm, color: colors.muted }}>
        {st.detail || row.uses} · {CONN.cols.checkedAt} {fmtTime(row.last?.checked_at)}
      </div>
    </div>
  );
}

export function ConnectionsView({ part }: { part: "external" | "ai" }) {
  const [data, setData] = useState<Connections | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null); // "all" | 연결 key
  const [note, setNote] = useState("");

  const load = useCallback(() => {
    setError(null);
    connections().then(setData).catch(setError);
  }, []);
  useEffect(load, [load]);

  const run = async (key: string, work: () => Promise<Connections>, done = "") => {
    setBusy(key);
    setError(null);
    try {
      setData(await work());
      setNote(done);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  const check = (key: string) => run(key, () => checkConnections(key));
  const checkMany = (rows: ConnRow[]) =>
    run("all", async () => {
      let out: Connections | null = null;
      for (const r of rows) out = await checkConnections(r.key);
      return out ?? connections();
    });
  const pickModel = (row: ConnRow, model: string) =>
    run(row.key, async () => {
      await setAiChoice(row.key, model);
      return checkConnections(row.key); // 고른 모델을 이 계정에서 쓸 수 있는지 바로 확인
    }, CONN.modelSaved(model));

  const aiRows = data?.rows.filter((r) => r.ai) ?? [];
  const allRows = data?.rows ?? []; // 전체 연결 표는 AI 줄도 함께 보여 준다
  const shownRows = part === "ai" ? aiRows : allRows;
  const lastAll = shownRows
    .map((r) => r.last?.checked_at ?? "")
    .sort()
    .at(-1);

  return (
    <div>
      <PageHeader
        title={part === "ai" ? CONN.aiTitle : CONN.title}
        sub={part === "ai" ? CONN.aiSub : CONN.sub}
        actions={
          <>
            <span style={{ fontSize: font.sm, color: colors.muted }}>
              {CONN.cols.checkedAt} {fmtTime(lastAll || undefined)}
            </span>
            <Button variant="primary" onClick={() => (part === "ai" ? checkMany(aiRows) : check("all"))} disabled={busy !== null}>
              {busy === "all" ? CONN.checking : part === "ai" ? CONN.checkAi : CONN.checkAll}
            </Button>
          </>
        }
      />
      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {note && <Notice>{note}</Notice>}
      {!data && error === null && <Skeleton lines={6} />}

      {data && part === "ai" && (
        <>
          <Card title={CONN.aiCards}>
            {!data.llm_enabled && <Notice tone="warn">{CONN.llmOff}</Notice>}
            {data.mask_names && (
              <Notice tone={data.mask_names.exists ? undefined : "warn"}>
                {data.mask_names.exists
                  ? CONN.maskOk(data.mask_names.count, data.mask_names.shippers)
                  : CONN.maskMissing(data.mask_names.last_error)}
              </Notice>
            )}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr)",
                gap: space.md,
              }}
            >
              {aiRows.map((row) => (
                <AiCard
                  key={row.key}
                  row={row}
                  busy={busy !== null}
                  onCheck={() => check(row.key)}
                  onModel={(m) => pickModel(row, m)}
                />
              ))}
            </div>
            <p style={{ margin: `${space.sm}px 0 0`, fontSize: font.sm, color: colors.muted }}>
              {CONN.appliesAll} {CONN.tokenNote}
            </p>
          </Card>
        </>
      )}

      {data && part === "external" && (
        <>
          <Card title={CONN.tableTitle}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: font.md }}>
                <thead>
                  <tr>
                    <th style={th}>{CONN.cols.name}</th>
                    <th style={th}>{CONN.cols.uses}</th>
                    <th style={th}>{CONN.cols.state}</th>
                    <th style={th}>{CONN.cols.detail}</th>
                    <th style={th}>{CONN.cols.checkedAt}</th>
                    <th style={th} />
                  </tr>
                </thead>
                <tbody>
                  {allRows.map((row) => {
                    const st = stateOf(row);
                    return (
                      <tr key={row.key}>
                        <td style={{ ...td, fontWeight: 600, whiteSpace: "nowrap" }}>{row.label}</td>
                        <td style={{ ...td, color: colors.muted }}>{row.uses}</td>
                        <td style={td}>
                          <Badge tone={st.tone}>{st.text}</Badge>
                        </td>
                        <td style={td}>{st.detail}</td>
                        <td style={{ ...td, whiteSpace: "nowrap", color: colors.muted }}>
                          {fmtTime(row.last?.checked_at)}
                        </td>
                        <td style={{ ...td, textAlign: "right" }}>
                          <Button small onClick={() => check(row.key)} disabled={busy !== null}>
                            {busy === row.key ? CONN.checking : CONN.check}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p style={{ margin: `${space.sm}px 0 0`, fontSize: font.sm, color: colors.muted }}>{CONN.envNote}</p>
          </Card>
        </>
      )}
    </div>
  );
}
