"use client";
// 탭 3. 검역 리스트 › ① 서류 올리기·추출 (DESIGN 3-1-1, 검역 리스트 탭 1단계). 선적 건 카드(받은 서류 칩·추출 상태,
// 펼치면 서류별 추출값) + 드라이브 접수 폴더 가져오기(화주 설정 inbox). 올리기는 공통 머리 [서류 올리기]. 담당: KHS
import { useCallback, useEffect, useState } from "react";

import { ShipmentCards } from "@/components/reader/ShipmentCards";
import { UploadDialog } from "@/components/reader/UploadDialog";
import { ListHeader } from "@/components/review/ListHeader";
import { pillPrimary, pillSecondary } from "@/components/review/listUi";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorLine, Notice, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getShipments } from "@/lib/api/history";
import { scanInbox } from "@/lib/api/reader";
import { getShipper } from "@/lib/api/settings";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { Shipment } from "@/lib/types/reader";

const U = HOME.upload;

export default function UploadPage() {
  const { shipperId, shipperName, error: shipperError } = useShipper();
  const [ships, setShips] = useState<Shipment[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [inboxOn, setInboxOn] = useState(false);
  const [inboxMsg, setInboxMsg] = useState("");

  const load = useCallback(() => {
    if (!shipperId) return;
    setError(null);
    getShipments(shipperId).then(setShips).catch(setError);
  }, [shipperId]);

  useEffect(() => {
    setShips(null);
    load();
  }, [load]);

  // 화주 설정 inbox가 켜져 있을 때만 [드라이브 접수 폴더에서 가져오기]
  useEffect(() => {
    if (!shipperId) return;
    getShipper(shipperId)
      .then((d) => setInboxOn(Boolean(d.settings.inbox)))
      .catch(() => setInboxOn(false));
  }, [shipperId]);

  const scan = async () => {
    setBusy(true);
    setInboxMsg("");
    try {
      const out = await scanInbox(shipperId);
      setInboxMsg(out.ok ? U.inboxDone(out.imported.length) : out.reason);
      load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const missing = ships?.filter((s) => s.missing.length).length ?? 0;

  return (
    <div>
      <ListHeader title={T.side.list.upload} onChanged={() => load()} />
      <p style={{ margin: `0 0 ${space.sm}px`, fontSize: font.md, color: colors.muted }}>{U.sub}</p>
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}

      {inboxOn && (
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: space.md, flexWrap: "wrap" }}>
            <button type="button" style={pillSecondary} disabled={!shipperId || busy} onClick={scan}>
              {busy ? U.inboxBusy : U.inbox}
            </button>
            <span style={{ fontSize: font.sm, color: colors.muted }}>{U.inboxHint}</span>
          </div>
          {inboxMsg && <Notice tone="warn">{inboxMsg}</Notice>}
        </Card>
      )}

      {ships === null && error === null && <Skeleton lines={4} />}
      {ships && ships.length === 0 && (
        <Card>
          <EmptyState
            text={U.emptyShipments}
            action={
              <button type="button" style={pillPrimary} onClick={() => setOpen(true)} disabled={!shipperId}>
                ⇪ {HOME.buttons.upload}
              </button>
            }
          />
        </Card>
      )}
      {ships && ships.length > 0 && (
        <>
          <div style={{ fontSize: font.md, margin: `${space.xs}px 0 ${space.sm}px` }}>
            {U.shipmentCount(ships.length, missing)}
          </div>
          <ShipmentCards shipments={ships} />
        </>
      )}

      {open && (
        <UploadDialog
          shipperId={shipperId}
          shipperName={shipperName}
          onClose={() => setOpen(false)}
          onUploaded={() => load()}
        />
      )}
    </div>
  );
}
