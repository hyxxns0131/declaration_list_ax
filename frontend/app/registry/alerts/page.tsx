"use client";
// 탭 2. 서류 등록·만료 알림 › 만료 알림 (DESIGN 6-3): 실적·해외제조업소 코드 3개월·1개월 전 메일. 배치만 한다. 담당: YHS
import { ExpiryAlerts } from "@/components/registry/ExpiryAlerts";
import { Card, PageHeader } from "@/components/ui/Card";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { EmptyState, ErrorLine } from "@/components/ui/StateBox";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { REGISTRY } from "@/lib/text/registry";

export default function AlertsPage() {
  const { shippers, shipperId, setShipperId, error } = useShipper();
  return (
    <div>
      <PageHeader
        title={REGISTRY.alertsTitle}
        sub={REGISTRY.alertsSub}
        actions={<ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />}
      />
      {error !== null && <ErrorLine error={error} />}
      <Card>{shipperId ? <ExpiryAlerts shipperId={shipperId} reloadKey={0} /> : <EmptyState text={T.pickShipper} />}</Card>
    </div>
  );
}
