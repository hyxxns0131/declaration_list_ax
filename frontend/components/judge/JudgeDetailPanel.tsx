"use client";
// 행 상세 패널 (기능 3 프로토타입 반영, 시연 피드백 ③): 재질 근거 카드 4개 + 제조업소 + 정밀검사 실적.
// 재질 카드 4개는 화주 설정 material_source_order 순서대로(백엔드가 실제로 쓴 순서 detail.material.order).
// 값을 바꾸지 않는다 — 고르기는 칸 옆 ⓘ(JudgeEvidence). props: row, onClose. 담당: LSY
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getJudge } from "@/lib/api/judge";
import { fmtDate, shown } from "@/lib/format";
import { JUDGE } from "@/lib/text/judge";
import type { Evidence, HistoryRow } from "@/lib/types/history";
import type { JudgeDetail, RecordCandidate } from "@/lib/types/judge";

const D = JUDGE.detail;
const SRC = JUDGE.sources;
const DEFAULT_ORDER = ["HISTORY", "IMPORT_DECL", "TEST_REPORT", "PHOTO"];

const box = {
  border: `1px solid ${colors.border}`,
  borderRadius: 10,
  padding: space.sm,
  minWidth: 0,
  fontSize: font.sm,
  lineHeight: 1.55,
} as const;
const list = { margin: `${space.xs}px 0 0`, padding: 0, listStyle: "none" } as const;
const item = { borderTop: `1px solid ${colors.border}`, padding: `${space.xs}px 0` } as const;

function matches(src: string, e: Evidence): boolean {
  return src === "PHOTO" ? e.source === "PHOTO" || e.source === "LABEL" : e.source === src;
}

function MaterialCards({ detail }: { detail: JudgeDetail }) {
  const ev = detail.material?.evidence ?? [];
  const order = detail.material?.order?.length ? detail.material.order : DEFAULT_ORDER;
  const used = ev.find((e) => e.source !== "RULE" && e.source !== "PHOTO" && e.source !== "LABEL")?.source;
  return (
    <div>
      <div style={{ fontWeight: 700, marginBottom: space.xs }}>
        {D.materialTitle} <span style={{ color: colors.muted, fontWeight: 400 }}>· {D.materialOrder}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: space.sm }}>
        {order.map((src, i) => {
          const hits = ev.filter((e) => matches(src, e));
          const isUsed = used === src;
          return (
            <section
              key={src}
              aria-label={`${i + 1}. ${SRC[src] ?? src}`}
              style={{
                ...box,
                borderColor: isUsed ? colors.primary : colors.border,
                background: isUsed ? colors.primarySoft : "transparent",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: space.xs }}>
                <b>
                  {i + 1}. {SRC[src] ?? src}
                  {src === "PHOTO" && ` · ${SRC.LABEL}`}
                </b>
                {isUsed ? (
                  <Badge tone="ok">✓ {D.used}</Badge>
                ) : hits.length ? (
                  <Badge tone="needCheck">{D.other}</Badge>
                ) : (
                  <Badge>{D.empty}</Badge>
                )}
              </div>
              {hits.length > 0 && (
                <ul style={list}>
                  {hits.map((e) => (
                    <li key={`${e.source}-${e.ref}-${e.note}`} style={item}>
                      {e.note}
                    </li>
                  ))}
                </ul>
              )}
              {src === "PHOTO" && <p style={{ margin: `${space.xs}px 0 0`, color: colors.muted }}>{D.photoNote}</p>}
            </section>
          );
        })}
      </div>
      {(detail.material?.candidates?.length ?? 0) > 1 && (
        <p style={{ margin: `${space.xs}px 0 0`, color: colors.needCheck }}>
          ? {JUDGE.evidence.candidates}: {detail.material?.candidates.join(" / ")}
        </p>
      )}
    </div>
  );
}

function FactoryCard({ detail }: { detail: JudgeDetail }) {
  const m = detail.maker;
  return (
    <section style={box}>
      <b>{D.factoryTitle}</b>
      <p style={{ margin: `${space.xs}px 0 0`, color: colors.muted }}>{JUDGE.evidence.docAddress(m?.address ?? "")}</p>
      {m?.candidates?.length ? (
        <ul style={list}>
          {m.candidates.map((c) => (
            <li key={c.code} style={item}>
              <b>{c.code}</b>{" "}
              {c.status && <Badge tone={c.status === "선택" ? "ok" : c.status === "제외" ? "neutral" : "info"}>{c.status}</Badge>}
              <div style={{ color: colors.muted }}>{c.address}</div>
              {typeof c.score === "number" && <div>{JUDGE.evidence.score(c.score)}</div>}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ margin: `${space.xs}px 0 0`, color: colors.muted }}>{D.noCandidates}</p>
      )}
      {(m?.notes ?? []).map((n) => (
        <p key={n} style={{ margin: `${space.xs}px 0 0` }}>
          {n}
        </p>
      ))}
    </section>
  );
}

function RecordLine({ c }: { c: RecordCandidate }) {
  const tone = c.status === "선택" ? "ok" : c.status === "제외" ? "neutral" : "info";
  return (
    <li style={item}>
      <b style={{ textDecoration: c.expired ? "line-through" : "none", color: c.expired ? colors.muted : colors.text }}>
        {c.value}
      </b>{" "}
      {c.status && <Badge tone={tone}>{D.status[c.status] ?? c.status}</Badge>}
      <div style={{ color: colors.muted }}>
        {c.materials.join(", ")} · ~{fmtDate(c.expires_on)}
      </div>
      {c.checks && (
        <div>
          {Object.entries(c.checks).map(([k, ok]) => (
            <span key={k} style={{ marginRight: space.sm, color: ok ? colors.ok : colors.mismatch }}>
              {ok ? "✓" : "✗"} {k}
            </span>
          ))}
        </div>
      )}
      {c.reason && <div style={{ color: c.status === "제외" ? colors.mismatch : colors.muted }}>{c.reason}</div>}
    </li>
  );
}

function RecordCard({ detail }: { detail: JudgeDetail }) {
  const r = detail.record;
  return (
    <section style={box}>
      <b>{D.recordTitle}</b>
      {r?.basis_date && <p style={{ margin: `${space.xs}px 0 0`, color: colors.muted }}>{D.basis(fmtDate(r.basis_date))}</p>}
      {r?.candidates?.length ? (
        <ul style={list}>
          {r.candidates.map((c) => (
            <RecordLine key={c.record_no} c={c} />
          ))}
        </ul>
      ) : (
        <p style={{ margin: `${space.xs}px 0 0`, color: colors.muted }}>{D.noCandidates}</p>
      )}
    </section>
  );
}

export function JudgeDetailPanel({ row, onClose }: { row: HistoryRow; onClose: () => void }) {
  const [detail, setDetail] = useState<JudgeDetail | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setDetail(null);
    setError(null);
    getJudge(row.row_id).then(setDetail).catch(setError);
  }, [row.row_id]);

  const name = String(shown(row.cells["한글 제품명(모델넘버)"]) ?? row.model);
  const note = String(shown(row.cells["비고"]) ?? "");

  return (
    <Card
      title={name}
      actions={
        <Button small variant="ghost" onClick={onClose}>
          {D.close}
        </Button>
      }
    >
      {note && (
        <p style={{ margin: `0 0 ${space.sm}px`, color: colors.needCheck, fontSize: font.sm, whiteSpace: "pre-line" }}>
          {note}
        </p>
      )}
      {error !== null && <ErrorLine error={error} />}
      {detail === null && error === null && <Skeleton lines={4} />}
      {detail && (
        <div style={{ display: "grid", gap: space.md }}>
          <MaterialCards detail={detail} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: space.md }}>
            <FactoryCard detail={detail} />
            <RecordCard detail={detail} />
          </div>
        </div>
      )}
    </Card>
  );
}
