// 표시 형식: 날짜 YYYY.MM.DD, 금액 천 단위 쉼표 (DESIGN 8장). 담당: KHS
import type { CellValue, Field } from "@/lib/types/history";

export function fmtDate(v: string | null | undefined): string {
  if (!v) return "";
  const m = /^(\d{4})[-./]?(\d{1,2})[-./]?(\d{1,2})/.exec(v);
  return m ? `${m[1]}.${m[2].padStart(2, "0")}.${m[3].padStart(2, "0")}` : v;
}

export function fmtNumber(v: CellValue | undefined, digits = 2): string {
  if (v === null || v === undefined || v === "") return "";
  const n = typeof v === "number" ? v : Number(String(v).replace(/,/g, ""));
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

/** 화면에 보일 값: final_value가 있으면 그것(AGENTS 0-5). */
export function shown(f: Field | undefined): CellValue {
  if (!f) return null;
  return f.final_value !== null && f.final_value !== undefined ? f.final_value : f.ai_value;
}

const DATE_COLS = new Set(["반입일", "입항일", "선적일", "검역 신고일자"]);
const NUM_COLS = new Set(["입수", "카톤 수", "순중량", "가격(USD)", "USD 환율", "가격(수출국)", "CI 통화 환율"]);

export function fmtCell(column: string, v: CellValue): string {
  if (v === null || v === undefined) return "";
  if (DATE_COLS.has(column)) return fmtDate(String(v));
  if (NUM_COLS.has(column)) return fmtNumber(v);
  return String(v);
}
