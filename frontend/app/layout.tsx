// 상단 탭 4개(검역 리스트·서류 등록·만료 알림·재질·실적 판단·기업 설정) + 로그인 확인. 탭 4개 고정, PM만 수정 (AGENTS 4-3). 탭은 components/auth/AuthGate.tsx에서 그린다. 담당: KHS
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthGate } from "@/components/auth/AuthGate";
import { T } from "@/lib/text/common";

import "./globals.css";

export const metadata: Metadata = { title: T.appName };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}
