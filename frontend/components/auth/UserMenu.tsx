"use client";
// 오른쪽 위: 이름 + 로그아웃 (DESIGN 2장). 담당: KHS
import { colors, space } from "@/components/ui/tokens";
import { logout } from "@/lib/api/core";
import { T } from "@/lib/text/common";

export function UserMenu({ name }: { name: string }) {
  const onLogout = async () => {
    await logout();
    window.location.href = "/login/";
  };
  return (
    <span style={{ display: "flex", gap: space.sm, alignItems: "center", color: colors.muted }}>
      {name}
      <button type="button" onClick={onLogout}>
        {T.logout}
      </button>
    </span>
  );
}
