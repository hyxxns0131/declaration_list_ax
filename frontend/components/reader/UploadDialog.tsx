"use client";
// 서류 올리기 대화상자 (DESIGN 3-1-1). props: shipperId → onUploaded(rowIds). 담당: KHS
import { useEffect, useRef, useState, type DragEvent } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine, Notice } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { previewFiles, uploadDocs } from "@/lib/api/reader";
import { T } from "@/lib/text/common";
import { DOC_LABELS, READER } from "@/lib/text/reader";
import type { PreviewOut, UploadOut } from "@/lib/types/reader";

export function UploadDialog({
  shipperId,
  shipperName,
  onClose,
  onUploaded,
  onStart,
  onEnd,
}: {
  shipperId: string;
  shipperName: string;
  onClose: () => void;
  onUploaded: (rowIds: string[], result: UploadOut) => void;
  onStart?: () => void;
  onEnd?: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<PreviewOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<UploadOut | null>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!files.length) {
      setPreview(null);
      return;
    }
    previewFiles(
      shipperId,
      files.map((f) => f.name),
    )
      .then(setPreview)
      .catch(() => setPreview(null));
  }, [files, shipperId]);

  const add = (list: FileList | null) => {
    if (!list) return;
    const next = [...files];
    for (const f of Array.from(list)) if (!next.some((x) => x.name === f.name)) next.push(f);
    setFiles(next);
    setResult(null);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    add(e.dataTransfer.files);
  };

  const submit = async () => {
    if (!files.length) return;
    setBusy(true);
    setError(null);
    onStart?.();
    try {
      const out = await uploadDocs(shipperId, files);
      setResult(out);
      setFiles([]);
      onUploaded([...out.created, ...out.updated], out);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
      onEnd?.();
    }
  };

  const kindOf = (name: string) => preview?.files.find((f) => f.filename === name)?.doc_type ?? null;

  return (
    <Modal
      title={READER.title(shipperName)}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>{result ? T.close : T.cancel}</Button>
          <Button variant="primary" disabled={busy || !files.length} onClick={submit}>
            {busy ? T.loading : READER.submit}
          </Button>
        </>
      }
    >
      <p style={{ marginTop: 0 }}>{READER.guide}</p>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${colors.border}`,
          borderRadius: 8,
          padding: space.lg,
          textAlign: "center",
          color: colors.muted,
        }}
      >
        {READER.drop}{" "}
        <Button small onClick={() => input.current?.click()}>
          {READER.pick}
        </Button>
        <div style={{ fontSize: font.sm, marginTop: space.xs }}>{READER.kinds}</div>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept=".pdf,.xlsx,.xls,.xlsm,.jpg,.jpeg,.png,.webp,.heic"
          onChange={(e) => {
            add(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: `${space.md}px 0` }}>
          {files.map((f) => {
            const k = kindOf(f.name);
            return (
              <li key={f.name} style={{ display: "flex", gap: space.sm, alignItems: "center", padding: "2px 0" }}>
                <Badge tone={k ? "info" : "needCheck"}>{k ? DOC_LABELS[k] ?? k : `? ${READER.unknownType}`}</Badge>
                <span style={{ fontSize: font.md }}>{f.name}</span>
                <Button small variant="ghost" onClick={() => setFiles(files.filter((x) => x !== f))}>
                  {READER.remove}
                </Button>
              </li>
            );
          })}
        </ul>
      )}

      {preview && (
        <div style={{ fontSize: font.md }}>
          {READER.recognized}:{" "}
          {preview.required.map((r) => (
            <span key={r.doc_type} style={{ marginRight: space.sm, color: r.present ? colors.ok : colors.mismatch }}>
              {r.present ? "✓" : "✗"} {r.label}
            </span>
          ))}
          <div style={{ color: colors.muted, fontSize: font.sm }}>
            {READER.required(preview.required.map((r) => r.label).join(" · "))}
          </div>
        </div>
      )}

      {busy && <Notice>{READER.uploading}</Notice>}
      {error !== null && <ErrorLine error={error} onRetry={submit} />}
      {result && (
        <div style={{ marginTop: space.md }}>
          <Notice>
            {result.bl_no ? `B/L ${result.bl_no} · ` : ""}
            {READER.done(result.created.length, result.updated.length)}
          </Notice>
          {result.reupload && <Notice>{READER.reupload}</Notice>}
          {result.missing_docs.length > 0 && (
            <Notice tone="warn">{READER.missing(result.missing_docs.map((d) => DOC_LABELS[d] ?? d).join(", "))}</Notice>
          )}
          {result.warnings.map((w) => (
            <Notice key={w} tone="warn">
              {w}
            </Notice>
          ))}
          {result.documents
            .filter((d) => d.warnings.length)
            .map((d) => (
              <Notice key={d.doc_id} tone="warn">
                {d.filename}: {d.warnings.join(", ")}
              </Notice>
            ))}
          {!result.drive.ok && <Notice>{T.integrations.driveOff}</Notice>}
        </div>
      )}
    </Modal>
  );
}
