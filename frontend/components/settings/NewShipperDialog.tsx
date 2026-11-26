"use client";
// 신규 화주 추가 모달: 사업자 통관고유부호 + 화주 별칭만 받는다(내부 id·받는 서류는 받지 않음, A4-1 개편 11/26).
// 입력이 바뀌면 이전 검사 결과를 버리고 300ms 뒤 POST /settings/shippers/check 로 형식·중복을 미리 본다.
// 최종 판단은 서버 등록(POST /settings/shippers)의 재검사. 기업 설정 › 규칙 설정(ShipperList)과
// 화주 선택·관리(ShipperPicker)가 같이 쓴다. 담당: JUJ
import { useEffect, useState, type CSSProperties } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine, Notice } from "@/components/ui/StateBox";
import { colors, font, radius, space } from "@/components/ui/tokens";
import { ApiError } from "@/lib/api/client";
import { checkNewShipper, createShipper, type NewShipperCheck, type NewShipperField } from "@/lib/api/settings";
import { SETTINGS } from "@/lib/text/settings";

const N = SETTINGS.newShipper;
const DEBOUNCE_MS = 300;

type CheckState =
  | { key: string; status: "checking" }
  | { key: string; status: "done"; result: NewShipperCheck }
  | { key: string; status: "error" };

type Line = { tone: "ok" | "bad" | "muted"; text: string } | null;

function lineFor(value: string, state: CheckState | null, field: NewShipperField | null, ok: string, reasons: Record<string, string>): Line {
  if (!value) return null; // 비어 있으면 안내 문구만 보이고 [추가]는 비활성
  if (!state || state.status === "checking") return { tone: "muted", text: N.checking };
  if (state.status === "error" || !field) return null; // 검사 실패는 아래 ErrorLine 없이 버튼만 막는다
  if (field.ok) return { tone: "ok", text: ok };
  return { tone: "bad", text: reasons[field.reason ?? ""] ?? field.message };
}

export function NewShipperDialog({
  onClose,
  onCreated,
}: {
  /** 예전 화주 ID 중복 검사용. 지금은 서버가 검사하므로 쓰지 않는다(ShipperPicker 호환용으로 남김). */
  existingIds?: string[];
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [code, setCode] = useState("");
  const [alias, setAlias] = useState("");
  const [check, setCheck] = useState<CheckState | null>(null);
  const [nonce, setNonce] = useState(0); // 409 뒤 다시 검사
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const codeT = code.trim();
  const aliasT = alias.trim();
  const key = `${codeT}|${aliasT}`;

  useEffect(() => {
    if (!codeT && !aliasT) {
      setCheck(null);
      return;
    }
    setCheck({ key, status: "checking" }); // 입력이 바뀌면 이전 결과는 즉시 무효
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      checkNewShipper(codeT, aliasT, ctrl.signal)
        .then((result) => {
          if (!ctrl.signal.aborted) setCheck({ key, status: "done", result });
        })
        .catch(() => {
          if (!ctrl.signal.aborted) setCheck({ key, status: "error" });
        });
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
  }, [codeT, aliasT, key, nonce]);

  const state = check && check.key === key ? check : null;
  const result = state?.status === "done" ? state.result : null;
  const codeLine = lineFor(codeT, state, result?.code ?? null, N.codeOk, N.codeReasons);
  const aliasLine = lineFor(aliasT, state, result?.alias ?? null, N.aliasOk, N.aliasReasons);
  const canSave = Boolean(codeT && aliasT && result?.code.ok && result.alias.ok && !busy);

  const create = async () => {
    if (!canSave) return;
    setBusy(true);
    setError(null);
    try {
      const out = await createShipper(codeT, aliasT);
      onCreated(String(out.settings.shipper_id));
    } catch (e) {
      setError(e); // 입력값은 그대로 둔다
      setBusy(false);
      if (e instanceof ApiError && e.status === 409) setNonce((n) => n + 1);
    }
  };

  const input: CSSProperties = {
    display: "block",
    width: "100%",
    boxSizing: "border-box",
    padding: `${space.xs + 4}px ${space.sm + 2}px`,
    marginTop: space.xs,
    border: `1px solid ${colors.border}`,
    borderRadius: radius,
    fontSize: font.md,
  };
  const help: CSSProperties = { display: "block", fontSize: font.sm, color: colors.muted, marginTop: space.xs };

  const field = (
    id: string,
    label: string,
    value: string,
    onChange: (v: string) => void,
    placeholder: string,
    helpText: string,
    line: Line,
    extra: { autoFocus?: boolean; maxLength?: number } = {},
  ) => (
    <div style={{ marginBottom: space.md }}>
      <label htmlFor={id} style={{ fontWeight: 600 }}>
        {label} <span style={{ color: colors.mismatch }}>{N.required}</span>
      </label>
      <input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        aria-required="true"
        aria-invalid={line?.tone === "bad"}
        aria-describedby={`${id}-help ${id}-line`}
        style={{ ...input, borderColor: line?.tone === "bad" ? colors.mismatch : colors.border }}
        {...extra}
      />
      <span id={`${id}-help`} style={help}>
        {helpText}
      </span>
      <span
        id={`${id}-line`}
        role="status"
        style={{
          display: "block",
          minHeight: 18,
          fontSize: font.sm,
          marginTop: 2,
          color: line?.tone === "ok" ? colors.ok : line?.tone === "bad" ? colors.mismatch : colors.muted,
        }}
      >
        {line && `${line.tone === "ok" ? "✓ " : line.tone === "bad" ? "■ " : ""}${line.text}`}
      </span>
    </div>
  );

  return (
    <Modal
      title={N.title}
      onClose={onClose}
      width={530}
      footer={
        <>
          <Button onClick={onClose}>{N.cancel}</Button>
          <Button variant="primary" disabled={!canSave} onClick={create}>
            {busy ? N.creating : N.create}
          </Button>
        </>
      }
    >
      <p style={{ marginTop: 0, marginBottom: space.md, color: colors.muted, fontSize: font.md }}>{N.intro}</p>
      {field(
        "new-shipper-code",
        N.code,
        code,
        (v) => setCode(v.toUpperCase()),
        N.codePlaceholder,
        result?.mode === "prod" ? N.codeHelpProd : N.codeHelpDev,
        codeLine,
        { autoFocus: true, maxLength: 40 },
      )}
      {field(
        "new-shipper-alias",
        N.alias,
        alias,
        (v) => setAlias(v.toUpperCase().replace(/[^A-Z ]/g, "")), // 영문만(앞뒤 공백은 검사·전송 때 지움)
        N.aliasPlaceholder,
        N.aliasHelp,
        aliasLine,
        { maxLength: 5 },
      )}
      <Notice>{N.defaultRules}</Notice>
      {error !== null && <ErrorLine error={error} />}
    </Modal>
  );
}
