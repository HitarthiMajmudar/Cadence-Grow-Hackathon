import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/endpoints";

export const qk = {
  health: ["health"] as const,
  clock: ["clock"] as const,
  watchlists: ["watchlists"] as const,
  watchlist: (id: string) => ["watchlist", id] as const,
  briefing: (id: string) => ["briefing", id] as const,
  cases: (id: string, budget?: string) => ["cases", id, budget ?? "default"] as const,
  case: (id: string) => ["case", id] as const,
  recentCases: ["cases", "recent"] as const,
  stocks: ["stocks"] as const,
  stockState: (s: string) => ["stock", s, "state"] as const,
  stockHistory: (s: string) => ["stock", s, "history"] as const,
  comparison: (s: string) => ["stock", s, "comparison"] as const,
  stockNews: (s: string) => ["stock", s, "news"] as const,
  stockCases: (s: string) => ["stock", s, "cases"] as const,
  replay: (s: string, lb: number) => ["replay", s, lb] as const,
  datasetHealth: ["dataset-health"] as const,
};

export const useHealth = () => useQuery({ queryKey: qk.health, queryFn: api.health, staleTime: 60_000 });
export const useClock = () => useQuery({ queryKey: qk.clock, queryFn: api.clock });
export const useWatchlists = () => useQuery({ queryKey: qk.watchlists, queryFn: api.watchlists });
export const useWatchlist = (id?: string) =>
  useQuery({ queryKey: qk.watchlist(id ?? ""), queryFn: () => api.watchlist(id!), enabled: !!id });
export const useBriefing = (id?: string) =>
  useQuery({ queryKey: qk.briefing(id ?? ""), queryFn: () => api.briefing(id!), enabled: !!id });
export const useCases = (watchlistId?: string, budget?: string) =>
  useQuery({
    queryKey: qk.cases(watchlistId ?? "", budget),
    queryFn: () => api.cases({ watchlist_id: watchlistId, budget }),
    enabled: !!watchlistId,
  });
export const useCase = (caseId?: string) =>
  useQuery({ queryKey: qk.case(caseId ?? ""), queryFn: () => api.case(caseId!), enabled: !!caseId });
export const useRecentCases = () =>
  useQuery({ queryKey: qk.recentCases, queryFn: api.recentCases });
export const useStocks = () => useQuery({ queryKey: qk.stocks, queryFn: api.stocks, staleTime: 300_000 });
export const useStockState = (s?: string) =>
  useQuery({ queryKey: qk.stockState(s ?? ""), queryFn: () => api.stockState(s!), enabled: !!s });
export const useStockHistory = (s?: string) =>
  useQuery({
    queryKey: qk.stockHistory(s ?? ""),
    queryFn: () => api.stockHistory(s!, { page_size: 1200 }),
    enabled: !!s,
  });
export const useComparison = (s?: string, lookback = 80) =>
  useQuery({
    queryKey: [...qk.comparison(s ?? ""), lookback],
    queryFn: () => api.stockComparison(s!, lookback),
    enabled: !!s,
  });
export const useStockNews = (s?: string) =>
  useQuery({ queryKey: qk.stockNews(s ?? ""), queryFn: () => api.stockNews(s!), enabled: !!s });
export const useStockCases = (s?: string) =>
  useQuery({ queryKey: qk.stockCases(s ?? ""), queryFn: () => api.stockCases(s!), enabled: !!s });
export const useReplay = (s?: string, lookback = 90) =>
  useQuery({
    queryKey: qk.replay(s ?? "", lookback),
    queryFn: () => api.replay(s!, { lookback_bars: lookback }),
    enabled: !!s,
  });
export const useDatasetHealth = () =>
  useQuery({ queryKey: qk.datasetHealth, queryFn: api.datasetHealth });

export function useAdvanceClock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bars?: number) => api.advanceClock(bars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clock"] });
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      qc.invalidateQueries({ queryKey: ["briefing"] });
      qc.invalidateQueries({ queryKey: ["cases"] });
      qc.invalidateQueries({ queryKey: ["stock"] });
      qc.invalidateQueries({ queryKey: ["dataset-health"] });
    },
  });
}

export function useResetClock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.resetClock(),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useMarkBriefingSeen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ watchlistId, ids }: { watchlistId: string; ids?: string[] }) =>
      api.markBriefingSeen(watchlistId, ids ?? []),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["briefing"] });
      qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useWatchlistMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["watchlists"] });
    qc.invalidateQueries({ queryKey: ["watchlist"] });
    qc.invalidateQueries({ queryKey: ["briefing"] });
    qc.invalidateQueries({ queryKey: ["cases"] });
  };
  return {
    create: useMutation({ mutationFn: api.createWatchlist, onSuccess: invalidate }),
    rename: useMutation({
      mutationFn: ({ id, name }: { id: string; name: string }) => api.renameWatchlist(id, name),
      onSuccess: invalidate,
    }),
    remove: useMutation({ mutationFn: (id: string) => api.deleteWatchlist(id), onSuccess: invalidate }),
    addSymbol: useMutation({
      mutationFn: ({ id, symbol }: { id: string; symbol: string }) => api.addSymbol(id, symbol),
      onSuccess: invalidate,
    }),
    removeSymbol: useMutation({
      mutationFn: ({ id, symbol }: { id: string; symbol: string }) => api.removeSymbol(id, symbol),
      onSuccess: invalidate,
    }),
    settings: useMutation({
      mutationFn: ({ id, ...body }: { id: string; attention_threshold?: number; daily_attention_budget?: string }) =>
        api.updateWatchlistSettings(id, body),
      onSuccess: invalidate,
    }),
  };
}
