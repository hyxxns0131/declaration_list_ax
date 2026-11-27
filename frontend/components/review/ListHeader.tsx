"use client";
// 검역 리스트 탭 공통 머리 (세 화면 공통): 제목 · 화주 선택 · 배지(자료 추가 필요·불일치·검수 대기·사람이 고름)
// · 주 버튼 [서류 올리기](대화상자) · 보조 버튼 [새로고침] · 품목사항 엑셀(탭 5)·설정 링크. 아래에 단계 표시줄.
// 품목사항은 이 탭에서 만들지 않는다(탭 5). 담당: KHS (검역 리스트 탭 0단계, HS 요청 11/26)
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { UploadDialog } from "@/components/reader/UploadDialog";
import { ListStepper } from "@/components/review/ListStepper";
import { STATE_STYLE, pillDisabled, pillPrimary, pillSecondary } from "@/components/review/listUi";
import { notifyListChanged } from "@/components/review/useListSteps";
import { ShipperSelect } from "@/components/ui/ShipperSelect";
import { colors, font, space } from "@/components/ui/tokens";
import { getBadges, refreshHistory } from "@/lib/api/history";
import { useShipper } from "@/lib/hooks/useShipper";
import { T } from "@/lib/text/common";
import { HOME } from "@/lib/text/home";
import type { Badges } from "@/lib/types/history";

export type BadgeFilter = "need_input" | "mismatch" | "review" | "manual";

const BADGES: { key: BadgeFilter; count: (b: Badges) => number; style: (typeof STATE_STYLE)[keyof typeof STATE_STYLE] }[] = [
  { key: "need_input", count: (b) => b.need_input, style: STATE_STYLE.needInput },
  { key: "mismatch", count: (b) => b.mismatch, style: STATE_STYLE.mismatch },
  { key: "review", count: (b) => b.review_waiting, style: STATE_STYLE.review },
  { key: "manual", count: (b) => b.manual, style: STATE_STYLE.manual },
];

export function ListHeader({
  title,
  filter,
  onFilter,
  onChanged,
  onMessage,
  showBadges = true,
}: {
  title: string;
  /** ② 화면은 배지 줄을 빼고 미해결/해결됨/전체 한 줄만 쓴다(HS 11/27) */
  showBadges?: boolean;
  /** 배지를 눌러 행을 거르는 화면(③)만 준다 */
  filter?: BadgeFilter | null;
  onFilter?: (f: BadgeFilter | null) => void;
  /** 서류 올리기·새로고침 뒤 화면 데이터를 다시 읽기 */
  onChanged?: (rowIds?: string[]) => void;
  onMessage?: (text: string) => void;
}) {
  const { shippers, shipperId, setShipperId, shipperName } = useShipper();
  const [badges, setBadges] = useState<Badges | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [busy, setBusy] = useState<"" | "upload" | "refresh">("");

  const load = useCallback(() => {
    if (!shipperId) return;
    getBadges(shipperId).then(setBadges).catch(() => setBadges(null));
  }, [shipperId]);
  useEffect(load, [load]);
  useEffect(() => {
    window.addEventListener("dl-list-changed", load);
    return () => window.removeEventListener("dl-list-changed", load);
  }, [load]);

  const refresh = async () => {
    setBusy("refresh");
    try {
      const out = await refreshHistory(shipperId);
      onMessage?.(HOME.refreshDone(out.rows, out.bls));
      notifyListChanged();
      onChanged?.();
    } catch {
      onMessage?.(T.networkError);
    } finally {
      setBusy("");
    }
  };

  return (
    <header style={{ marginBottom: space.xs }}>
      <div style={{ display: "flex", alignItems: "center", gap: space.md, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: colors.brand }}>{title}</h1>
        <ShipperSelect shippers={shippers} value={shipperId} onChange={setShipperId} />
        <span style={{ display: "flex", gap: space.xs + 2, flexWrap: "wrap" }}>
          {badges &&
            showBadges &&
            BADGES.map((b) => {
              const n = b.count(badges);
              const on = filter === b.key;
              const style = {
                border: `1px solid ${on ? b.style.color : "transparent"}`,
                background: b.style.bg,
                color: b.style.color,
                borderRadius: 999,
                padding: `3px ${space.sm + 2}px`,
                fontSize: font.sm,
                fontWeight: 700,
                fontVariantNumeric: "tabular-nums" as const,
                cursor: onFilter ? "pointer" : "default",
              };
              return onFilter ? (
                <button
                  key={b.key}
                  type="button"
                  aria-pressed={on}
                  onClick={() => onFilter(on ? null : b.key)}
                  style={style}
                >
                  {b.style.text} {n}
                </button>
              ) : (
                <span key={b.key} style={style}>
                  {b.style.text} {n}
                </span>
              );
            })}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", gap: space.sm, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => setUploadOpen(true)}
            disabled={!shipperId || busy !== ""}
            style={{ ...pillPrimary, ...(!shipperId || busy ? pillDisabled : {}) }}
          >
            ⇪ {busy === "upload" ? "판독 중…" : HOME.buttons.upload}
          </button>
          <button
            type="button"
            onClick={refresh}
            disabled={!shipperId || busy !== ""}
            style={{ ...pillSecondary, ...(!shipperId || busy ? pillDisabled : {}) }}
          >
            ⟳ {busy === "refresh" ? T.loading : HOME.buttons.refresh}
          </button>
          <Link href="/item-sheet/" style={{ fontSize: font.sm, color: colors.brand }}>
            {HOME.bar.itemSheetLink}
          </Link>
          <Link href="/settings/rules/" style={{ fontSize: font.sm, color: colors.muted }}>
            ⚙ {HOME.buttons.settings}
          </Link>
        </span>
      </div>
      <ListStepper />
      {uploadOpen && (
        <UploadDialog
          shipperId={shipperId}
          shipperName={shipperName}
          onClose={() => setUploadOpen(false)}
          onStart={() => setBusy("upload")}
          onEnd={() => setBusy("")}
          onUploaded={(ids) => {
            notifyListChanged();
            onChanged?.(ids);
          }}
        />
      )}
    </header>
  );
}
