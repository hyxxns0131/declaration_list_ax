"use client";
// 칸 편집 (DESIGN 3-4): 저장하면 final_value. 서류 값과 다르면 메모. 프로그램 값으로 되돌리기. 담당: KHS
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorLine } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { fmtCell, shown } from "@/lib/format";
import { deleteRow, patchCell } from "@/lib/api/history";
import { HOME } from "@/lib/text/home";
import type { HistoryRow } from "@/lib/types/history";

export function CellEditor({
  row,
  column,
  onClose,
  onSaved,
}: {
  row: HistoryRow;
  column: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const cell = row.cells[column];
  const [value, setValue] = useState(String(shown(cell) ?? ""));
  const [memo, setMemo] = useState(cell?.memo ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const program = cell?.ai_value;
  const differs = program !== null && program !== undefined && String(program) !== value.trim() && value.trim() !== "";

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onSaved();
      onClose();
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  const save = () =>
    run(() => patchCell(row.row_id, { column, value: value.trim() === "" ? "" : value.trim(), memo }));
  const revert = () => run(() => patchCell(row.row_id, { column, clear: true, memo: "" }));
  const remove = () => {
    if (window.confirm(HOME.deleteConfirm)) void run(() => deleteRow(row.row_id));
  };

  return (
    <Modal
      title={`${column.split(" (")[0]} · ${row.model || row.row_id}`}
      onClose={onClose}
      width={520}
      footer={
        <>
          <Button variant="danger" onClick={remove} disabled={busy} style={{ marginRight: "auto" }}>
            {HOME.deleteRow}
          </Button>
          {cell?.final_value !== null && cell?.final_value !== undefined && (
            <Button onClick={revert} disabled={busy}>
              {HOME.revert}
            </Button>
          )}
          <Button onClick={onClose}>취소</Button>
          <Button variant="primary" onClick={save} disabled={busy}>
            저장
          </Button>
        </>
      }
    >
      <label style={{ display: "block", fontSize: font.sm, color: colors.muted }}>{column}</label>
      <textarea
        autoFocus
        rows={column === "비고" ? 4 : 2}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && column !== "비고") {
            e.preventDefault();
            void save();
          }
        }}
        style={{ width: "100%", padding: space.sm, fontSize: font.md }}
      />
      {program !== null && program !== undefined && (
        <p style={{ fontSize: font.sm, color: colors.muted, margin: `${space.xs}px 0` }}>
          프로그램 값: {fmtCell(column, program)}
        </p>
      )}
      {(differs || memo) && (
        <>
          <label style={{ display: "block", fontSize: font.sm, color: colors.edited, marginTop: space.sm }}>
            ✎ {HOME.memoPlaceholder}
          </label>
          <input
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            style={{ width: "100%", padding: space.sm }}
          />
        </>
      )}
      {error !== null && <ErrorLine error={error} />}
    </Modal>
  );
}
