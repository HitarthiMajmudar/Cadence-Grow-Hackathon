export type Freshness = "fresh" | "delayed" | "stale" | "missing" | "conflicting";
export type Severity = "critical" | "high" | "moderate" | "low" | "minimal";
export type CaseStatus = "new" | "viewed" | "saved" | "dismissed";
export type ChangeClass =
  | "important"
  | "investigating"
  | "explained"
  | "normal"
  | "insufficient_data";
export type DetectiveStatus = "supports" | "opposes" | "inconclusive";

export interface UserPreferences {
  default_watchlist_id: string | null;
  attention_threshold: number;
  daily_attention_budget: string;
  reduced_motion: boolean;
  theme: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
  last_login_at: string;
  preferences: UserPreferences;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LiveSymbolMatch {
  symbol: string;
  name: string;
  exchange: string;
  mic_code: string | null;
  country: string | null;
  currency: string | null;
  instrument_type: string | null;
}

export interface LiveQuote {
  symbol: string;
  name: string;
  exchange: string;
  currency: string | null;
  price: number;
  previous_close: number | null;
  change: number | null;
  change_pct: number | null;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  is_market_open: boolean | null;
  as_of: string | null;
}

export interface LiveCandle {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface LiveHistoryResponse {
  symbol: string;
  exchange: string | null;
  interval: string;
  candles: LiveCandle[];
}

export interface StockMeta {
  symbol: string;
  name: string;
  sector: string;
  sector_name: string;
  index: string;
  weight: number;
  currency: string;
  summary: string;
}

export interface StockState {
  symbol: string;
  name: string;
  sector: string;
  sector_name: string;
  as_of: string;
  price: number | null;
  previous_close: number | null;
  change_pct: number | null;
  change_abs: number | null;
  day_volume: number;
  attention_score: number;
  confidence: number;
  severity: Severity;
  verdict: string | null;
  freshness: Freshness;
  spark: number[];
  open_case_id: string | null;
}

export interface WatchlistItem {
  symbol: string;
  name: string;
  sector: string;
  sector_name: string;
  latest_price: number | null;
  previous_close: number | null;
  change_pct: number | null;
  change_abs: number | null;
  attention_score: number;
  severity: Severity;
  freshness: Freshness;
  verdict: string | null;
  spark: number[];
  open_case_id: string | null;
}

export interface Watchlist {
  id: string;
  user_id: string;
  name: string;
  symbols: string[];
  attention_threshold: number;
  daily_attention_budget: string;
  created_at: string;
  updated_at: string;
}

export interface WatchlistDetail extends Watchlist {
  items: WatchlistItem[];
  dataset_timestamp: string | null;
}

export interface DemoClock {
  user_id: string;
  current_dataset_timestamp: string;
  dataset_first_timestamp: string;
  dataset_last_timestamp: string;
  default_present_timestamp: string;
  bars_from_present: number;
  bars_to_end: number;
  is_at_end: boolean;
  updated_at: string;
  dataset_label: string;
  demo_mode: boolean;
}

export interface ClockAdvanceResult {
  clock: DemoClock;
  advanced_bars: number;
  market_hours_advanced: number;
  from_timestamp: string;
  to_timestamp: string;
  new_case_ids: string[];
}

export interface ScoreComponent {
  key: string;
  label: string;
  points: number;
  max_points: number;
  detail: string;
}

export interface Evidence {
  kind: "supporting" | "counter" | "quality";
  label: string;
  detail: string;
  metric?: string | null;
  value?: number | null;
}

export interface DetectiveFinding {
  detective: string;
  key: "stock" | "volume" | "sector" | "news";
  finding: string;
  evidence: string[];
  confidence: number;
  status: DetectiveStatus;
}

export interface RelatedNews {
  id: string;
  timestamp: string;
  headline: string;
  source: string;
  event_type: string;
  sentiment_label: string;
  sentiment_score: number;
  minutes_from_detection: number;
  relevance: number;
}

export interface DataQuality {
  freshness: Freshness;
  confidence_penalty: number;
  warnings: string[];
  sources_considered: string[];
  resolved_source: string | null;
  conflict_detail: string | null;
  events: any[];
}

export interface AttentionBreakdown {
  score: number;
  confidence: number;
  severity: string;
  components: ScoreComponent[];
  top_reasons: string[];
  supporting_evidence: Evidence[];
  counter_evidence: Evidence[];
  data_quality_warnings: string[];
  signal_agreement: number;
  agreeing_axes: string[];
}

export interface CaseSummary {
  id: string;
  case_id: string;
  symbol: string;
  company_name: string;
  sector: string;
  sector_name: string;
  detection_timestamp: string;
  comparison_start: string;
  comparison_end: string;
  attention_score: number;
  confidence: number;
  severity: Severity;
  verdict: string;
  headline_explanation: string;
  explanation: string;
  created_at: string;
  status: CaseStatus;
  viewed_at: string | null;
  is_seen: boolean;
  peers_in_move?: number;
  spark?: number[];
}

export interface CaseDetail extends CaseSummary {
  breakdown: AttentionBreakdown;
  detectives: DetectiveFinding[];
  score_components: ScoreComponent[];
  supporting_evidence: Evidence[];
  counter_evidence: Evidence[];
  related_news: RelatedNews[];
  data_quality: DataQuality;
  metrics: Record<string, number>;
  spark: number[];
  price_series: { timestamp: string; close: number | null; volume: number; attention_score: number }[];
  court_tally: { supports: number; opposes: number; inconclusive: number; split: boolean; net: number };
  verdict_reason?: string;
  feedback_summary?: Record<string, number>;
}

export interface CaseListResponse {
  needs_attention: CaseSummary[];
  still_investigating: CaseSummary[];
  explained: CaseSummary[];
  total: number;
  threshold: number;
  budget: string;
  budget_label: string;
  page: number;
  page_size: number;
}

export interface StockChange {
  symbol: string;
  name: string;
  sector: string;
  classification: ChangeClass;
  price_then: number | null;
  price_now: number | null;
  price_change_pct: number | null;
  attention_then: number;
  attention_now: number;
  attention_delta: number;
  freshness: Freshness;
  verdict: string | null;
  headline: string;
  new_case_id: string | null;
  new_case_score: number | null;
}

export interface Briefing {
  watchlist_id: string;
  watchlist_name: string;
  has_previous_snapshot: boolean;
  snapshot_acknowledged_at: string | null;
  snapshot_dataset_timestamp: string | null;
  current_dataset_timestamp: string;
  hours_away: number;
  market_hours_away: number;
  total_changes: number;
  changes_worth_attention: number;
  summary_line: string;
  threshold: number;
  budget: string;
  changes: StockChange[];
  new_case_ids: string[];
  counts: Record<string, number>;
}

export interface ComparisonPoint {
  timestamp: string;
  stock_indexed: number;
  sector_indexed: number;
  market_indexed: number;
}

export interface ComparisonSeries {
  symbol: string;
  sector: string;
  market_index: string;
  start: string;
  end: string;
  points: ComparisonPoint[];
  stock_return_pct: number;
  sector_return_pct: number;
  market_return_pct: number;
  who_moved_first: string | null;
}

export interface Candle {
  timestamp: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number;
  freshness: Freshness;
  source: string;
}

export interface ReplayFrame {
  index: number;
  timestamp: string;
  close: number | null;
  volume: number;
  stock_indexed: number;
  sector_indexed: number;
  market_indexed: number;
  attention_score: number;
  confidence: number;
  verdict: string;
  severity: string;
  freshness: Freshness;
  return_zscore: number;
  volume_ratio: number;
  is_anomaly: boolean;
  anomaly_level: "none" | "moderate" | "serious";
  case_id: string | null;
  news_ids: string[];
}

export interface ReplayNewsMarker {
  id: string;
  timestamp: string;
  frame_index: number;
  headline: string;
  event_type: string;
  sentiment_label: string;
  sentiment_score: number;
}

export interface ReplayAnomalyMarker {
  frame_index: number;
  timestamp: string;
  level: string;
  attention_score: number;
  verdict: string;
  case_id: string | null;
  label: string;
}

export interface ReplayResponse {
  symbol: string;
  company_name: string;
  sector: string;
  market_index: string;
  start: string;
  end: string;
  frame_count: number;
  bars_per_day: number;
  frames: ReplayFrame[];
  news_markers: ReplayNewsMarker[];
  anomaly_markers: ReplayAnomalyMarker[];
  score_evolution: { timestamp: string; attention_score: number; confidence: number }[];
  who_moved_first: string | null;
  first_mover_detail: string;
  dataset_label: string;
}

export interface StoryCardData {
  case_id: string;
  symbol: string;
  company_name: string;
  event_date: string;
  attention_score: number;
  confidence: number;
  severity: string;
  verdict: string;
  one_line: string;
  main_evidence: string[];
  sparkline: number[];
  dataset_label: string;
  generated_at: string;
  disclaimer: string;
}

export interface DataQualityEventOut {
  id: string;
  symbol: string;
  timestamp: string;
  status: Freshness;
  sources: any[];
  details: string;
  confidence_penalty: number;
}

export interface DatasetHealth {
  dataset_label: string;
  dataset_first_timestamp: string;
  dataset_last_timestamp: string;
  current_dataset_timestamp: string;
  freshness_overall: Freshness;
  freshness_status_text: string;
  total_observations: number;
  symbols_tracked: number;
  symbols_with_issues: string[];
  missing_bars: number;
  stale_bars: number;
  conflicting_bars: number;
  events: DataQualityEventOut[];
  per_symbol: {
    symbol: string;
    freshness: Freshness;
    last_observation: string | null;
    bars_missing_recent: number;
    events: DataQualityEventOut[];
    confidence_penalty: number;
  }[];
}

export interface Health {
  status: string;
  db_backend: string;
  db_connected: boolean;
  dataset_label: string;
  dataset_first_timestamp: string;
  dataset_last_timestamp: string;
  dataset_present_timestamp: string;
  sentiment_model: string;
  scored_bars: number;
  cases: number;
}
