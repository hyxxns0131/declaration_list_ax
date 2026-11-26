// 화면 길잡이: 상단 탭(홈 + 6개)과 탭별 사이드바 메뉴. 경로·순서는 이 파일 한 곳에서만 정한다. 담당: KHS
// 탭 순서: 1 기업 설정(JUJ) → 2 서류 등록·만료 알림(YHS) → 3 검역 리스트(KHS) → 4 재질·실적 판단(LSY) → 5 품목사항 엑셀(LSY) → 6 연결 설정(KHS).
// 데이터 흐름 순서(설정 → 실적 등록 → 검역이력 → 판단). 탭 순서 변경: 로직 점검 반영 11/25
import { T } from "@/lib/text/common";

export interface SideItem {
  href: string;
  label: string;
  icon: string;
  /** 단계 번호(검역 리스트 탭만). 사이드바에 번호와 상태(✓·남은 수)를 작게 붙인다 */
  step?: number;
}

export interface Tab {
  key: "home" | "registry" | "list" | "judge" | "itemSheet" | "settings" | "connections";
  href: string;
  label: string;
  owner: string;
  side: SideItem[];
}

/** 메인 화면 = 검역이력 표 (제안서 가이드라인 ④). 로그인 뒤·앱 이름 클릭·처음 연 홈에서 여기로 간다. 로직 점검 반영 11/25 */
export const MAIN_PATH = "/history/";

export const TABS: readonly Tab[] = [
  {
    key: "home",
    href: "/",
    label: T.home,
    owner: "KHS",
    side: [{ href: "/", label: T.side.home.overview, icon: "▦" }],
  },
  {
    // 탭 1. 기업 설정: 화주 선택이 뒤 단계(서류 등록·판단·검역 리스트)를 바꾸므로 맨 앞 (HS 요청 11/25 21시)
    key: "settings",
    href: "/settings/",
    label: T.tabs.settings,
    owner: "JUJ",
    side: [
      { href: "/settings/", label: T.side.settings.shippers, icon: "◉" },
      { href: "/settings/rules/", label: T.side.settings.rules, icon: "☑" },
    ],
  },
  {
    key: "registry",
    href: "/registry/",
    label: T.tabs.registry,
    owner: "YHS",
    side: [
      { href: "/registry/", label: T.side.registry.records, icon: "▤" },
      { href: "/registry/factories/", label: T.side.registry.factories, icon: "⌂" },
      { href: "/registry/alerts/", label: T.side.registry.alerts, icon: "⏰" },
    ],
  },
  {
    key: "list",
    href: "/history/",
    label: T.tabs.list,
    owner: "KHS",
    side: [
      // 업무 순서 ①②③ (탭을 누르면 ③ 완성된 검역 리스트가 열린다: 탭 href = /history/)
      { href: "/history/upload/", label: T.side.list.upload, icon: "⇪", step: 1 },
      { href: "/history/review/", label: T.side.list.review, icon: "⇆", step: 2 },
      { href: "/history/", label: T.side.list.table, icon: "▤", step: 3 },
    ],
  },
  {
    key: "judge",
    href: "/judge/",
    label: T.tabs.judge,
    owner: "LSY",
    side: [
      { href: "/judge/", label: T.side.judge.groups, icon: "▦" },
      { href: "/judge/evidence/", label: T.side.judge.evidence, icon: "ⓘ" },
    ],
  },
  {
    // 탭 5. 품목사항 엑셀: 판단 탭에서 분리 (HS 요청 11/26). 품목사항 로직(a3_judge/item_sheet)이 LSY라 화면도 LSY
    key: "itemSheet",
    href: "/item-sheet/",
    label: T.tabs.itemSheet,
    owner: "LSY",
    side: [{ href: "/item-sheet/", label: T.side.itemSheet.all, icon: "⇩" }],
  },
  {
    // 탭 6. 연결 설정: 가이드라인 밖, HS 요청 11/25 (번호 6: HS 요청 11/26)
    key: "connections",
    href: "/connections/",
    label: T.tabs.connections,
    owner: "KHS",
    side: [
      { href: "/connections/", label: T.side.connections.all, icon: "⚡" },
      { href: "/connections/ai/", label: T.side.connections.ai, icon: "✦" },
    ],
  },
];

const norm = (p: string) => (p.endsWith("/") ? p : `${p}/`);

/** 지금 경로가 속한 탭. 홈은 "/"만. */
export function currentTab(pathname: string): Tab {
  const p = norm(pathname);
  return TABS.find((t) => t.key !== "home" && p.startsWith(t.href)) ?? TABS[0];
}

/** 사이드바 메뉴 중 지금 경로(가장 긴 일치). */
export function isSideActive(pathname: string, tab: Tab, href: string): boolean {
  const p = norm(pathname);
  const best = tab.side
    .filter((s) => p.startsWith(s.href))
    .sort((a, b) => b.href.length - a.href.length)[0];
  return best?.href === href;
}
