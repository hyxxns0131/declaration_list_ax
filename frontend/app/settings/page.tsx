"use client";
// 탭 1. 기업 설정 › 화주 선택·관리 (DESIGN 7-0, HS 요청 11/25): 작업 화주 고르기 · 새 화주 추가 · 화주 삭제(기본 A·B 제외).
// 여기서 고른 화주를 뒤 탭(서류 등록·판단·검역 리스트)이 같이 쓴다. 규칙 설정은 /settings/rules. 담당: KHS(화면 배치) · JUJ(화주 API)
import Link from "next/link";
import { useState } from "react";

import { ShipperPicker } from "@/components/settings/ShipperPicker";
import { PageHeader } from "@/components/ui/Card";
import { ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { forgetShipper, useShipper } from "@/lib/hooks/useShipper";
import { SETTINGS } from "@/lib/text/settings";

const P = SETTINGS.pick;

export default function ShipperHomePage() {
  const { shippers, shipperId, setShipperId, chosen, loaded, reload, error } = useShipper();
  const [note, setNote] = useState("");

  return (
    <div>
      <PageHeader
        title={P.pageTitle}
        sub={P.pageSub}
        actions={chosen ? <Link href="/settings/rules/">{P.rulesLink}</Link> : undefined}
      />
      {error !== null && <ErrorLine error={error} onRetry={() => void reload()} />}
      {note && <Notice>{note}</Notice>}
      {!loaded && <Skeleton lines={4} />}
      {loaded && (
        <ShipperPicker
          shippers={shippers}
          current={shipperId}
          chosen={chosen}
          onPick={(id) => {
            setNote("");
            setShipperId(id);
          }}
          onAdded={async (id) => {
            const list = await reload();
            setShipperId(id);
            setNote(P.added(list.find((s) => s.shipper_id === id)?.display_name ?? id));
          }}
          onDeleted={async (gone) => {
            if (chosen && gone.shipper_id === shipperId) forgetShipper(); // 작업 중이던 화주면 선택을 지운다
            await reload();
            setNote(P.removed(gone.display_name));
          }}
        />
      )}
    </div>
  );
}
