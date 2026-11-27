"use client";
// 기업 설정 › 규칙 설정 왼쪽 세로 화주 목록 (DESIGN 7장 와이어프레임, AGENTS 4-1 ShipperList).
// '＋ 화주 추가'는 화주 목록 뒤에 따로 그려 화주가 늘어도 항상 맨 아래에 있다. 담당: JUJ
import type { CSSProperties } from "react";

import { Card } from "@/components/ui/Card";
import { colors, font, radius, space } from "@/components/ui/tokens";
import { SETTINGS } from "@/lib/text/settings";
import type { Shipper } from "@/lib/types/core";

const item: CSSProperties = {
  display: "block",
  width: "100%",
  textAlign: "left",
  padding: `${space.sm}px ${space.sm + 4}px`,
  marginBottom: space.sm,
  border: `1px solid ${colors.border}`,
  borderRadius: radius,
  background: colors.bg,
  color: colors.text,
  fontSize: font.md,
  cursor: "pointer",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

export function ShipperList({
  shippers,
  current,
  onPick,
  onAdd,
}: {
  shippers: Shipper[];
  current: string;
  onPick: (id: string) => void;
  onAdd: () => void;
}) {
  return (
    <Card title={SETTINGS.list} style={{ marginBottom: 0 }}>
      <nav aria-label={SETTINGS.list}>
        {shippers.length === 0 && (
          <p style={{ fontSize: font.sm, color: colors.muted, marginTop: 0 }}>{SETTINGS.emptyList}</p>
        )}
        {shippers.map((s) => {
          const on = s.shipper_id === current;
          return (
            <button
              key={s.shipper_id}
              type="button"
              aria-pressed={on}
              title={s.display_name}
              onClick={() => onPick(s.shipper_id)}
              style={{
                ...item,
                ...(on
                  ? { background: colors.primarySoft, borderColor: colors.primary, color: colors.primary, fontWeight: 700 }
                  : null),
              }}
            >
              {s.display_name}
            </button>
          );
        })}
        <button
          type="button"
          onClick={onAdd}
          style={{ ...item, marginBottom: 0, borderStyle: "dashed", borderColor: colors.primary, color: colors.primary, fontWeight: 600 }}
        >
          {SETTINGS.add}
        </button>
      </nav>
    </Card>
  );
}
