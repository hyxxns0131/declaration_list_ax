"use client";
// 현재 적용 중인 규칙(읽기 전용, 시연 피드백 ③). 체크박스를 두지 않는다 — 바꾸기는 탭 1 기업 설정(은진 파트).
// 은진 파트 코드는 고치지 않고 조회 API(lib/api/settings: getRules·getShipper)만 부른다. 규칙 이름·설명도 거기서 읽는다.
// props: shipperId. 담당: LSY
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorLine, Skeleton } from "@/components/ui/StateBox";
import { colors, font, space } from "@/components/ui/tokens";
import { getRules, getShipper } from "@/lib/api/settings";
import { JUDGE } from "@/lib/text/judge";
import type { Catalog, RuleDef, RuleValue, ShipperValues } from "@/lib/types/settings";

const R = JUDGE.rules;

function show(rule: RuleDef, value: RuleValue | undefined): string {
  if (value === undefined || value === null || value === "") return R.none;
  if (typeof value === "boolean") return value ? R.on : R.off;
  const label = (v: string | null) => rule.options?.find((o) => o.value === v)?.label ?? String(v);
  if (Array.isArray(value)) {
    if (!value.length) return R.none;
    const parts = value.map((v) => (typeof v === "string" ? label(v) : v.key));
    return rule.type === "order" ? parts.join(" → ") : parts.join(", ");
  }
  return typeof value === "string" ? label(value) : String(value);
}

export function AppliedRules({ shipperId }: { shipperId: string }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [values, setValues] = useState<ShipperValues | null>(null);
  const [changed, setChanged] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!shipperId) return;
    setValues(null);
    setError(null);
    Promise.all([getRules(), getShipper(shipperId)])
      .then(([rules, shipper]) => {
        setCatalog(rules.catalog);
        setValues(shipper.settings);
        setChanged(shipper.differs_from_default);
      })
      .catch(setError);
  }, [shipperId]);

  const groups = (catalog?.groups ?? []).filter((g) => (R.groups as readonly string[]).includes(g.id));

  return (
    <Card
      title={R.title}
      actions={
        <span style={{ display: "inline-flex", gap: space.sm, alignItems: "center" }}>
          <Link href="/settings/rules/" style={{ fontSize: font.sm, color: colors.primary }}>
            {R.edit}
          </Link>
          <Button small variant="ghost" onClick={() => setOpen(!open)}>
            {open ? R.hide : R.show}
          </Button>
        </span>
      }
    >
      <p style={{ margin: 0, color: colors.muted, fontSize: font.sm }}>{R.sub}</p>
      {error !== null && <ErrorLine error={error} />}
      {open && values === null && error === null && <Skeleton lines={3} />}
      {open && values && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: space.md,
            marginTop: space.sm,
          }}
        >
          {groups.map((g) => (
            <div key={g.id}>
              <div style={{ fontWeight: 700, fontSize: font.sm, marginBottom: space.xs }}>{g.label}</div>
              <div>
                {g.rules.map((rule) => (
                  <div
                    key={rule.key}
                    title={rule.description}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: space.sm,
                      padding: "2px 0",
                      borderTop: `1px solid ${colors.border}`,
                      fontSize: font.sm,
                    }}
                  >
                    <span style={{ color: colors.text, flex: "1 1 auto", minWidth: 0 }}>{rule.label}</span>
                    <span
                      style={{
                        flex: "0 1 55%",
                        textAlign: "right",
                        fontWeight: changed.includes(rule.key) ? 700 : 400,
                        color: changed.includes(rule.key) ? colors.primary : colors.muted,
                      }}
                    >
                      {show(rule, values[rule.key])}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
