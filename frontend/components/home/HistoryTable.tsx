"use client";
// 검역이력 표 (DESIGN 3-2). 열 이름·순서는 시트 그대로. 신고건 사이에 구분선. 담당: KHS
// props: rows, selected → onSelect·onEdit·onOpenReview. 데이터를 만들지 않고 받은 것만 그린다.
import type { CSSProperties } from "react";

import { GroupLine } from "@/components/judge/DeclarationGroups";
import { kindOf } from "@/components/judge/JudgeEvidence";
import { Badge, type Tone } from "@/components/ui/Badge";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtCell, shown } from "@/lib/format";
import { HOME } from "@/lib/text/home";
import type { Declaration, Field, HistoryRow, RowStatus } from "@/lib/types/history";

const STATUS_TONE: Record<RowStatus, Tone> = {
  "자료 추가 필요": "needInput",
  "확인 필요": "needCheck",
  "반입 전": "neutral",
  "신청 전": "ok",
  승인: "neutral",
};
const NOT_EDITABLE = new Set(["가격(USD)", "USD 환율", "CI 통화 환율"]);

function cellStyle(f: Field | undefined, locked: boolean): { style: CSSProperties; mark: string; title: string } {
  if (locked) return { style: { color: colors.approved }, mark: "", title: HOME.locked };
  if (!f) return { style: {}, mark: "", title: "" };
  switch (f.flag) {
    case "mismatch":
      return { style: { color: colors.mismatch, background: colors.mismatchSoft, fontWeight: 600 }, mark: "■ ", title: f.memo || "서류와 다름" };
    case "edited":
      return { style: { color: colors.edited, background: colors.editedSoft, fontWeight: 600 }, mark: "✎ ", title: f.memo || "담당자가 고친 값이 서류와 다름" };
    case "need_input":
      return { style: { background: colors.needInput, color: colors.needInputText }, mark: "", title: "자료 추가 필요" };
    case "need_check":
      return { style: { color: colors.needCheck, background: colors.needCheckSoft }, mark: "? ", title: f.memo || "확인 필요" };
    default:
      return { style: {}, mark: "", title: f.memo };
  }
}

function shortLabel(col: string): string {
  return col.split(" (")[0];
}

export function HistoryTable({
  rows,
  columns,
  declarations,
  selected,
  activeRowId,
  onSelect,
  onSelectGroup,
  onOpenReview,
  onEdit,
  onOpenEvidence,
  onMove,
}: {
  rows: HistoryRow[];
  columns: string[];
  declarations: Declaration[];
  selected: Set<string>;
  activeRowId: string | null;
  onSelect: (rowId: string, on: boolean) => void;
  onSelectGroup: (rowIds: string[]) => void;
  onOpenReview: (rowId: string) => void;
  onEdit: (row: HistoryRow, column: string) => void;
  onOpenEvidence: (row: HistoryRow, column: string) => void;
  onMove: (rowId: string, dir: -1 | 1) => void;
}) {
  const byId = new Map(rows.map((r) => [r.row_id, r]));
  const used = new Set<string>();
  const sections: { decl: Declaration | null; rows: HistoryRow[] }[] = [];
  for (const d of declarations) {
    const rs = d.row_ids.map((id) => byId.get(id)).filter((r): r is HistoryRow => Boolean(r));
    rs.forEach((r) => used.add(r.row_id));
    if (rs.length) sections.push({ decl: d, rows: rs });
  }
  const rest = rows.filter((r) => !used.has(r.row_id));
  if (rest.length) sections.push({ decl: null, rows: rest });
  const colSpan = columns.length + 3;
  let declNo = 0;

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="grid sheet">
        <thead>
          <tr>
            <th style={{ width: 28 }} aria-label="선택" />
            <th>{HOME.status}</th>
            {columns.map((c) => (
              <th key={c} title={c}>
                {shortLabel(c)}
              </th>
            ))}
            <th aria-label="행 이동" />
          </tr>
        </thead>
        <tbody>
          {sections.map((sec, si) => {
            if (sec.decl) declNo += 1;
            return [
              sec.decl ? (
                <GroupLine
                  key={`g-${sec.decl.declaration_id}`}
                  index={declNo}
                  decl={sec.decl}
                  colSpan={colSpan}
                  onSelectGroup={onSelectGroup}
                />
              ) : (
                <tr key={`g-rest-${si}`}>
                  <td colSpan={colSpan} style={{ background: colors.bgSubtle, fontSize: font.sm, padding: space.xs }}>
                    승인·기타
                  </td>
                </tr>
              ),
              ...sec.rows.map((r) => {
                const locked = r.status === "승인";
                const active = r.row_id === activeRowId;
                return (
                  <tr
                    key={r.row_id}
                    onClick={() => onOpenReview(r.row_id)}
                    style={{
                      background: active ? colors.primarySoft : undefined,
                      color: locked ? colors.approved : undefined,
                      cursor: "pointer",
                    }}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label="행 선택"
                        checked={selected.has(r.row_id)}
                        onChange={(e) => onSelect(r.row_id, e.target.checked)}
                      />
                    </td>
                    <td>
                      <Badge tone={STATUS_TONE[r.status]}>
                        {locked ? "🔒 " : ""}
                        {r.status}
                      </Badge>
                      {r.confirmed && (
                        <span style={{ fontSize: font.sm, color: colors.ok }} title={HOME.confirmedMark}>
                          {" "}✓
                        </span>
                      )}
                    </td>
                    {columns.map((c) => {
                      const f = r.cells[c];
                      const v = shown(f);
                      const st = cellStyle(f, locked);
                      const judge = kindOf(c) !== null;
                      const editable = !locked && !NOT_EDITABLE.has(c);
                      const text = fmtCell(c, v);
                      return (
                        <td
                          key={c}
                          title={NOT_EDITABLE.has(c) ? HOME.computed : st.title || (editable ? HOME.editHint : "")}
                          style={{ ...st.style, whiteSpace: c === "비고" ? "pre-line" : undefined }}
                          onDoubleClick={(e) => {
                            e.stopPropagation();
                            if (editable) onEdit(r, c);
                          }}
                        >
                          {st.mark}
                          {text}
                          {c === "한글 제품명(모델넘버)" && r.part_lines.length > 0 && (
                            <span title={r.part_lines.join("\n")} style={{ color: colors.muted, fontSize: font.sm }}>
                              {" "}({r.part_lines.length}줄)
                            </span>
                          )}
                          {judge && (
                            <button
                              type="button"
                              aria-label="판단 근거 보기"
                              title="판단 근거 보기"
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenEvidence(r, c);
                              }}
                              style={{ border: "none", background: "none", color: colors.primary, cursor: "pointer", padding: "0 2px" }}
                            >
                              ⓘ
                            </button>
                          )}
                        </td>
                      );
                    })}
                    <td onClick={(e) => e.stopPropagation()} style={{ whiteSpace: "nowrap" }}>
                      <button type="button" className="mini" title={HOME.moveUp} onClick={() => onMove(r.row_id, -1)}>
                        ↑
                      </button>
                      <button type="button" className="mini" title={HOME.moveDown} onClick={() => onMove(r.row_id, 1)}>
                        ↓
                      </button>
                    </td>
                  </tr>
                );
              }),
            ];
          })}
        </tbody>
      </table>
    </div>
  );
}
