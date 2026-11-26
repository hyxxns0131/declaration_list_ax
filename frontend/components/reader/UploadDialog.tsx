"use client";
// 서류 올리기 대화상자 (DESIGN 3-1-1, 검역 리스트 탭 1단계 화면 ①). props: shipperId → onUploaded(rowIds).
// 흰 카드(모서리 24px, 폭 480px) · (가) 끌어놓기 영역 · (나) 파일 카드(판별·크기·상태, 진행 막대) · (다) [취소] [올리기].
// 폴더 1개 = 선적서류 1건. 담당: KHS
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type DragEvent } from "react";

import { LIST_BLUE, PILL_HEIGHT, pillDisabled, pillPrimary, pillSecondary } from "@/components/review/listUi";
import { errorText } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { previewFiles, uploadDocs } from "@/lib/api/reader";
import { T } from "@/lib/text/common";
import { DOC_LABELS, READER } from "@/lib/text/reader";
import type { PreviewOut, UploadOut } from "@/lib/types/reader";

type Phase = "ready" | "reading" | "done" | "failed";

const ACCEPT = ".pdf,.xlsx,.xls,.xlsm,.jpg,.jpeg,.png,.webp,.heic";
const FAIL_WORDS = ["판독 실패", "지원하지 않는"];

function size(n: number): string {
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(n / 1024))} KB`;
}

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
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<PreviewOut | null>(null);
  const [phase, setPhase] = useState<Phase>("ready");
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<UploadOut | null>(null);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);

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
    setPhase("ready");
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    add(e.dataTransfer.files);
  };

  const submit = async () => {
    if (!files.length) return;
    setPhase("reading");
    setError(null);
    onStart?.();
    try {
      const out = await uploadDocs(shipperId, files);
      setResult(out);
      setPhase("done");
      onUploaded([...out.created, ...out.updated], out);
    } catch (e) {
      setError(e);
      setPhase("failed");
    } finally {
      onEnd?.();
    }
  };

  const kindOf = (name: string): string | null => {
    const doc = result?.documents.find((d) => d.filename === name);
    return doc?.doc_type ?? preview?.files.find((f) => f.filename === name)?.doc_type ?? null;
  };
  const docOf = (name: string) => result?.documents.find((d) => d.filename === name);
  const reading = phase === "reading";
  const off = reading || !files.length || phase === "done";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={READER.title(shipperName)}
      onClick={(e) => e.target === e.currentTarget && !reading && onClose()}
      style={{ position: "fixed", inset: 0, background: colors.overlay, display: "grid", placeItems: "center", zIndex: 40, padding: space.md }}
    >
      <style>{`
        .upl-bar { position: relative; overflow: hidden; }
        .upl-bar.run::after { content: ""; position: absolute; top: 0; bottom: 0; left: 0; width: 40%; background: ${LIST_BLUE}; animation: uplRun 1.1s ease-in-out infinite; border-radius: 3px; }
        @keyframes uplRun { from { transform: translateX(-100%); } to { transform: translateX(250%); } }
        .upl-card button:focus-visible { outline: 3px solid ${LIST_BLUE}; outline-offset: 2px; }
        @media (prefers-reduced-motion: reduce) { .upl-bar.run::after { animation: none; width: 100%; opacity: .5; } .upl-round { box-shadow: none !important; } }
      `}</style>
      <div
        className="upl-card"
        style={{
          background: colors.bg,
          borderRadius: 24,
          boxShadow: "0 20px 50px rgba(15, 23, 42, 0.22)",
          width: "min(480px, 100%)",
          maxHeight: "92vh",
          overflowY: "auto",
          padding: space.lg,
        }}
      >
        <div style={{ fontSize: font.sm, color: colors.muted, marginBottom: space.sm }}>{READER.title(shipperName)}</div>

        {/* (가) 끌어놓기 영역 */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={onDrop}
          style={{
            border: `2px dashed ${over ? LIST_BLUE : "#d5dbe5"}`,
            background: over ? colors.primarySoft : "#f7f9fc",
            borderRadius: 16,
            padding: `${space.lg}px ${space.md}px`,
            textAlign: "center",
          }}
        >
          <div style={{ fontWeight: 800, fontSize: font.lg, marginBottom: space.md }}>{READER.dropTitle}</div>
          <button
            type="button"
            className="upl-round"
            aria-label={READER.pick}
            onClick={() => input.current?.click()}
            disabled={reading}
            style={{
              width: 80,
              height: 80,
              borderRadius: "50%",
              border: "none",
              background: "#fff",
              color: LIST_BLUE,
              fontSize: 34,
              fontWeight: 800,
              cursor: "pointer",
              boxShadow: `0 10px 24px rgba(37, 99, 201, ${over ? 0.45 : 0.25})`,
            }}
          >
            ↑
          </button>
          <div style={{ marginTop: space.md, fontSize: font.md, color: colors.muted }}>{READER.kinds}</div>
          <div style={{ fontSize: font.md, color: colors.muted }}>{READER.folderRule}</div>
          <button
            type="button"
            onClick={() => folder.current?.click()}
            disabled={reading}
            style={{ marginTop: space.sm, border: "none", background: "none", color: LIST_BLUE, cursor: "pointer", fontSize: font.md }}
          >
            {READER.pickFolder}
          </button>
          <input
            ref={input}
            type="file"
            multiple
            hidden
            accept={ACCEPT}
            onChange={(e) => {
              add(e.target.files);
              e.target.value = "";
            }}
          />
          <input
            ref={folder}
            type="file"
            multiple
            hidden
            {...({ webkitdirectory: "" } as Record<string, string>)}
            onChange={(e) => {
              add(e.target.files);
              e.target.value = "";
            }}
          />
        </div>

        {/* (나) 파일 목록 */}
        {files.length > 0 && (
          <ul style={{ listStyle: "none", padding: 0, margin: `${space.md}px 0 0`, display: "grid", gap: space.sm }}>
            {files.map((f) => {
              const k = kindOf(f.name);
              const doc = docOf(f.name);
              const failed = phase === "failed" || Boolean(doc?.warnings.some((w) => FAIL_WORDS.some((x) => w.includes(x))));
              const state = reading ? READER.reading : failed ? READER.failed : phase === "done" ? READER.read : READER.waiting;
              return (
                <li key={f.name} style={{ background: "#f3f5f9", borderRadius: 14, padding: `${space.sm + 2}px ${space.md - 4}px` }}>
                  <div style={{ display: "flex", alignItems: "center", gap: space.sm + 2 }}>
                    <span
                      aria-hidden
                      style={{ width: 36, height: 36, borderRadius: 10, background: colors.primarySoft, color: LIST_BLUE, display: "grid", placeItems: "center", fontWeight: 800, flexShrink: 0 }}
                    >
                      {f.name.toLowerCase().endsWith(".pdf") ? "P" : /\.(xlsx|xls|xlsm)$/i.test(f.name) ? "X" : "I"}
                    </span>
                    <span style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={f.name}>
                        {f.name}
                      </div>
                      <div style={{ fontSize: font.sm, color: failed ? colors.mismatch : colors.muted }}>
                        {k ? DOC_LABELS[k] ?? k : `? ${READER.unknownType}`} · {size(f.size)} · {state}
                      </div>
                    </span>
                    <button
                      type="button"
                      aria-label={`${f.name} ${READER.remove}`}
                      disabled={reading}
                      onClick={() => setFiles(files.filter((x) => x !== f))}
                      style={{ width: 30, height: 30, borderRadius: "50%", border: `1px solid ${colors.border}`, background: "#fff", cursor: "pointer", flexShrink: 0 }}
                    >
                      ×
                    </button>
                  </div>
                  <div className={`upl-bar${reading ? " run" : ""}`} style={{ height: 4, borderRadius: 3, background: "#dde3ec", marginTop: space.sm }}>
                    {!reading && phase !== "ready" && (
                      <div style={{ height: "100%", width: "100%", borderRadius: 3, background: failed ? colors.mismatch : LIST_BLUE }} />
                    )}
                  </div>
                  {failed && doc && doc.warnings.length > 0 && (
                    <div style={{ fontSize: font.sm, color: colors.mismatch, marginTop: 4 }}>{doc.warnings.join(" · ")}</div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {preview && files.length > 0 && phase !== "done" && (
          <div style={{ fontSize: font.sm, marginTop: space.sm }}>
            {READER.recognized}:{" "}
            {preview.required.map((r) => (
              <span key={r.doc_type} style={{ marginRight: space.sm, color: r.present ? colors.ok : colors.needInputText }}>
                {r.present ? "✓" : "✗"} {r.label}
              </span>
            ))}
          </div>
        )}

        {phase === "failed" && (
          <div role="alert" style={{ marginTop: space.sm, color: colors.mismatch, fontSize: font.md }}>
            ■ {errorText(error)}{" "}
            <button type="button" onClick={submit} style={{ border: "none", background: "none", color: LIST_BLUE, cursor: "pointer", fontWeight: 700 }}>
              {T.retry}
            </button>
          </div>
        )}

        {result && (
          <div style={{ marginTop: space.md, padding: space.sm + 2, borderRadius: 12, background: colors.okSoft, fontSize: font.md }}>
            <strong>{READER.summary(1, result.missing_docs.length)}</strong>
            {result.bl_no && <span style={{ color: colors.muted }}> · B/L {result.bl_no}</span>}
            {result.missing_docs.length > 0 && (
              <div style={{ color: colors.needInputText, fontSize: font.sm }}>
                {READER.missing(result.missing_docs.map((d) => DOC_LABELS[d] ?? d).join(", "))}
              </div>
            )}
            {result.warnings.map((w) => (
              <div key={w} style={{ color: colors.needCheck, fontSize: font.sm }}>
                {w}
              </div>
            ))}
            {!result.drive.ok && <div style={{ color: colors.muted, fontSize: font.sm }}>{T.integrations.driveOff}</div>}
            <button
              type="button"
              onClick={() => {
                onClose();
                router.push("/history/review/");
              }}
              style={{ ...pillPrimary, height: 40, marginTop: space.sm }}
            >
              {READER.goReview} →
            </button>
          </div>
        )}

        {/* (다) 버튼 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: space.sm, marginTop: space.lg }}>
          <button
            type="button"
            onClick={onClose}
            disabled={reading}
            style={{ ...pillSecondary, height: PILL_HEIGHT + 4, justifyContent: "center", ...(reading ? pillDisabled : {}) }}
          >
            {result ? T.close : T.cancel}
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={off}
            style={{ ...pillPrimary, height: PILL_HEIGHT + 4, justifyContent: "center", ...(off ? pillDisabled : {}) }}
          >
            {reading ? READER.reading : READER.submit}
          </button>
        </div>
      </div>
    </div>
  );
}
