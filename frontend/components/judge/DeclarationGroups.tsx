"use client";
// 신고건 구분선 (DESIGN 3-1). 표 안에서 신고건 사이에 한 줄로 그린다 — 시트의 '빈 행 1개'. 담당: LSY
// 데이터(Declaration)는 홈이 lib/api/judge로 받아 넘긴다. 이 부품은 그리기·묶음 선택 이벤트만.
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate } from "@/lib/format";
import { HOME } from "@/lib/text/home";
import type { Declaration } from "@/lib/types/history";

export function GroupLine({
  index,
  decl,
  colSpan,
  onSelectGroup,
}: {
  index: number;
  decl: Declaration;
  colSpan: number;
  onSelectGroup: (rowIds: string[]) => void;
}) {
  const vessel = decl.key.vessel_key.replace(/^모선명:/, "");
  return (
    <tr>
      <td
        colSpan={colSpan}
        style={{ background: colors.bgSubtle, borderTop: `2px solid ${colors.border}`, padding: `${space.xs}px ${space.sm}px` }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: space.sm, flexWrap: "wrap", fontSize: font.sm }}>
          <strong>{HOME.groupLine(index, vessel, decl.key.factory_code, decl.key.material)}</strong>
          {decl.key.color && <Badge>{decl.key.color}</Badge>}
          {decl.arrival_date && <span style={{ color: colors.muted }}>반입 {fmtDate(decl.arrival_date)}</span>}
          {decl.record_nos.length > 0 && <span style={{ color: colors.muted }}>실적 {decl.record_nos.join(", ")}</span>}
          {decl.warnings.map((w) => (
            <Badge key={w} tone="needCheck" title={w}>
              ? {w}
            </Badge>
          ))}
          <Button small onClick={() => onSelectGroup(decl.row_ids)} style={{ marginLeft: "auto" }}>
            {HOME.selectGroup}
          </Button>
        </span>
      </td>
    </tr>
  );
}
