"use client";
// 화주 목록 + 화주 추가 (DESIGN 7장). 가명만 보인다. 담당: JUJ
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ErrorLine } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { createShipper } from "@/lib/api/settings";
import { DOC_LABELS } from "@/lib/text/reader";
import { SETTINGS } from "@/lib/text/settings";
import type { Shipper } from "@/lib/types/core";

const DOCS = ["CI", "PL", "BL", "CO", "INTAKE_LIST", "PHOTO"];

export function ShipperList({
  shippers,
  current,
  onPick,
  onCreated,
}: {
  shippers: Shipper[];
  current: string;
  onPick: (id: string) => void;
  onCreated: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [docs, setDocs] = useState<string[]>(["CI", "PL", "BL", "CO"]);
  const [error, setError] = useState<unknown>(null);

  const create = async () => {
    try {
      await createShipper(id.trim(), name.trim(), docs);
      setOpen(false);
      onCreated(id.trim());
    } catch (e) {
      setError(e);
    }
  };

  return (
    <aside style={{ width: 200, borderRight: `1px solid ${colors.border}`, paddingRight: space.md }}>
      <strong>{SETTINGS.list}</strong>
      {shippers.length === 0 && <EmptyState text={SETTINGS.emptyList} />}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {shippers.map((s) => (
          <li key={s.shipper_id}>
            <button
              type="button"
              onClick={() => onPick(s.shipper_id)}
              style={{
                width: "100%",
                textAlign: "left",
                padding: space.xs + 2,
                border: "none",
                borderRadius: 4,
                background: s.shipper_id === current ? colors.primarySoft : "transparent",
                color: s.shipper_id === current ? colors.primary : colors.text,
                cursor: "pointer",
              }}
            >
              {s.shipper_id === current ? "● " : "○ "}
              {s.display_name}
            </button>
          </li>
        ))}
      </ul>
      <Button small onClick={() => setOpen(true)}>
        {SETTINGS.add}
      </Button>
      {open && (
        <Modal
          title={SETTINGS.newShipper.title}
          onClose={() => setOpen(false)}
          width={460}
          footer={
            <>
              <Button onClick={() => setOpen(false)}>취소</Button>
              <Button variant="primary" disabled={!id.trim() || !name.trim()} onClick={create}>
                {SETTINGS.newShipper.create}
              </Button>
            </>
          }
        >
          <label style={{ display: "block", marginBottom: space.sm }}>
            {SETTINGS.newShipper.id}
            <input value={id} onChange={(e) => setId(e.target.value)} style={{ display: "block", width: "100%", padding: space.xs }} />
          </label>
          <label style={{ display: "block", marginBottom: space.sm }}>
            {SETTINGS.newShipper.name}
            <input value={name} onChange={(e) => setName(e.target.value)} style={{ display: "block", width: "100%", padding: space.xs }} />
          </label>
          <div>{SETTINGS.newShipper.docs}</div>
          {DOCS.map((d) => (
            <label key={d} style={{ marginRight: space.sm }}>
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
      )}
    </aside>
  );
}
