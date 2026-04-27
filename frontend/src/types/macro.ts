// Macro 4페이지 타입 정의 — backend/api/macro.py 응답 스키마와 일치

export interface CommodityEffect {
  sector: string;
  direction: string;
  tickers_kr: string[];
  tickers_us: string[];
  mechanism: string;
}

export interface CommodityItem {
  id: string;
  name: string;
  category: string;
  unit: string;
  ticker: string | null;
  is_hidden_bottleneck?: boolean;
  primary_effects: CommodityEffect[];
}

export interface CommodityFeedItem {
  id: string;
  name: string;
  category: string;
  unit: string;
  ticker: string | null;
  fetchable: boolean;
  is_proxy?: boolean;
  chartable?: boolean;
  source?: string;
  source_url?: string | null;
  source_type?: string;
  fetched_at?: string | null;
  data_as_of?: string | null;
  frequency?: string;
  confidence?: number;
  coverage_status?: string;
  proxy_for?: string | null;
  price?: number | null;
  change_pct_1d?: number | null;
  change_pct_5d?: number | null;
  change_pct_10d?: number | null;
  change_pct_20d?: number | null;
  change_pct_60d?: number | null;
  change_pct_120d?: number | null;
  zscore_60d?: number | null;
  is_anomalous?: boolean;
  is_surge?: boolean;
  is_plunge?: boolean;
  is_multi_month_uptrend?: boolean;
  is_multi_month_downtrend?: boolean;
  trend_label?: string | null;
  trend_score?: number | null;
  surge_reasons?: string[] | null;
  trend_reasons?: string[] | null;
  signal_type?: string;
  timing_action?: string;
  timing_score?: number;
  timing_reasons?: string[] | null;
  risk_notes?: string[] | null;
  driver_label?: string | null;
  cause_reasons?: string[] | null;
  bullish_thesis?: string | null;
  caution?: string | null;
  strategic_watch?: boolean;
  strategic_score?: number;
  strategic_label?: string | null;
  strategic_reasons?: string[] | null;
  fallback_url?: string | null;
  note?: string | null;
  is_hidden_bottleneck?: boolean;
  error?: string | null;
}

export interface MoversBundle {
  surges: CommodityFeedItem[];
  plunges: CommodityFeedItem[];
  uptrends?: CommodityFeedItem[];
  downtrends?: CommodityFeedItem[];
}

export interface CommoditiesResponse {
  status: string;
  total_commodities: number;
  categories: string[];
  items: CommodityItem[];
  insights: {
    top_signal_kr: string[];
    hidden_bottlenecks: string[];
  };
  feed: CommodityFeedItem[];
  movers: MoversBundle;
}

export interface SectorSentiment {
  sector_id: string;
  sentiment: "bullish" | "bearish" | "neutral";
  score: number;
  bullish_count: number;
  bearish_count: number;
  bullish_signals: string[];
  bearish_signals: string[];
  watch_signals?: string[];
  data_coverage: "commodity_only" | "core_watchlist" | "no_commodity_link" | "no_data";
  verdict?: string;
  key_takeaway?: string;
  leading_signals?: string[];
  next_checks?: string[];
  indicator_assessments?: {
    name: string;
    direction: "bullish" | "bearish" | "watch";
    reason: string;
  }[];
}

export interface SectorMeta {
  id: string;
  name: string;
  phase: 1 | 2;
  indicator_count: number;
  live_sentiment?: SectorSentiment;
}

export interface IndicatorItem {
  id: string;
  sector_id: string;
  sector_name: string;
  name: string;
  what: string;
  lead_time: string;
  source: { name: string; url: string; free: boolean; api?: boolean };
  tickers_kr: string[];
  tickers_us: string[];
  is_top_signal?: boolean;
}

export interface IndicatorsResponse {
  status: string;
  total_sectors: number;
  total_indicators: number;
  phases: { phase_1: number; phase_2: number };
  sectors: SectorMeta[];
  featured: IndicatorItem[];
  top_sectors?: {
    bullish_sectors: SectorSentiment[];
    bearish_sectors: SectorSentiment[];
  };
}

export interface MacroDimension {
  id: string;
  name: string;
  key_indicators: string[];
}

export interface MacroScenario {
  id: string;
  name: string;
  triggers: string[];
  favorable: string[];
  unfavorable: string[];
}

export interface LiveMacroIndicator {
  id: string;
  name: string;
  ticker: string;
  category: string;
  unit: string;
  price: number | null;
  change_pct_1d: number | null;
  change_pct_5d: number | null;
  change_pct_60d: number | null;
  zscore_60d: number | null;
  error: string | null;
}

export interface ActiveScenario {
  id: string;
  name: string;
  strength: number; // 0~1
  evidence: string[];
  favorable_sectors: string[];
  unfavorable_sectors: string[];
}

export interface CurrentMacroEvent {
  id: string;
  title: string;
  severity: number;
  status: string;
  evidence: string[];
  favorable_sectors: string[];
  unfavorable_sectors: string[];
  sector_impacts?: {
    sector_id: string;
    score: number;
    direction: "favorable" | "unfavorable";
    reason: string;
  }[];
  source_notes: string[];
}

export interface SynthesizedSector {
  sector_id: string;
  synthesis_score: number;
  synthesis_sentiment: "bullish" | "bearish" | "neutral";
  drivers: string[];
}

export interface OutlookResponse {
  status: string;
  live_indicators?: LiveMacroIndicator[];
  current_events?: CurrentMacroEvent[];
  active_scenarios?: ActiveScenario[];
  synthesis?: {
    top_sectors: SynthesizedSector[];
    bottom_sectors: SynthesizedSector[];
    all_sectors: SynthesizedSector[];
  };
  current_regime: {
    as_of: string;
    lei_6m_change: number;
    fed_target_range: string;
    hy_oas: number;
    vkospi: number;
    summary: string;
  };
  dimensions: MacroDimension[];
  scenarios: MacroScenario[];
  policy_alerts: string[];
}

export interface ValueChainPlayerKR {
  name: string;
  ticker: string;
}

export interface ValueChainTier {
  node_id?: string;
  level: 0 | 1 | 2 | 3 | 4 | 5;
  name: string;
  players: string[];
  players_kr?: ValueChainPlayerKR[];
  players_us?: string[];
  is_korean_alpha?: boolean;
  roles?: string[];
  signals?: string[];
  cost_drivers?: string[];
  signal_map?: string[];
  materials?: string[];
}

export interface ValueChainSector {
  sector_id: string;
  sector_no?: number;
  sector_name: string;
  tiers: ValueChainTier[];
  hidden_alpha: string;
  mermaid?: string;
  wiki_section_anchor?: string;
}

export interface HiddenAlphaItem {
  company: string;
  tickers: string[];
  thesis: string;
}

export interface ValueChainResponse {
  status: string;
  source?: string;
  total_sectors: number;
  total_kr_stocks: number | string;
  total_us_stocks: number | string;
  sectors: ValueChainSector[];
  hidden_alpha_top: HiddenAlphaItem[];
  warnings: string[];
}

export interface WikiPageResponse {
  name: string;
  filename: string;
  content: string;
  size_bytes: number;
}

export type MacroPageName = "commodities" | "indicators" | "outlook" | "value-chain";

// ────────────────────────────────────────────────────────────────
// Regime (5년 history 기반) — wiki/macro/05-regime-scoring.md
// ────────────────────────────────────────────────────────────────

export type RegimeLabel = "Sleeper" | "Breakout" | "Steady" | "Topping" | "Crash" | "Rebound";

export interface RegimeMetrics {
  price?: number;
  pct_5y?: number;
  pct_from_high_5y?: number;
  pct_from_low_5y?: number;
  ret_30d?: number | null;
  ret_60d?: number | null;
  ret_252d?: number | null;
  vol_60d_annualized?: number | null;
  vol_z?: number;
  trend_12m?: number | null;
  momentum_accel?: number | null;
  breakout_3y?: boolean;
  breakdown_3y?: boolean;
  data_points?: number;
}

export interface RegimeItem {
  id: string;
  name: string;
  category?: string;
  is_proxy?: boolean;
  current_regime: RegimeLabel;
  previous_regime?: RegimeLabel | null;
  previous_regime_days?: number;
  regime_since?: string;
  days_in_zone?: number;
  regime_change?: boolean;
  metrics?: RegimeMetrics;
  last_update?: string;
  recommendation?: string;
  recommendation_note?: string;
}

export interface RegimeResponse {
  updated: string | null;
  total_items: number;
  regime_changes_today: number;
  distribution: Record<RegimeLabel, RegimeItem[]>;
  changed_today: RegimeItem[];
  items: RegimeItem[];
  errors_last_run: { id: string; reason: string }[];
  recommendation_matrix: Record<RegimeLabel, { action: string; note: string }>;
}
