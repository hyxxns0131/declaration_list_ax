// 상단 탭: 홈 + 1 기업 설정 · 2 서류 등록·만료 알림 · 3 검역 리스트 · 4 재질·실적 판단 · 5 품목사항 엑셀 · 6 연결 설정(탭 순서 변경: 로직 점검 반영 11/25, 5번 추가 HS 요청 11/26) + 로그인 확인. PM만 수정 (AGENTS 4-3). 탭은 components/auth/AuthGate.tsx, 목록은 lib/nav.ts. 담당: KHS
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
