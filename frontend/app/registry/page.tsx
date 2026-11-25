"use client";
// 탭 2. 서류 등록·만료 알림 › 실적 현황 (DESIGN 6-1): 숫자 카드 · 필터 · 실적 표 · 수입신고서·성적서 올리기. 배치만 한다. 담당: YHS
import { useCallback, useEffect, useState } from "react";

import { RecordTable } from "@/components/registry/RecordTable";
import { RecordUpload } from "@/components/registry/RecordUpload";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader, StatCard, StatGrid } from "@/components/ui/Card";
import { EmptyState, ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { space } from "@/components/ui/tokens";
import { shippers as getShippers } from "@/lib/api/core";
import { getRecords } from "@/lib/api/registry";
import { T } from "@/lib/text/common";
import { REGISTRY } from "@/lib/text/registry";
import type { Shipper } from "@/lib/types/core";
import type { PreciseRecord } from "@/lib/types/registry";
import { SHIPPER_KEY, rememberShipper } from "@/lib/hooks/useShipper";


export default function RegistryPage() {
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [shipperId, setShipperId] = useState("");
  const [maker, setMaker] = useState("");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("사용 가능");
  const [records, setRecords] = useState<PreciseRecord[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [upload, setUpload] = useState(false);
  const [all, setAll] = useState<PreciseRecord[] | null>(null);

  useEffect(() => {
    getShippers()
      .then((list) => {
        setShippers(list);
        const saved = window.localStorage.getItem(SHIPPER_KEY);
        setShipperId(list.find((s) => s.shipper_id === saved)?.shipper_id ?? list[0]?.shipper_id ?? "");
      })
      .catch(setError);
  }, []);

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    getRecords({ shipperId, maker, model, status })
      .then(setRecords)
      .catch(setError);
    getRecords({ shipperId, status: "" })
      .then(setAll)
      .catch(setError);
  }, [shipperId, maker, model, status]);

  useEffect(() => {
    const t = window.setTimeout(load, 250); // 검색어 입력 중에는 잠깐 기다린다
    return () => window.clearTimeout(t);
  }, [load]);

  const name = shippers.find((s) => s.shipper_id === shipperId)?.display_name ?? shipperId;
  const changed = load;
  const count = (st: string) => (all ? all.filter((r) => r.status === st).length : null);

  return (
    <div>
      <PageHeader
        title={REGISTRY.title}
        sub={REGISTRY.sub}
        actions={
          <Button variant="primary" disabled={!shipperId} onClick={() => setUpload(true)}>
            {REGISTRY.upload}
          </Button>
        }
      />
      <StatGrid>
        <StatCard label={REGISTRY.stats.all} value={all?.length ?? null} tone="info" />
        <StatCard label={REGISTRY.stats.valid} value={count("유효")} tone="ok" />
        <StatCard label={REGISTRY.stats.soon} value={count("만료 임박")} tone="warn" href="/registry/alerts/" />
        <StatCard label={REGISTRY.stats.expired} value={count("만료")} tone="neutral" />
      </StatGrid>
      <Card>
      <div style={{ display: "flex", gap: space.sm, alignItems: "center", flexWrap: "wrap", marginBottom: space.sm }}>
        <select
          value={shipperId}
          onChange={(e) => {
            setShipperId(e.target.value);
            rememberShipper(e.target.value);
          }}
          style={{ padding: space.xs }}
          aria-label={T.shipper}
        >
          {shippers.map((s) => (
            <option key={s.shipper_id} value={s.shipper_id}>
              {s.display_name}
            </option>
          ))}
        </select>
        <input placeholder={REGISTRY.filters.maker} value={maker} onChange={(e) => setMaker(e.target.value)} style={{ padding: space.xs }} />
        <input placeholder={REGISTRY.filters.model} value={model} onChange={(e) => setModel(e.target.value)} style={{ padding: space.xs }} />
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ padding: space.xs }} aria-label={REGISTRY.filters.status}>
          <option value="사용 가능">사용 가능(유효·만료 임박)</option>
          <option value="">{REGISTRY.filters.all}</option>
          <option value="유효">유효</option>
          <option value="만료 임박">만료 임박</option>
          <option value="만료">만료</option>
        </select>
      </div>

      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {records === null && error === null && <Skeleton lines={4} />}
      {records && records.length === 0 && (
        <EmptyState
          text={REGISTRY.empty}
          action={
            <Button variant="primary" onClick={() => setUpload(true)}>
              {REGISTRY.upload}
            </Button>
          }
        />
      )}
      {records && records.length > 0 && <RecordTable records={records} onChanged={changed} />}
      </Card>

      {upload && <RecordUpload shipperId={shipperId} shipperName={name} onClose={() => setUpload(false)} onDone={changed} />}
    </div>
  );
}
