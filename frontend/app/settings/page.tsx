"use client";
// 탭 4. 기업 설정 (DESIGN 7장): 화주 목록 · 규칙 묶음 · 시험 실행 · 저장. 배치와 상태 연결만. 담당: JUJ
import { useCallback, useEffect, useState } from "react";

import { DryRunCompare } from "@/components/settings/DryRunCompare";
import { RuleGroups } from "@/components/settings/RuleGroups";
import { ShipperList } from "@/components/settings/ShipperList";
import { Button } from "@/components/ui/Button";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { dryRun, getRules, getShipper, listShippers, saveShipper } from "@/lib/api/settings";
import { SETTINGS } from "@/lib/text/settings";
import type { Shipper } from "@/lib/types/core";
import type { Catalog, DryRunOut, RuleValue, ShipperException, ShipperValues } from "@/lib/types/settings";

export default function SettingsPage() {
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [current, setCurrent] = useState("");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [defaults, setDefaults] = useState<ShipperValues>({});
  const [saved, setSaved] = useState<ShipperValues | null>(null);
  const [values, setValues] = useState<ShipperValues | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<"" | "save" | "dry">("");
  const [msg, setMsg] = useState("");
  const [dry, setDry] = useState<DryRunOut | null>(null);

  const dirty = values !== null && saved !== null && JSON.stringify(values) !== JSON.stringify(saved);

  const loadList = useCallback(async (pick?: string) => {
    try {
      const list = await listShippers();
      setShippers(list);
      setCurrent((cur) => pick ?? (cur || list[0]?.shipper_id || ""));
    } catch (e) {
      setError(e);
    }
  }, []);

  useEffect(() => {
    getRules()
      .then((r) => {
        setCatalog(r.catalog);
        setDefaults(r.default);
      })
      .catch(setError);
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (!current) return;
    setValues(null);
    setMsg("");
    getShipper(current)
      .then((d) => {
        setSaved(d.settings);
        setValues(d.settings);
      })
      .catch(setError);
  }, [current]);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const pick = (id: string) => {
    if (dirty && !window.confirm(SETTINGS.leaveConfirm)) return;
    setCurrent(id);
  };

  const change = (key: string, value: RuleValue, exception?: ShipperException) => {
    if (!values) return;
    const next: ShipperValues = { ...values, [key]: value };
    if (exception) {
      const list = (Array.isArray(values.exceptions) ? values.exceptions : []) as ShipperException[];
      next.exceptions = [...list.filter((e) => e.key !== key), exception];
    }
    setValues(next);
  };

  const editable = (v: ShipperValues): ShipperValues => {
    const keys = new Set([...(catalog?.groups.flatMap((g) => g.rules.map((r) => r.key)) ?? []), ...(catalog?.meta_keys ?? [])]);
    return Object.fromEntries(Object.entries(v).filter(([k]) => keys.has(k) && k !== "group_by_maker"));
  };

  const save = async () => {
    if (!values) return;
    setBusy("save");
    setError(null);
    try {
      const out = await saveShipper(current, editable(values));
      setSaved(out.settings);
      setValues(out.settings);
      setMsg(SETTINGS.saved(out.rebuilt?.bls ?? 0));
      await loadList(current);
    } catch (e) {
      setError(e); // 입력값은 지우지 않는다(DESIGN 7장)
    } finally {
      setBusy("");
    }
  };

  const runDry = async () => {
    if (!values) return;
    setBusy("dry");
    setError(null);
    try {
      setDry(await dryRun(current, editable(values)));
    } catch (e) {
      setError(e);
    } finally {
      setBusy("");
    }
  };

  const name = shippers.find((s) => s.shipper_id === current)?.display_name ?? current;

  return (
    <div>
      <h2 style={{ margin: `0 0 ${space.sm}px`, fontSize: font.xl }}>{SETTINGS.title}</h2>
      <div style={{ display: "flex", gap: space.lg }}>
      <ShipperList shippers={shippers} current={current} onPick={pick} onCreated={(id) => void loadList(id)} />
      <section style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: space.sm, marginBottom: space.sm }}>
          <strong style={{ fontSize: font.lg }}>{name}</strong>
          {dirty && <span style={{ color: colors.edited, fontSize: font.sm }}>✎ {SETTINGS.unsaved}</span>}
          <span style={{ marginLeft: "auto", display: "flex", gap: space.sm }}>
            <Button onClick={runDry} disabled={!values || busy !== ""}>
              {busy === "dry" ? SETTINGS.running : SETTINGS.dryRun}
            </Button>
            <Button
              variant="primary"
              onClick={save}
              disabled={!dirty || busy !== ""}
              style={dirty ? { boxShadow: `0 0 0 3px ${colors.primarySoft}` } : undefined}
            >
              {busy === "save" ? "저장 중…" : SETTINGS.save}
            </Button>
          </span>
        </div>
        <p style={{ fontSize: font.sm, color: colors.muted, marginTop: 0 }}>
          {SETTINGS.driveFolder}: {SETTINGS.driveFolderNote}
        </p>
        {error !== null && <ErrorLine error={error} />}
        {msg && <Notice>{msg}</Notice>}
        {(!catalog || !values) && error === null && <Skeleton lines={6} />}
        {catalog && values && <RuleGroups catalog={catalog} values={values} defaults={defaults} onChange={change} />}
      </section>
      {dry && <DryRunCompare result={dry} onClose={() => setDry(null)} />}
      </div>
    </div>
  );
}
