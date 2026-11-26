"use client";
// 단계 표시줄·사이드바 단계 표시가 같이 쓰는 GET /history/steps. 서류 올리기·새로고침·검수 저장 뒤
// notifyListChanged()로 다시 읽는다. 담당: KHS (검역 리스트 탭 0단계)
import { useEffect, useState } from "react";

import { getSteps } from "@/lib/api/history";
import type { ListSteps } from "@/lib/types/history";

const CHANGED = "dl-list-changed";

export function notifyListChanged(): void {
  window.dispatchEvent(new Event(CHANGED));
}

export function useListSteps(shipperId: string): ListSteps | null {
  const [data, setData] = useState<ListSteps | null>(null);
  useEffect(() => {
    if (!shipperId) return;
    let alive = true;
    const load = () =>
      getSteps(shipperId)
        .then((d) => alive && setData(d))
        .catch(() => alive && setData(null));
    load();
    window.addEventListener(CHANGED, load);
    return () => {
      alive = false;
      window.removeEventListener(CHANGED, load);
    };
  }, [shipperId]);
  return data;
}
