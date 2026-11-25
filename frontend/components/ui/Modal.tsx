"use client";
// 대화상자. Esc·바깥 누르면 닫힘. 담당: 공통(KHS 관리)
import { useEffect, type ReactNode } from "react";

import { colors, font, radius, space } from "@/components/ui/tokens";

export function Modal({
  title,
  onClose,
  children,
  footer,
  width = 640,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: colors.overlay,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: 60,
        zIndex: 50,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          width,
          maxWidth: "95vw",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          background: colors.bg,
          borderRadius: radius + 2,
          boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: `${space.sm + 4}px ${space.md}px`,
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <strong style={{ fontSize: font.lg }}>{title}</strong>
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            style={{ marginLeft: "auto", border: "none", background: "none", fontSize: 20, cursor: "pointer" }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: space.md, overflow: "auto" }}>{children}</div>
        {footer && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: space.sm,
              padding: `${space.sm + 4}px ${space.md}px`,
              borderTop: `1px solid ${colors.border}`,
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
