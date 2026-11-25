"use client";
// 오른쪽 위: 이름(회색) + 파란 동그라미 머리글자 + 로그아웃 (DESIGN 2장·8장). 담당: KHS
import { Button } from "@/components/ui/Button";
import { colors, font, space } from "@/components/ui/tokens";
import { logout } from "@/lib/api/core";
import { T } from "@/lib/text/common";

export function UserMenu({ name }: { name: string }) {
  const onLogout = async () => {
    await logout();
    window.location.href = "/login/";
  };
  return (
    <span style={{ display: "flex", gap: space.sm + 4, alignItems: "center", color: colors.muted }}>
      <span style={{ whiteSpace: "nowrap" }}>{name}</span>
      <span
        aria-hidden
        style={{
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: colors.brand,
          color: "#fff",
          display: "grid",
          placeItems: "center",
          fontWeight: 700,
          fontSize: font.md,
          flexShrink: 0,
        }}
      >
        {name.trim().charAt(0) || "?"}
      </span>
      <Button small variant="ghost" onClick={onLogout}>
        {T.logout}
      </Button>
    </span>
  );
}
