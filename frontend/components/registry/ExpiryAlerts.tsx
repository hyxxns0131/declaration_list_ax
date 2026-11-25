"use client";
// 만료 임박 + 알림 메일 (DESIGN 6장): 3개월·1개월 전, 실적·해외제조업소 코드, 같은 대상·같은 단계 1번만. 담당: YHS
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine, Notice } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtDate } from "@/lib/format";
import { getAlerts, previewAlertMail, sendAlerts } from "@/lib/api/registry";
import { REGISTRY } from "@/lib/text/registry";
import type { AlertsOut, MailPreview } from "@/lib/types/registry";

const A = REGISTRY.alerts;

export function ExpiryAlerts({ shipperId, reloadKey }: { shipperId: string; reloadKey: number }) {
  const [data, setData] = useState<AlertsOut | null>(null);
  const [preview, setPreview] = useState<MailPreview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    getAlerts(shipperId).then(setData).catch(setError);
  }, [shipperId]);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  const send = async () => {
    setBusy(true);
    try {
      const out = await sendAlerts(shipperId);
      setMsg(out.sent ? A.sent(out.sent) : out.reason);
      setPreview(null);
      load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const one = data?.summary["30"] ?? 0;
  const three = data?.summary["90"] ?? 0;

  return (
    <section style={{ marginTop: space.lg }}>
      <div style={{ display: "flex", alignItems: "center", gap: space.sm }}>
        <strong>{A.title}</strong>
        <span>{A.summary(one, three)}</span>
        <span style={{ marginLeft: "auto", display: "flex", gap: space.sm }} title={data && !data.mail.ok ? `${A.mailOff} (${data.mail.reason})` : ""}>
          <Button
            small
            onClick={() => previewAlertMail(shipperId).then(setPreview).catch(setError)}
            disabled={!data?.items.length}
          >
            {A.preview}
          </Button>
          <Button small variant="primary" disabled={!data?.mail.ok || busy || !data?.items.length} onClick={send}>
            {A.send}
          </Button>
        </span>
      </div>
      {data && !data.mail.ok && <Notice tone="warn">{A.mailOff} — {data.mail.reason}</Notice>}
      {msg && <Notice>{msg}</Notice>}
      {error !== null && <ErrorLine error={error} onRetry={load} />}
      {data && data.items.length === 0 && <p style={{ color: colors.muted }}>{A.none}</p>}
      {data && data.items.length > 0 && (
        <ul style={{ fontSize: font.md, paddingLeft: space.lg }}>
          {data.items.map((a) => (
            <li key={`${a.kind}:${a.record_no}`} style={{ marginBottom: space.xs }}>
              <Badge tone={a.stage <= 30 ? "mismatch" : "edited"}>{A.days(a.days_left)}</Badge>{" "}
              <Badge tone={a.kind === "factory_code" ? "info" : "neutral"}>{A.kind[a.kind] ?? a.kind}</Badge>{" "}
              {a.kind === "factory_code" ? a.factory : `${a.record_no} · ${a.factory} · ${a.materials.join(", ")}`} · 만료{" "}
              {fmtDate(a.expires_on)}
              {a.sent && (
                <span style={{ color: colors.ok, fontSize: font.sm }}>
                  {" "}
                  ✓ {A.already}
                </span>
              )}
              <div style={{ color: colors.muted, fontSize: font.sm }}>
                {a.kind === "factory_code"
                  ? A.renew
                  : `이 실적을 쓰는 모델: ${a.models.join(", ") || "-"} → ${A.alt(a.alternative)}`}
              </div>
            </li>
          ))}
        </ul>
      )}
      {preview && (
        <Modal
          title={A.preview}
          onClose={() => setPreview(null)}
          footer={
            <>
              <Button onClick={() => setPreview(null)}>닫기</Button>
              <Button variant="primary" disabled={!data?.mail.ok || busy || !preview.count} onClick={send}>
                {A.send}
              </Button>
            </>
          }
        >
          <p>
            <strong>제목:</strong> {preview.subject}
          </p>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", background: colors.bgSubtle, padding: space.sm }}>
            {preview.body || A.none}
          </pre>
        </Modal>
      )}
    </section>
  );
}
