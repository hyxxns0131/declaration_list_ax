"use client";
// 화주 고르기 드롭다운. 담당: 공통(KHS 관리)
import { colors, space } from "@/components/ui/tokens";
import { T } from "@/lib/text/common";
import type { Shipper } from "@/lib/types/core";

export function ShipperSelect({
  shippers,
  value,
  onChange,
}: {
  shippers: Shipper[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: space.xs }}>
      {T.shipper}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: space.xs, borderColor: value ? colors.border : colors.primary, background: colors.bg }}
      >
        {!value && <option value="">{T.pickShipper}</option>}
        {shippers.map((s) => (
          <option key={s.shipper_id} value={s.shipper_id}>
            {s.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
