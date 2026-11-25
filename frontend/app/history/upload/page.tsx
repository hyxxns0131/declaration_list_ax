"use client";
// 탭 4. 검역 리스트 › 서류 올리기 (DESIGN 3-1-1). 올리기 대화상자를 열고 결과 행으로 안내한다. 담당: KHS
import Link from "next/link";
import { useState } from "react";

import { UploadDialog } from "@/components/reader/UploadDialog";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { ErrorLine, Notice } from "@/components/ui/StateBox";
import { font, space } from "@/components/ui/tokens";
import { useShipper } from "@/lib/hooks/useShipper";
import { HOME } from "@/lib/text/home";

const U = HOME.upload;

export default function UploadPage() {
  const { shippers, shipperId, setShipperId, shipperName, error } = useShipper();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [rowIds, setRowIds] = useState<string[] | null>(null);
  const [active, setActive] = useState<string | null>(null);

  return (
    <div>
      <PageHeader title={U.title} sub={U.sub} actions={<ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />} />
      {error !== null && <ErrorLine error={error} />}
      <Card>
        <ol style={{ margin: `0 0 ${space.md}px`, paddingLeft: space.lg, fontSize: font.md }}>
          {U.steps.map((s) => (
            <li key={s} style={{ marginBottom: space.xs }}>
              {s}
            </li>
          ))}
        </ol>
        <Button variant="primary" disabled={!shipperId || busy} onClick={() => setOpen(true)}>
          {busy ? "판독 중…" : HOME.buttons.upload}
        </Button>
      </Card>
      {rowIds && (
        <Notice>
          {U.done(rowIds.length)} · <Link href="/history/">{U.goTable}</Link>
        </Notice>
      )}
      {open && (
        <UploadDialog
          shipperId={shipperId}
          shipperName={shipperName}
          onClose={() => setOpen(false)}
          onStart={() => setBusy(true)}
          onEnd={() => setBusy(false)}
          onUploaded={(ids) => {
            setRowIds(ids);
            if (ids[0]) setActive(ids[0]);
          }}
        />
      )}
      {active && <ReviewPanel rowId={active} onConfirmed={() => undefined} onClose={() => setActive(null)} />}
    </div>
  );
}
