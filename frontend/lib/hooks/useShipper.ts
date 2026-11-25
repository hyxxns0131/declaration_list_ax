"use client";
// 화주 목록 + 고른 화주(모든 탭·사이드바 화면이 같은 값을 쓴다, localStorage). 담당: KHS
// 탭 1 기업 설정 첫 화면에서 "작업할 화주"를 먼저 고른다(HS 요청 11/25). 한 곳에서 바꾸면 같은 화면의 다른 부품
// (예: 위 줄의 '작업 화주' 표시, 화면별 화주 드롭다운)도 바로 바뀌도록 창 이벤트로 알린다.
import { useCallback, useEffect, useState } from "react";

import { shippers as getShippers } from "@/lib/api/core";
import type { Shipper } from "@/lib/types/core";

export const SHIPPER_KEY = "dl_shipper";
const CHANGED = "dl-shipper-changed";

/** 작업 화주 저장 + 같은 화면의 다른 부품(사이드바 '작업 화주' 등)에 알림. 화면에서 직접 setItem하지 말고 이것을 쓴다. */
export function rememberShipper(id: string): void {
  if (!id) return;
  window.localStorage.setItem(SHIPPER_KEY, id);
  window.dispatchEvent(new Event(CHANGED));
}

/** 작업 화주 지우기(그 화주를 삭제했을 때). */
export function forgetShipper(): void {
  window.localStorage.removeItem(SHIPPER_KEY);
  window.dispatchEvent(new Event(CHANGED));
}

export function useShipper() {
  const [shippers, setShippers] = useState<Shipper[]>([]);
  const [shipperId, setId] = useState("");
  const [chosen, setChosen] = useState(false); // 담당자가 고른 화주가 저장돼 있고 목록에 있다
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const reload = useCallback(async (): Promise<Shipper[]> => {
    try {
      const list = await getShippers();
      setShippers(list);
      const saved = window.localStorage.getItem(SHIPPER_KEY);
      const hit = list.find((s) => s.shipper_id === saved);
      setChosen(Boolean(hit));
      // 고른 적이 없으면 화면이 비지 않게 첫 화주를 임시로 쓴다(홈은 chosen=false면 먼저 고르게 한다)
      setId(hit?.shipper_id ?? list[0]?.shipper_id ?? "");
      setError(null);
      return list;
    } catch (e) {
      setError(e);
      return [];
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void reload();
    const sync = () => void reload();
    window.addEventListener(CHANGED, sync);
    window.addEventListener("storage", sync); // 다른 창에서 바꾼 경우
    return () => {
      window.removeEventListener(CHANGED, sync);
      window.removeEventListener("storage", sync);
    };
  }, [reload]);

  const setShipperId = useCallback((id: string) => {
    setId(id);
    if (!id) return;
    setChosen(true);
    rememberShipper(id);
  }, []);

  const shipperName = shippers.find((s) => s.shipper_id === shipperId)?.display_name ?? shipperId;
  return { shippers, shipperId, setShipperId, shipperName, chosen, loaded, reload, error };
}
