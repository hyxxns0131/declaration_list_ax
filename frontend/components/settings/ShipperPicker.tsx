"use client";
// 탭 1. 기업 설정 첫 화면: 작업할 화주 고르기 · 새 화주 추가 · 화주 삭제(기본 A·B 제외) (DESIGN 7-0, HS 요청 11/25).
// 고른 화주는 모든 탭이 같이 쓴다(lib/hooks/useShipper). 담당: KHS(화면) · JUJ(화주 API)
import { useEffect, useState } from "react";

import { NewShipperDialog } from "@/components/settings/NewShipperDialog";
import { Button } from "@/components/ui/Button";
import { SectionTitle } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine } from "@/components/ui/StateBox";
import { cardRadius, colors, font, space } from "@/components/ui/tokens";
import { getBadges } from "@/lib/api/history";
import { deleteShipper } from "@/lib/api/settings";
import { SETTINGS } from "@/lib/text/settings";
import type { Shipper } from "@/lib/types/core";

/** 기본 화주: 삭제 버튼을 보이지 않는다(백엔드 a4_settings DEFAULT_SHIPPERS와 같게). */
export const DEFAULT_SHIPPERS = ["A", "B"];
const P = SETTINGS.pick;

export function ShipperPicker({
  shippers,
  current,
  chosen,
  onPick,
  onAdded,
  onDeleted,
}: {
  shippers: Shipper[];
  current: string;
  chosen: boolean;
  onPick: (id: string) => void;
  onAdded: (id: string) => void;
  onDeleted: (s: Shipper) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Shipper | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [rows, setRows] = useState<Record<string, number>>({});

  // 카드에 붙일 짧은 정보: 검역이력 행 수 (화주마다 한 번씩)
  useEffect(() => {
    let alive = true;
    for (const s of shippers) {
      getBadges(s.shipper_id)
        .then((b) => alive && setRows((r) => ({ ...r, [s.shipper_id]: b.total })))
        .catch(() => undefined);
    }
    return () => {
      alive = false;
    };
  }, [shippers]);

  const remove = async () => {
    if (!removing) return;
    setBusy(true);
    setError(null);
    try {
      await deleteShipper(removing.shipper_id);
      const gone = removing;
      setRemoving(null);
      onDeleted(gone);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const tile = (on: boolean) =>
    ({
      textAlign: "left",
      border: on ? `2px solid ${colors.primary}` : `2px solid ${colors.cardBorder}`,
      borderRadius: cardRadius,
      padding: `${space.md + 2}px ${space.md + 4}px`,
      minHeight: 120,
      cursor: "pointer",
      background: on ? colors.primarySoft : colors.surface,
      color: colors.text,
      boxShadow: colors.cardShadow,
      display: "flex",
      flexDirection: "column",
      gap: space.xs,
      font: "inherit",
      width: "100%",
    }) as const;

  return (
    <section style={{ marginBottom: space.lg }}>
      <SectionTitle>{P.title}</SectionTitle>
      <p style={{ margin: `-${space.xs}px 0 ${space.md}px`, fontSize: font.sm, color: colors.muted }}>
        {chosen ? P.subChosen : P.sub}
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))", gap: space.md }}>
        {shippers.map((s) => {
          const on = chosen && s.shipper_id === current;
          const muted = colors.muted;
          const locked = DEFAULT_SHIPPERS.includes(s.shipper_id.toUpperCase());
          return (
            <div key={s.shipper_id} style={{ position: "relative" }}>
              <button type="button" aria-pressed={on} onClick={() => onPick(s.shipper_id)} style={tile(on)}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: muted }}>
                  {on ? P.selected : P.choose}
                </span>
                <span style={{ fontSize: font.xl, fontWeight: 800 }}>{s.display_name}</span>
                <span style={{ fontSize: font.sm, color: muted, marginTop: "auto" }} title={locked ? P.defaultLocked : undefined}>
                  {`ID ${s.shipper_id}`}
                  {rows[s.shipper_id] !== undefined && ` · ${P.rows(rows[s.shipper_id])}`}
                  {locked && ` · ${P.defaultTag}`}
                </span>
              </button>
              {!locked && (
                <button
                  type="button"
                  aria-label={`${s.display_name} ${P.remove}`}
                  title={`${s.display_name} ${P.remove}`}
                  onClick={() => setRemoving(s)}
                  style={{
                    position: "absolute",
                    top: space.sm,
                    right: space.sm,
                    border: 0,
                    borderRadius: 8,
                    padding: `2px ${space.sm}px`,
                    fontSize: font.sm,
                    cursor: "pointer",
                    background: colors.bg,
                    color: colors.mismatch,
                  }}
                >
                  {P.remove}
                </button>
              )}
            </div>
          );
        })}
        <button
          type="button"
          onClick={() => setAdding(true)}
          style={{
            ...tile(false),
            background: colors.bg,
            border: `2px dashed ${colors.primary}`,
            color: colors.brand,
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "none",
          }}
        >
          <span style={{ fontSize: 28, lineHeight: 1 }}>＋</span>
          <span style={{ fontWeight: 700 }}>{P.add}</span>
        </button>
      </div>

      {adding && (
        <NewShipperDialog
          existingIds={shippers.map((s) => s.shipper_id)}
          onClose={() => setAdding(false)}
          onCreated={(id) => {
            setAdding(false);
            onAdded(id);
          }}
        />
      )}

      {removing && (
        <Modal
          title={P.removeTitle}
          onClose={() => setRemoving(null)}
          width={440}
          footer={
            <>
              <Button onClick={() => setRemoving(null)}>{SETTINGS.newShipper.cancel}</Button>
              <Button variant="danger" onClick={remove} disabled={busy}>
                {busy ? P.removing : P.remove}
              </Button>
            </>
          }
        >
          <p style={{ marginTop: 0, fontWeight: 600 }}>{P.removeAsk(removing.display_name)}</p>
          <p style={{ fontSize: font.sm, color: colors.muted }}>{P.removeNote}</p>
          {error !== null && <ErrorLine error={error} />}
        </Modal>
      )}
    </section>
  );
}
