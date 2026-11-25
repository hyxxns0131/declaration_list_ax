"use client";
// 상단 바 (DESIGN 3-3): 화주 드롭다운 · 배지 · 버튼 4개(서류 올리기·품목사항 만들기·새로고침·설정). 담당: KHS
import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { colors, space } from "@/components/ui/tokens";
import { HOME } from "@/lib/text/home";
import { T } from "@/lib/text/common";
import type { Shipper } from "@/lib/types/core";
import type { Badges } from "@/lib/types/history";

export type HomeFilter = "all" | "attention" | "progress";

export function TopBar({
  shippers,
  shipperId,
  onShipper,
  badges,
  filter,
  onFilter,
  onUpload,
  onRefresh,
  refreshing,
  itemSheet,
}: {
  shippers: Shipper[];
  shipperId: string;
  onShipper: (id: string) => void;
  badges: Badges | null;
  filter: HomeFilter;
  onFilter: (f: HomeFilter) => void;
  onUpload: () => void;
  onRefresh: () => void;
  refreshing: boolean;
  itemSheet: ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap", marginBottom: space.sm }}>
      <label style={{ display: "flex", alignItems: "center", gap: space.xs }}>
        {T.shipper}
        <select
          value={shipperId}
          onChange={(e) => onShipper(e.target.value)}
          style={{ padding: space.xs, borderColor: shipperId ? colors.border : colors.primary, borderWidth: shipperId ? 1 : 2 }}
        >
          {!shipperId && <option value="">{T.pickShipper}</option>}
          {shippers.map((s) => (
            <option key={s.shipper_id} value={s.shipper_id}>
              {s.display_name}
            </option>
          ))}
        </select>
      </label>
      {badges && (
        <>
          <Badge
            tone={badges.need_check ? "needCheck" : "neutral"}
            active={filter === "attention"}
            onClick={() => onFilter(filter === "attention" ? "all" : "attention")}
            title="확인 필요·불일치·자료 추가 필요 행만 보기"
          >
            {HOME.badges.needCheck(badges.need_check)}
          </Badge>
          <Badge
            tone="info"
            active={filter === "progress"}
            onClick={() => onFilter(filter === "progress" ? "all" : "progress")}
            title="신청 전·승인 전 신고건만 보기"
          >
            {HOME.badges.inProgress(badges.in_progress)}
          </Badge>
          <Badge tone={badges.ready ? "ok" : "neutral"}>{HOME.badges.ready(badges.ready)}</Badge>
          {badges.mismatch > 0 && <Badge tone="mismatch">■ {HOME.badges.mismatch(badges.mismatch)}</Badge>}
          {badges.edited > 0 && <Badge tone="edited">✎ {HOME.badges.edited(badges.edited)}</Badge>}
        </>
      )}
      <span style={{ marginLeft: "auto", display: "flex", gap: space.sm, alignItems: "center" }}>
        <Button onClick={onUpload} disabled={!shipperId}>
          {HOME.buttons.upload}
        </Button>
        {itemSheet}
        <Button onClick={onRefresh} disabled={!shipperId || refreshing} title={HOME.buttons.refresh}>
          ⟳ {refreshing ? T.loading : HOME.buttons.refresh}
        </Button>
        <Link href="/settings/rules/" title={HOME.buttons.settings} style={{ fontSize: 18, textDecoration: "none" }}>
          ⚙
        </Link>
      </span>
    </div>
  );
}
