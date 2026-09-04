import { useCallback, useEffect, useState } from "react";
import { useWatchlists } from "./queries";

const KEY = "market_detective.active_watchlist";

export function useActiveWatchlist() {
  const { data: watchlists, isLoading } = useWatchlists();
  const [activeId, setActiveId] = useState<string | undefined>(() => {
    try {
      return localStorage.getItem(KEY) ?? undefined;
    } catch {
      return undefined;
    }
  });

  useEffect(() => {
    if (!watchlists || watchlists.length === 0) return;
    const exists = activeId && watchlists.some((w) => w.id === activeId);
    if (!exists) {
      setActiveId(watchlists[0].id);
    }
  }, [watchlists, activeId]);

  const setActive = useCallback((id: string) => {
    setActiveId(id);
    try {
      localStorage.setItem(KEY, id);
    } catch {
      /* ignore */
    }
  }, []);

  const active = watchlists?.find((w) => w.id === activeId) ?? watchlists?.[0];

  return { activeId: active?.id, active, setActive, watchlists, isLoading };
}
