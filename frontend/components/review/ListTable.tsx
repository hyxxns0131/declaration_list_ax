"use client";
// 화면 ③ 완성된 검역 리스트 표 (검역 리스트 탭 4단계). components/home/HistoryTable을 바탕으로 넓힘(그 파일은 그대로 둔다).
// - 칸 묶음 머리줄(서류·운송·제품·가격·등록 정보·진행), 머리글·왼쪽 칸(체크·상태·B/L·한글 제품명) 고정, 줄무늬, 행 높이 36px 이상
// - 값 출처 표시: 사람이 고른·고친 값 = 주황 ✎, 등록 정보(수입신고필증·시험성적서·규칙·이력)로 채운 값 = 파란 점,
//   서류끼리 달라 비워 둔 값 = 빨간 [검수 필요] → ② 서류 대조·검수 그 행으로
// - 신고건 구분선, 칸 두 번 눌러 고치기(final_value), 승인 행 잠금
// 데이터를 만들지 않고 받은 것만 그린다. 담당: KHS
import type { CSSProperties, ReactNode } from "react";

import { GroupLine } from "@/components/judge/DeclarationGroups";
import { kindOf } from "@/components/judge/JudgeEvidence";
import { LIST_BLUE, STATE_STYLE } from "@/components/review/listUi";
import { Badge, type Tone } from "@/components/ui/Badge";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtCell, shown } from "@/lib/format";
import { HOME } from "@/lib/text/home";
import type { Declaration, Field, HistoryRow, RowStatus } from "@/lib/types/history";

const L = HOME.listTable;

const STATUS_TONE: Record<RowStatus, Tone> = {
  "자료 추가 필요": "needInput",
  "확인 필요": "needCheck",
  "반입 전": "neutral",
  "신청 전": "ok",
  승인: "neutral",
};
const NOT_EDITABLE = new Set(["가격(USD)", "USD 환율", "CI 통화 환율"]);
const NAME_COL = "한글 제품명(모델넘버)";
const BL_COL = "B/L Number";

/** 칸 묶음. 화면에서만 묶어 보이고, 시트·품목사항 엑셀의 열 순서는 그대로다 */
const GROUPS: { key: string; label: string; cols: string[] }[] = [
  { key: "doc", label: "서류", cols: [BL_COL] },
  { key: "ship", label: "운송", cols: ["모선명", "반입지 코드", "반입일", "입항일", "선적일", "도착항 코드", "선적항 코드", "화물관리번호"] },
  { key: "product", label: "제품", cols: [NAME_COL, "제조사", "영문 제품명", "입수", "카톤 수", "순중량"] },
  { key: "price", label: "가격", cols: ["가격(USD)", "USD 환율", "CI 통화", "가격(수출국)", "CI 통화 환율"] },
  {
    key: "registry",
    label: "등록 정보",
    cols: ["재질 (재질 코드명으로 작성, 가나다 순으로 기재)", "색상", "재질 구분 (깊이·용량·용도)", "실적접수번호 (승인일)"],
  },
  { key: "progress", label: "진행", cols: ["검역 신고일자", "승인번호", "비고"] },
];
const GROUP_OF = new Map(GROUPS.flatMap((g) => g.cols.map((c) => [c, g.key] as const)));
const REGISTRY_SOURCES = new Set(["IMPORT_DECL", "TEST_REPORT", "RULE", "HISTORY"]);

/** 왼쪽 고정 칸 너비(px): 체크, 상태, B/L, 한글 제품명 */
const W_CHECK = 34;
const W_STATUS = 116;
const W_BL = 136;
const W_NAME = 230;
const LEFT = { check: 0, status: W_CHECK, bl: W_CHECK + W_STATUS, name: W_CHECK + W_STATUS + W_BL };
const HEAD_H = 30;
const ROW_H = 38;

type Origin = "manual" | "registry" | "blocked" | "needInput" | "check" | "plain";

function originOf(f: Field | undefined, col: string): Origin {
  if (!f) return "plain";
  const v = shown(f);
  if (f.flag === "mismatch" && (v === null || v === undefined || v === "")) return "blocked";
  if (f.final_value !== null && f.final_value !== undefined) return "manual";
  if (f.evidence.some((e) => e.source === "MANUAL")) return "manual";
  if (f.flag === "need_input") return "needInput";
  if (f.flag === "mismatch" || f.flag === "need_check") return "check";
  if (GROUP_OF.get(col) === "registry" || col === "제조사") {
    if (f.evidence.some((e) => REGISTRY_SOURCES.has(e.source))) return "registry";
  }
  return "plain";
}

function shortLabel(col: string): string {
  return col.split(" (")[0];
}

function stickyCell(left: number, width: number, bg: string, extra: CSSProperties = {}): CSSProperties {
  return { position: "sticky", left, width, minWidth: width, maxWidth: width, background: bg, zIndex: 1, ...extra };
}

export function ListTable({
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
  maxHeight,
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
  maxHeight?: string;
}) {
  // 고정 칸(B/L·한글 제품명)은 왼쪽으로 빼고, 나머지는 칸 묶음 순서로
  const rest = columns.filter((c) => c !== BL_COL && c !== NAME_COL);
  const order = GROUPS.map((g) => g.key);
  const sorted = [...rest].sort((a, b) => order.indexOf(GROUP_OF.get(a) ?? "progress") - order.indexOf(GROUP_OF.get(b) ?? "progress"));
  const runs: { label: string; span: number }[] = [];
  for (const c of sorted) {
    const g = GROUPS.find((x) => x.key === (GROUP_OF.get(c) ?? "progress"));
    const label = g?.label ?? "";
    const last = runs[runs.length - 1];
    if (last && last.label === label) last.span += 1;
    else runs.push({ label, span: 1 });
  }

  const byId = new Map(rows.map((r) => [r.row_id, r]));
  const used = new Set<string>();
  const sections: { decl: Declaration | null; rows: HistoryRow[] }[] = [];
  for (const d of declarations) {
    const rs = d.row_ids.map((id) => byId.get(id)).filter((r): r is HistoryRow => Boolean(r));
    rs.forEach((r) => used.add(r.row_id));
    if (rs.length) sections.push({ decl: d, rows: rs });
  }
  const others = rows.filter((r) => !used.has(r.row_id));
  if (others.length) sections.push({ decl: null, rows: others });
  const colSpan = sorted.length + 5;
  let declNo = 0;
  let zebra = 0;

  const th: CSSProperties = {
    position: "sticky",
    top: HEAD_H,
    zIndex: 2,
    background: colors.bgSubtle,
    fontSize: font.sm,
    fontWeight: 700,
    textAlign: "left",
    padding: `6px ${space.sm}px`,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: "nowrap",
  };
  const groupTh: CSSProperties = {
    ...th,
    top: 0,
    height: HEAD_H,
    color: colors.muted,
    fontWeight: 600,
    borderBottom: `1px solid ${colors.border}`,
  };
  const td: CSSProperties = {
    padding: `0 ${space.sm}px`,
    height: ROW_H,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: "nowrap",
    maxWidth: 260,
    overflow: "hidden",
    textOverflow: "ellipsis",
    fontSize: 13,
  };

  const renderCell = (r: HistoryRow, c: string, locked: boolean, bg: string, sticky?: CSSProperties) => {
    const f = r.cells[c];
    const origin = locked ? "plain" : originOf(f, c);
    const text = fmtCell(c, shown(f));
    const editable = !locked && !NOT_EDITABLE.has(c);
    const judge = kindOf(c) !== null;
    let style: CSSProperties = { ...td, background: bg, ...sticky };
    let mark: ReactNode = null;
    let tip = f?.memo ?? "";
    if (locked) style = { ...style, color: colors.approved };
    else if (origin === "manual") {
      style = { ...style, color: colors.edited, background: colors.editedSoft, fontWeight: 600 };
      mark = "✎ ";
      tip = tip || L.manual;
    } else if (origin === "needInput") {
      style = { ...style, color: colors.needInputText, background: colors.needInput };
      tip = tip || STATE_STYLE.needInput.text;
    } else if (origin === "check") {
      style = { ...style, color: colors.needCheck, background: colors.needCheckSoft };
      mark = "? ";
    } else if (origin === "registry") {
      mark = <span aria-label={L.registry} title={L.registry} style={{ display: "inline-block", width: 7, height: 7, borderRadius: 999, background: LIST_BLUE, marginRight: 5, verticalAlign: "middle" }} />;
      tip = tip || L.registry;
    }
    return (
      <td
        key={c}
        style={style}
        title={[text, NOT_EDITABLE.has(c) ? HOME.computed : tip || (editable ? HOME.editHint : ""), locked ? HOME.locked : ""].filter(Boolean).join(" · ")}
        onDoubleClick={(e) => {
          e.stopPropagation();
          if (editable) onEdit(r, c);
        }}
      >
        {origin === "blocked" ? (
          <button
            type="button"
            aria-label={`${shortLabel(c)} 검수 필요`}
            onClick={(e) => {
              e.stopPropagation();
              onOpenReview(r.row_id);
            }}
            title={f?.memo || L.blockedTip}
            style={{ color: colors.mismatch, background: colors.mismatchSoft, fontWeight: 700, fontSize: 12, borderRadius: 999, padding: "2px 8px", border: 0, cursor: "pointer" }}
          >
            ■ {L.blocked}
          </button>
        ) : (
          <>
            {mark}
            {text}
          </>
        )}
        {c === NAME_COL && r.cells["모델"]?.flag === "mismatch" && (
          <button type="button" onClick={() => onOpenReview(r.row_id)}>모델 검수 필요</button>
        )}
        {c === NAME_COL && r.model && !text.includes(r.model) && (
          <span style={{ marginLeft: 4 }}>{r.model}</span>
        )}
        {c === NAME_COL && r.part_lines.length > 0 && (
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
  };

  return (
    <div style={{ overflow: "auto", maxHeight: maxHeight ?? "none", border: `1px solid ${colors.border}`, borderRadius: 12, background: "#fff" }}>
      <table style={{ borderCollapse: "separate", borderSpacing: 0, minWidth: "100%" }}>
        <thead>
          <tr>
            <th colSpan={4} style={{ ...groupTh, ...stickyCell(0, W_NAME + LEFT.name, colors.bgSubtle, { zIndex: 4, top: 0 }) }}>
              {L.fixed}
            </th>
            {runs.map((g, i) => (
              <th key={`${g.label}-${i}`} colSpan={g.span} style={{ ...groupTh, borderLeft: `2px solid ${colors.border}` }}>
                {g.label}
              </th>
            ))}
            <th style={groupTh} />
          </tr>
          <tr>
            <th style={{ ...th, ...stickyCell(LEFT.check, W_CHECK, colors.bgSubtle, { zIndex: 4, top: HEAD_H }) }} aria-label="선택" />
            <th style={{ ...th, ...stickyCell(LEFT.status, W_STATUS, colors.bgSubtle, { zIndex: 4, top: HEAD_H }) }}>{HOME.status}</th>
            <th style={{ ...th, ...stickyCell(LEFT.bl, W_BL, colors.bgSubtle, { zIndex: 4, top: HEAD_H }) }}>B/L</th>
            <th style={{ ...th, ...stickyCell(LEFT.name, W_NAME, colors.bgSubtle, { zIndex: 4, top: HEAD_H, boxShadow: `2px 0 0 ${colors.border}` }) }}>
              {shortLabel(NAME_COL)}
            </th>
            {sorted.map((c, i) => {
              const first = i === 0 || GROUP_OF.get(sorted[i - 1]) !== GROUP_OF.get(c);
              return (
                <th key={c} title={c} style={{ ...th, borderLeft: first ? `2px solid ${colors.border}` : undefined }}>
                  {shortLabel(c)}
                </th>
              );
            })}
            <th style={th} aria-label="행 이동" />
          </tr>
        </thead>
        <tbody>
          {sections.map((sec, si) => {
            if (sec.decl) declNo += 1;
            return [
              sec.decl ? (
                <GroupLine key={`g-${sec.decl.declaration_id}`} index={declNo} decl={sec.decl} colSpan={colSpan} onSelectGroup={onSelectGroup} />
              ) : (
                <tr key={`g-rest-${si}`}>
                  <td colSpan={colSpan} style={{ background: colors.bgSubtle, fontSize: font.sm, padding: space.xs, borderTop: `2px solid ${colors.border}` }}>
                    {L.restGroup}
                  </td>
                </tr>
              ),
              ...sec.rows.map((r) => {
                const locked = r.status === "승인";
                const active = r.row_id === activeRowId;
                zebra += 1;
                const bg = active ? colors.primarySoft : zebra % 2 === 0 ? "#f8fafc" : "#fff";
                return (
                  <tr key={r.row_id} onClick={() => onOpenReview(r.row_id)} style={{ cursor: "pointer", color: locked ? colors.approved : undefined }}>
                    <td style={{ ...td, ...stickyCell(LEFT.check, W_CHECK, bg) }} onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" aria-label="행 선택" checked={selected.has(r.row_id)} onChange={(e) => onSelect(r.row_id, e.target.checked)} />
                    </td>
                    <td style={{ ...td, ...stickyCell(LEFT.status, W_STATUS, bg) }}>
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
                    {renderCell(r, BL_COL, locked, bg, stickyCell(LEFT.bl, W_BL, bg))}
                    {renderCell(r, NAME_COL, locked, bg, stickyCell(LEFT.name, W_NAME, bg, { boxShadow: `2px 0 0 ${colors.border}` }))}
                    {sorted.map((c) => renderCell(r, c, locked, bg))}
                    <td style={{ ...td, background: bg }} onClick={(e) => e.stopPropagation()}>
                      {!locked && (
                        <>
                          <button type="button" className="mini" title={HOME.moveUp} onClick={() => onMove(r.row_id, -1)}>
                            ↑
                          </button>
                          <button type="button" className="mini" title={HOME.moveDown} onClick={() => onMove(r.row_id, 1)}>
                            ↓
                          </button>
                        </>
                      )}
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
