export interface Stock {
  ticker: string;
  name: string;
  sector?: string;
  price: number;
  change_percent: number;
}

export interface Sector {
  name: string;
  description: string;
  stocks: Stock[];
  relatedCommodities?: string[];
}

export interface TechnicalIndicators {
  rsi: number;
  macd: number;
  macd_signal: number;
  bollinger_upper: number;
  bollinger_middle: number;
  bollinger_lower: number;
  sma_20: number;
  sma_50: number;
  sma_200: number | null;
  buy_sell_signal: string;
}

export interface AnalysisResult {
  ticker: string;
  name?: string;
  recommendation: string;
  confidence_score: number;
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
  sma_20?: number;
  sma_50?: number;
  sma_200?: number;
  bollinger_upper?: number;
  bollinger_middle?: number;
  bollinger_lower?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
}

export interface NewsArticle {
  title: string;
  url: string;
  source: string;
  publishedAt: string;
  summary: string;
}

export interface CommodityPrice {
  name: string;
  nameKo?: string;
  price: number;
  change: number;
  changePercent: number;
  unit?: string;
}
