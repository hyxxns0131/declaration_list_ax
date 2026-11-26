"use client";
// 화면 ① 선적 건 카드 목록: B/L 번호, 받은 서류 칩(CI·PL·B/L, 빠진 것은 노랑 '없음'), 추출 상태.
// 카드를 펼치면 서류별 추출값 표(서류 3개를 열로). 데이터는 GET /reader/shipments. 담당: KHS (검역 리스트 탭 1단계)
import { useState } from "react";

import { LIST_BLUE } from "@/components/review/listUi";
import { colors, font, space } from "@/components/ui/tokens";
import { openDocument } from "@/lib/api/reader";
import { fmtNumber } from "@/lib/format";
import { DOC_LABELS } from "@/lib/text/reader";
import type { Shipment, ShipmentDoc } from "@/lib/types/reader";

const COLS = ["CI", "PL", "BL"] as const;
const FIELDS: { key: keyof ShipmentDoc["values"]; label: string; num?: boolean }[] = [
  { key: "bl_no", label: "B/L 번호" },
  { key: "invoice_no", label: "인보이스 번호" },
  { key: "doc_date", label: "서류 날짜" },
  { key: "vessel", label: "모선" },
  { key: "manufacturer_name", label: "제조사" },
  { key: "currency", label: "통화" },
  { key: "total_amount", label: "총 금액", num: true },
  { key: "total_cartons", label: "총 카톤", num: true },
  { key: "total_gross_kg", label: "총중량(kg)", num: true },
  { key: "line_count", label: "품목 줄 수", num: true },
];
const STATUS_COLOR: Record<Shipment["status"], { fg: string; bg: string }> = {
  "추출 완료": { fg: colors.ok, bg: colors.okSoft },
  "확인 필요": { fg: colors.needCheck, bg: colors.needCheckSoft },
  "자료 추가 필요": { fg: colors.needInputText, bg: colors.needInput },
};
const num = { textAlign: "right" as const, fontVariantNumeric: "tabular-nums" as const };

function Chip({ type, doc }: { type: string; doc?: ShipmentDoc }) {
  const ok = Boolean(doc);
  return (
    <span
      title={doc ? `${doc.filename}${doc.warnings.length ? ` · ${doc.warnings.join(", ")}` : ""}` : `${DOC_LABELS[type] ?? type} 없음`}
      style={{
        borderRadius: 999,
        padding: `2px ${space.sm + 2}px`,
        fontSize: font.sm,
        fontWeight: 700,
        background: ok ? colors.primarySoft : colors.needInput,
        color: ok ? LIST_BLUE : colors.needInputText,
      }}
    >
      {type === "BL" ? "B/L" : type} {ok ? (doc?.warnings.length ? "?" : "✓") : "없음"}
    </span>
  );
}

export function ShipmentCards({ shipments }: { shipments: Shipment[] }) {
  const [open, setOpen] = useState<string | null>(shipments[0]?.bl_no ?? null);
  return (
    <div style={{ display: "grid", gap: space.sm }}>
      {shipments.map((s) => {
        const key = s.bl_no || s.folder_ids.join(",");
        const isOpen = open === key;
        const st = STATUS_COLOR[s.status];
        return (
          <section key={key} style={{ background: colors.cardBg, borderRadius: 16, padding: `${space.sm + 4}px ${space.md}px` }}>
            <button
              type="button"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : key)}
              style={{ display: "flex", alignItems: "center", gap: space.md, width: "100%", border: "none", background: "none", cursor: "pointer", font: "inherit", textAlign: "left", flexWrap: "wrap" }}
            >
              <span style={{ fontWeight: 800, fontSize: font.lg, minWidth: 140 }}>{s.bl_no || "B/L 번호 없음"}</span>
              <span style={{ display: "flex", gap: space.xs + 2 }}>
                {COLS.map((t) => (
                  <Chip key={t} type={t} doc={s.documents[t]} />
                ))}
                {s.documents.CO && <Chip type="CO" doc={s.documents.CO} />}
              </span>
              <span style={{ marginLeft: "auto", borderRadius: 999, padding: `2px ${space.sm + 2}px`, fontSize: font.sm, fontWeight: 700, color: st.fg, background: st.bg }}>
                {s.status}
              </span>
              <span aria-hidden style={{ color: colors.muted }}>
                {isOpen ? "▴" : "▾"}
              </span>
            </button>
            {s.missing_marks.length > 0 && (
              <div style={{ fontSize: font.sm, color: colors.needInputText, marginTop: 4 }}>{s.missing_marks.join(" · ")}</div>
            )}
            {isOpen && (
              <div style={{ overflowX: "auto", marginTop: space.sm }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, background: "#fff", borderRadius: 10 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left" }}>항목</th>
                      {COLS.map((t) => (
                        <th key={t} style={{ textAlign: "left" }}>
                          {DOC_LABELS[t]}
                          {s.documents[t] && (
                            <button
                              type="button"
                              onClick={() => openDocument(s.documents[t].doc_id)}
                              style={{ marginLeft: 6, border: "none", background: "none", color: LIST_BLUE, cursor: "pointer", fontSize: 12, textTransform: "none" }}
                            >
                              원본
                            </button>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {FIELDS.map((f) => (
                      <tr key={f.key}>
                        <td style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{f.label}</td>
                        {COLS.map((t) => {
                          const d = s.documents[t];
                          const v = d?.values[f.key];
                          const src = d?.sources[f.key === "line_count" ? "lines" : f.key];
                          return (
                            <td key={t} style={f.num ? num : undefined} title={src ? `출처: ${src}` : undefined}>
                              {d ? (v === null || v === "" ? <span style={{ color: colors.muted }}>—</span> : f.num ? fmtNumber(v as number) : String(v)) : <span style={{ color: colors.muted }}>—</span>}
                              {src?.startsWith("llm") && <span style={{ marginLeft: 4, fontSize: 11, color: colors.needCheck }}>AI</span>}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
