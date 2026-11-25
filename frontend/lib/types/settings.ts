// 백엔드 a4_settings 응답과 같은 타입. 담당: JUJ
export type RuleValue = boolean | number | string | null | string[] | ShipperException[];

export interface RuleOption {
  value: string | null;
  label: string;
}

export interface RuleDef {
  key: string;
  type: "bool" | "int" | "select" | "multi" | "order" | "select_list";
  label: string;
  description: string;
  options?: RuleOption[];
  fixed?: boolean;
  proposal?: boolean;
  advanced?: boolean;
  exception?: boolean;
}

export interface RuleGroup {
  id: string;
  label: string;
  rules: RuleDef[];
}

export interface Catalog {
  groups: RuleGroup[];
  meta_keys: string[];
}

export interface ShipperException {
  key: string;
  reason: string;
  basis?: string;
  since?: string;
}

export type ShipperValues = Record<string, RuleValue>;

export interface ShipperDetail {
  settings: ShipperValues;
  differs_from_default: string[];
  default: ShipperValues;
  rebuilt?: { bls: number; removed: number; kept: number };
}

export interface DryRunDecl {
  declaration_id: string;
  rows: string[];
  records: string[];
  warnings: string[];
}

export interface DryRunOut {
  source: string;
  before: DryRunDecl[];
  after: DryRunDecl[];
  changed: { key: string; label: string; before: RuleValue; after: RuleValue }[];
  row_count: { before: number; after: number };
}
