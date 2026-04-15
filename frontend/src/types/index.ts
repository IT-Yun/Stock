export interface Stock {
  ticker: string;
  name: string;
  sector?: string;
  price: number;
  change_percent: number;
  changePercent?: number;
  change?: number;
  volume?: number;
  marketCap?: number;
}

export interface Sector {
  name: string;
  description: string;
  stocks: Stock[];
  relatedCommodities?: string[];
}

export interface TechnicalIndicators {
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macdSignal?: number | null;
  bollinger_upper: number | null;
  bollingerUpper?: number | null;
  bollinger_middle: number | null;
  bollingerMiddle?: number | null;
  bollinger_lower: number | null;
  bollingerLower?: number | null;
  sma_20: number | null;
  sma20?: number | null;
  sma_50: number | null;
  sma50?: number | null;
  sma_200: number | null;
  sma200?: number | null;
  buy_sell_signal: string | null;
}

export interface AnalysisResult {
  ticker: string;
  name?: string;
  recommendation: "strong_buy" | "buy" | "hold" | "sell" | "strong_sell" | string;
  confidence_score: number;
  confidence?: number;
  indicators: TechnicalIndicators;
  summary?: string;
}

export interface ChartDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma_20?: number | null;
  sma_50?: number | null;
  sma_200?: number | null;
  bollinger_upper?: number | null;
  bollinger_middle?: number | null;
  bollinger_lower?: number | null;
  rsi?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_histogram?: number | null;
}

export interface NewsArticle {
  title: string;
  url: string;
  source: string;
  published_at?: string | null;
  publishedAt?: string;
  summary?: string | null;
}

export interface CommodityPrice {
  name: string;
  symbol: string;
  nameKo?: string;
  price: number;
  change_percent: number;
  change?: number;
  changePercent?: number;
  unit?: string;
}
