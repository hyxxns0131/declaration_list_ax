"use client";
// 새 화주 추가 창: 화주 이름(가명)·화주 ID·받는 서류 → POST /settings/shippers (기본 규칙 복사 + 이름).
// 홈의 '작업할 화주 고르기'와 기업 설정 › 화주 관리가 같이 쓴다. 담당: JUJ(API) · KHS(홈에서 사용)
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { createShipper } from "@/lib/api/settings";
import { DOC_LABELS } from "@/lib/text/reader";
import { SETTINGS } from "@/lib/text/settings";

const DOCS = ["CI", "PL", "BL", "CO", "INTAKE_LIST", "PHOTO"];
const ID_RE = /^[A-Za-z0-9]{1,20}$/; // 백엔드 a4_settings와 같은 규칙(영문·숫자 20자 이내)

export function NewShipperDialog({
  existingIds,
  onClose,
  onCreated,
}: {
  existingIds: string[];
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [docs, setDocs] = useState<string[]>(["CI", "PL", "BL", "CO"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const cleanId = id.trim();
  const idProblem = !cleanId
    ? ""
    : !ID_RE.test(cleanId)
      ? SETTINGS.newShipper.idRule
      : existingIds.some((x) => x.toLowerCase() === cleanId.toLowerCase())
        ? SETTINGS.newShipper.idTaken
        : "";
  const canSave = Boolean(cleanId && name.trim() && !idProblem && !busy);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      await createShipper(cleanId, name.trim(), docs);
      onCreated(cleanId);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  const input = { display: "block", width: "100%", padding: `${space.xs + 2}px ${space.sm}px`, marginTop: space.xs };
  return (
    <Modal
      title={SETTINGS.newShipper.title}
      onClose={onClose}
      width={460}
      footer={
        <>
          <Button onClick={onClose}>{SETTINGS.newShipper.cancel}</Button>
          <Button variant="primary" disabled={!canSave} onClick={create}>
            {busy ? SETTINGS.newShipper.creating : SETTINGS.newShipper.create}
          </Button>
        </>
      }
    >
      <label style={{ display: "block", marginBottom: space.md }}>
        {SETTINGS.newShipper.name}
        <input autoFocus value={name} onChange={(e) => setName(e.target.value)} style={input} />
        <span style={{ fontSize: font.sm, color: colors.muted }}>{SETTINGS.newShipper.pseudonym}</span>
      </label>
      <label style={{ display: "block", marginBottom: space.md }}>
        {SETTINGS.newShipper.id}
        <input value={id} onChange={(e) => setId(e.target.value)} style={input} />
        {idProblem && <span style={{ fontSize: font.sm, color: colors.mismatch }}>■ {idProblem}</span>}
      </label>
      <div style={{ marginBottom: space.xs }}>{SETTINGS.newShipper.docs}</div>
      {DOCS.map((d) => (
        <label key={d} style={{ marginRight: space.sm, whiteSpace: "nowrap" }}>
          <input
            type="checkbox"
            checked={docs.includes(d)}
            onChange={(e) => setDocs(e.target.checked ? [...docs, d] : docs.filter((x) => x !== d))}
          />
          {DOC_LABELS[d]}
        </label>
      ))}
      <p style={{ fontSize: font.sm, color: colors.muted }}>{SETTINGS.newShipper.note}</p>
      {error !== null && <ErrorLine error={error} />}
    </Modal>
  );
}
