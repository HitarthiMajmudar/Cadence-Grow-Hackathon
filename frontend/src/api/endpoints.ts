import { apiFetch } from "./client";
import type {
  AuthResponse,
  Briefing,
  CaseDetail,
  CaseListResponse,
  CaseSummary,
  Candle,
  ComparisonSeries,
  DatasetHealth,
  DemoClock,
  ClockAdvanceResult,
  Health,
  LiveHistoryResponse,
  LiveQuote,
  LiveSymbolMatch,
  RelatedNews,
  ReplayResponse,
  StockMeta,
  StockState,
  StoryCardData,
  User,
  Watchlist,
  WatchlistDetail,
} from "@/types";

export const api = {
  health: () => apiFetch<Health>("/health", { auth: false }),

  signup: (name: string, email: string, password: string) =>
    apiFetch<AuthResponse>("/auth/signup", { method: "POST", body: { name, email, password }, auth: false }),
  login: (email: string, password: string) =>
    apiFetch<AuthResponse>("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
  me: () => apiFetch<User>("/auth/me"),
  updatePreferences: (body: Record<string, unknown>) =>
    apiFetch<User>("/auth/me/preferences", { method: "PATCH", body }),

  liveSearch: (q: string) => apiFetch<LiveSymbolMatch[]>("/live/search", { params: { q } }),
  liveQuote: (symbol: string, exchange?: string) =>
    apiFetch<LiveQuote>(`/live/${symbol}/quote`, { params: { exchange } }),
  liveHistory: (symbol: string, exchange?: string, outputsize = 180) =>
    apiFetch<LiveHistoryResponse>(`/live/${symbol}/history`, { params: { exchange, outputsize } }),

  stocks: () => apiFetch<StockMeta[]>("/stocks", { auth: false }),
  searchStocks: (q: string) => apiFetch<StockMeta[]>("/stocks/search", { params: { q }, auth: false }),
  stockState: (symbol: string) => apiFetch<StockState>(`/stocks/${symbol}/state`),
  stockHistory: (symbol: string, params?: Record<string, string | number | boolean>) =>
    apiFetch<{ symbol: string; candles: Candle[]; total: number; page: number; page_size: number }>(
      `/stocks/${symbol}/history`,
      { params },
    ),
  stockComparison: (symbol: string, lookback_bars = 70) =>
    apiFetch<ComparisonSeries>(`/stocks/${symbol}/comparison`, { params: { lookback_bars } }),
  stockNews: (symbol: string) =>
    apiFetch<{ symbol: string; news: RelatedNews[] }>(`/stocks/${symbol}/news`),
  stockCases: (symbol: string) =>
    apiFetch<{ symbol: string; cases: CaseSummary[] }>(`/stocks/${symbol}/cases`),

  watchlists: () => apiFetch<Watchlist[]>("/watchlists"),
  watchlist: (id: string) => apiFetch<WatchlistDetail>(`/watchlists/${id}`),
  createWatchlist: (body: { name: string; symbols?: string[]; attention_threshold?: number; daily_attention_budget?: string }) =>
    apiFetch<WatchlistDetail>("/watchlists", { method: "POST", body }),
  renameWatchlist: (id: string, name: string) =>
    apiFetch<Watchlist>(`/watchlists/${id}`, { method: "PATCH", body: { name } }),
  deleteWatchlist: (id: string) => apiFetch<void>(`/watchlists/${id}`, { method: "DELETE" }),
  addSymbol: (id: string, symbol: string) =>
    apiFetch<WatchlistDetail>(`/watchlists/${id}/symbols`, { method: "POST", body: { symbol } }),
  removeSymbol: (id: string, symbol: string) =>
    apiFetch<WatchlistDetail>(`/watchlists/${id}/symbols/${symbol}`, { method: "DELETE" }),
  updateWatchlistSettings: (id: string, body: { attention_threshold?: number; daily_attention_budget?: string }) =>
    apiFetch<Watchlist>(`/watchlists/${id}/settings`, { method: "PATCH", body }),
  attentionBudgets: () =>
    apiFetch<{ budgets: { id: string; label: string }[] }>("/watchlists/meta/attention-budgets", { auth: false }),

  briefing: (watchlistId: string) =>
    apiFetch<Briefing>("/briefings", { params: { watchlist_id: watchlistId } }),
  markBriefingSeen: (watchlistId: string, seenCaseIds: string[] = []) =>
    apiFetch<{ acknowledged_at: string; dataset_timestamp: string; seen_case_ids: string[] }>(
      "/briefings/mark-seen",
      { method: "POST", body: { watchlist_id: watchlistId, seen_case_ids: seenCaseIds } },
    ),

  cases: (params: { watchlist_id?: string; scope?: string; budget?: string; threshold?: number }) =>
    apiFetch<CaseListResponse>("/cases", { params }),
  case: (caseId: string) => apiFetch<CaseDetail>(`/cases/${caseId}`),
  recentCases: () => apiFetch<{ cases: CaseSummary[] }>("/cases/recent"),
  setCaseStatus: (caseId: string, status: string) =>
    apiFetch<{ case_id: string; status: string }>(`/cases/${caseId}/status`, {
      method: "PATCH",
      body: { status },
    }),
  submitFeedback: (caseId: string, feedback: string, note?: string) =>
    apiFetch<{ case_id: string; summary: Record<string, number> }>(`/cases/${caseId}/feedback`, {
      method: "POST",
      body: { feedback, note },
    }),
  storyCard: (caseId: string) => apiFetch<StoryCardData>(`/cases/${caseId}/story-card`),

  replay: (symbol: string, params?: Record<string, string | number>) =>
    apiFetch<ReplayResponse>(`/replay/${symbol}`, { params }),

  clock: () => apiFetch<DemoClock>("/demo-clock"),
  advanceClock: (bars?: number) =>
    apiFetch<ClockAdvanceResult>("/demo-clock/advance", { method: "POST", body: bars ? { bars } : {} }),
  resetClock: () => apiFetch<DemoClock>("/demo-clock/reset", { method: "POST" }),

  datasetHealth: () => apiFetch<DatasetHealth>("/data-quality/health"),
  symbolQuality: (symbol: string) => apiFetch<any>(`/data-quality/${symbol}`),
};
