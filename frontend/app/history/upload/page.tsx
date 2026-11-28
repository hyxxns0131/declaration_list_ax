"use client";
// 탭 3. 검역 리스트 › ① 서류 올리기·추출 (DESIGN 3-1-1·3-7, 검역 리스트 탭 1단계). 담당: KHS
// HS 요청 11/27 "보기 편하게, 초보자도 쉽게": '지금 할 일' 한 줄(3단계 안내 상자는 HS 요청으로 뺌),
// 선적 건 카드는 할 일 있는 건이 위·끝난 건이 아래, 카드마다 버튼 하나. 드라이브 접수 폴더 가져오기(화주 설정 inbox).
import { useRouter } from "next/navigation";
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
import { CARDS } from "@/lib/text/reader";
import type { Shipment } from "@/lib/types/reader";

const U = HOME.upload;

export default function UploadPage() {
  const router = useRouter();
  const { shipperId, shipperName, error: shipperError } = useShipper();
  const [ships, setShips] = useState<Shipment[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState(false);
  const [folderId, setFolderId] = useState<string | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [inboxOn, setInboxOn] = useState(false);
  const [inboxMsg, setInboxMsg] = useState("");
  const [note, setNote] = useState("");

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

  const openUpload = (fid?: string) => {
    setFolderId(fid);
    setOpen(true);
  };
  const todo = ships?.filter((s) => s.next !== "done") ?? [];

  return (
    <div>
      <ListHeader title={T.side.list.upload} onChanged={() => load()} />
      {(shipperError ?? error) !== null && <ErrorLine error={shipperError ?? error} onRetry={load} />}
      {note && <Notice>{note}</Notice>}

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
              <button type="button" style={pillPrimary} onClick={() => openUpload()} disabled={!shipperId}>
                ⇪ {HOME.buttons.upload}
              </button>
            }
          />
        </Card>
      )}
      {ships && ships.length > 0 && (
        <>
          <div
            role="status"
            style={{
              fontSize: font.md,
              fontWeight: 700,
              margin: `${space.xs}px 0`,
              padding: `${space.sm}px ${space.md}px`,
              borderRadius: 12,
              background: todo.length ? colors.needCheckSoft : colors.okSoft,
              color: todo.length ? colors.text : colors.ok,
            }}
          >
            {CARDS.todo(todo.length, todo[0] ? CARDS.next[todo[0].next] : "")}
          </div>
          <ShipmentCards
            shipments={ships}
            shipperId={shipperId}
            onChanged={(msg) => {
              setNote(msg);
              load();
            }}
            onAddMore={(fid) => openUpload(fid)}
            onGo={(where, rowId) =>
              router.push(
                where === "review" ? `/history/review/${rowId ? `?row=${encodeURIComponent(rowId)}` : ""}` : "/history/",
              )
            }
          />
        </>
      )}

      {open && (
        <UploadDialog
          shipperId={shipperId}
          shipperName={shipperName}
          folderId={folderId}
          onClose={() => setOpen(false)}
          onUploaded={() => load()}
        />
      )}
    </div>
  );
}
