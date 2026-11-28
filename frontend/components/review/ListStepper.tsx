"use client";
// 검역 리스트 탭 단계 표시줄 (헤더 바로 아래, 세 화면 공통): ① 서류 올리기·추출 → ② 서류 대조·검수 → ③ 완성된 검역 리스트.
// 순서·경로는 lib/nav.ts의 list 탭 side, 완료 판단은 GET /history/steps(화주별). 원을 누르면 그 화면으로(막지 않음).
// 담당: KHS (검역 리스트 탭 0단계, HS 요청 11/26)
import Link from "next/link";
import { usePathname } from "next/navigation";

import { LIST_BLUE } from "@/components/review/listUi";
import { useListSteps } from "@/components/review/useListSteps";
import { colors, font, space } from "@/components/ui/tokens";
import { useShipper } from "@/lib/hooks/useShipper";
import { TABS, isSideActive } from "@/lib/nav";

const GREY = "#c7ced9";
const KEYS = ["upload", "review", "list"] as const;

export function ListStepper() {
  const pathname = usePathname();
  const { shipperId } = useShipper();
  const data = useListSteps(shipperId);
  const tab = TABS.find((t) => t.key === "list");
  if (!tab) return null;
  const items = tab.side.filter((s) => s.step).sort((a, b) => (a.step ?? 0) - (b.step ?? 0));
  const currentLabel = items.find((s) => isSideActive(pathname, tab, s.href))?.label ?? "";

  return (
    <nav aria-label="검역 리스트 단계" className="list-stepper" style={{ margin: `${space.xs}px 0 ${space.md}px` }}>
      <style>{`
        .list-stepper .ring { animation: stepGlow 1.6s ease-out 1; }
        @keyframes stepGlow { from { box-shadow: 0 0 0 0 rgba(58,155,232,.45); } to { box-shadow: 0 0 0 12px rgba(58,155,232,0); } }
        @media (prefers-reduced-motion: reduce) { .list-stepper .ring { animation: none; } }
        .list-stepper a:focus-visible { outline: 2px solid ${LIST_BLUE}; outline-offset: 3px; border-radius: 999px; }
        @media (max-width: 760px) { .list-stepper .name, .list-stepper .left { display: none; } .list-stepper .current-name { display: block !important; } }
      `}</style>
      <ol style={{ display: "flex", alignItems: "flex-start", listStyle: "none", margin: 0, padding: 0 }}>
        {items.map((s, i) => {
          const info = data?.steps.find((x) => x.key === KEYS[(s.step ?? 1) - 1]);
          const current = isSideActive(pathname, tab, s.href);
          const done = Boolean(info?.done) && !current;
          const size = current ? 38 : 30;
          const last = i === items.length - 1;
          return (
            <li key={s.href} style={{ display: "flex", alignItems: "flex-start", flex: last ? "0 0 auto" : 1 }}>
              <Link
                href={s.href}
                aria-current={current ? "step" : undefined}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", textDecoration: "none", minWidth: 110 }}
              >
                <span
                  className={current ? "ring" : undefined}
                  style={{
                    width: size,
                    height: size,
                    marginTop: current ? 0 : 4,
                    borderRadius: "50%",
                    display: "grid",
                    placeItems: "center",
                    fontWeight: 800,
                    fontSize: current ? font.lg : font.md,
                    fontVariantNumeric: "tabular-nums",
                    background: current || done ? LIST_BLUE : "#eef1f6",
                    color: current || done ? "#fff" : colors.muted,
                    border: done || current ? "none" : `2px solid ${GREY}`,
                    outline: current ? `3px solid ${colors.primarySoft}` : undefined,
                    outlineOffset: current ? 3 : undefined,
                  }}
                >
                  {done ? "✓" : s.step}
                </span>
                <span
                  className="name"
                  style={{
                    marginTop: space.xs + 2,
                    fontSize: font.md,
                    fontWeight: current ? 800 : 500,
                    color: current ? colors.text : done ? colors.text : colors.muted,
                    whiteSpace: "nowrap",
                  }}
                >
                  {s.label}
                </span>
                {info && !info.done && (
                  <span className="left" style={{ fontSize: font.sm, color: colors.muted, whiteSpace: "nowrap" }}>
                    {info.remaining > 0 ? `${info.label} ${info.remaining}` : info.label}
                  </span>
                )}
              </Link>
              {!last && (
                // 연결선: 이 단계가 끝났으면 파랑
                <span aria-hidden style={{ flex: 1, height: 2, marginTop: 18, background: info?.done ? LIST_BLUE : GREY, minWidth: 24 }} />
              )}
            </li>
          );
        })}
      </ol>
      <div className="current-name" style={{ display: "none", textAlign: "center", fontWeight: 800, marginTop: space.xs }}>
        {currentLabel}
      </div>
    </nav>
  );
}

/** 사이드바 메뉴 옆 작은 단계 상태: 완료면 ✓, 아니면 남은 수. AuthGate가 step이 있는 메뉴에만 붙인다 */
export function SideStepMark({ step }: { step: number }) {
  const { shipperId } = useShipper();
  const data = useListSteps(shipperId);
  const info = data?.steps.find((x) => x.key === KEYS[step - 1]);
  if (!info) return null;
  return (
    <span
      title={info.done ? "완료" : `${info.label} ${info.remaining}`}
      style={{
        marginLeft: "auto",
        minWidth: 20,
        height: 20,
        padding: "0 6px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 800,
        display: "inline-grid",
        placeItems: "center",
        background: info.done ? colors.okSoft : colors.pillWarnSoft,
        color: info.done ? colors.ok : colors.pillWarnText,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {info.done ? "✓" : info.remaining || "·"}
    </span>
  );
}
