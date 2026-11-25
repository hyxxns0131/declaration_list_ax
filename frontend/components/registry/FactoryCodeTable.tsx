"use client";
// 해외제조업소 코드 표 (DESIGN 6장, A2-5): 코드·업소명·등록(갱신)일·만료일·상태, 등록일 입력. 담당: YHS
// 만료일 계산은 백엔드(factory_codes)에서 한다. 이 부품은 그리기와 등록일 저장만.
import { useCallback, useEffect, useState } from "react";

import { Badge, type Tone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate } from "@/lib/format";
import { getFactories, patchFactory } from "@/lib/api/registry";
import { REGISTRY } from "@/lib/text/registry";
import type { FactoryCode, FactoryStatus } from "@/lib/types/registry";

const F = REGISTRY.factories;
const TONE: Record<FactoryStatus, Tone> = { 유효: "ok", "만료 임박": "edited", 만료: "mismatch", "확인 필요": "needCheck" };

const th = { textAlign: "left", padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.sm } as const;
const td = { padding: space.xs, borderBottom: `1px solid ${colors.border}`, fontSize: font.md } as const;

export function FactoryCodeTable({ reloadKey, onChanged }: { reloadKey: number; onChanged: () => void }) {
  const [rows, setRows] = useState<FactoryCode[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    setError(null);
    getFactories().then(setRows).catch(setError);
  }, []);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  const save = async (code: string, registeredOn: string | null) => {
    setBusy(true);
    try {
      await patchFactory(code, registeredOn);
      setEditing(null);
      setMsg(F.saved(code));
      load();
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section style={{ marginTop: space.lg }}>
      <strong>{F.title}</strong>
      <p style={{ color: colors.muted, fontSize: font.sm, margin: `${space.xs}px 0` }}>{F.note}</p>
      {msg && <Notice>{msg}</Notice>}
      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {rows === null && error === null && <Skeleton lines={3} />}
      {rows && rows.length === 0 && <p style={{ color: colors.muted }}>{F.empty}</p>}
      {rows && rows.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>{F.cols.code}</th>
              <th style={th}>{F.cols.name}</th>
              <th style={th}>{F.cols.registered}</th>
              <th style={th}>{F.cols.expires}</th>
              <th style={th}>{F.cols.status}</th>
              <th style={th}>{F.cols.source}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.code} style={{ color: f.status === "만료" ? colors.expired : colors.text }}>
                <td style={td}>{f.code}</td>
                <td style={td}>{f.name || "-"}</td>
                <td style={td}>
                  {editing === f.code ? (
                    <span style={{ display: "inline-flex", gap: space.xs }}>
                      <input type="date" value={value} onChange={(e) => setValue(e.target.value)} />
                      <Button small variant="primary" disabled={busy || !value} onClick={() => save(f.code, value)}>
                        {F.save}
                      </Button>
                      <Button small disabled={busy} onClick={() => save(f.code, null)}>
                        {F.clear}
                      </Button>
                      <Button small variant="ghost" onClick={() => setEditing(null)}>
                        {F.cancel}
                      </Button>
                    </span>
                  ) : (
                    <span style={{ display: "inline-flex", gap: space.xs, alignItems: "baseline" }}>
                      {f.registered_on ? fmtDate(f.registered_on) : <span style={{ color: colors.needCheck }}>? {F.unknown}</span>}
                      <Button
                        small
                        variant="ghost"
                        onClick={() => {
                          setEditing(f.code);
                          setValue(f.registered_on ?? "");
                        }}
                      >
                        {F.edit}
                      </Button>
                    </span>
                  )}
                </td>
                <td style={{ ...td, textDecoration: f.status === "만료" ? "line-through" : "none" }}>
                  {f.expires_on ? fmtDate(f.expires_on) : "—"}
                </td>
                <td style={td}>
                  <Badge tone={TONE[f.status]}>
                    {f.status === "만료 임박" && f.days_left !== null ? F.soon(f.days_left) : f.status}
                  </Badge>
                </td>
                <td style={{ ...td, color: colors.muted, fontSize: font.sm }}>{f.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
