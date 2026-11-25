"use client";
// 탭 2. 서류 등록·만료 알림 › 해외제조업소 코드 (DESIGN 6-2, A2-5). 배치만 한다. 담당: YHS
import { useState } from "react";

import { FactoryCodeTable } from "@/components/registry/FactoryCodeTable";
import { Card, PageHeader } from "@/components/ui/Card";
import { REGISTRY } from "@/lib/text/registry";

export default function FactoriesPage() {
  const [reloadKey, setReloadKey] = useState(0);
  return (
    <div>
      <PageHeader title={REGISTRY.factories.title} sub={REGISTRY.factoriesSub} />
      <Card>
        <FactoryCodeTable reloadKey={reloadKey} onChanged={() => setReloadKey((k) => k + 1)} />
      </Card>
    </div>
  );
}
