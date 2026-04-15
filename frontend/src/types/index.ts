export interface Stock {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: number;
}

export interface Sector {
  name: string;
  description: string;
  stocks: Stock[];
  relatedCommodities: string[];
}

export interface TechnicalIndicators {
  rsi: number;
  rsiSignal: string;
  macdLine: number;
  macdSignal: number;
  macdHistogram: number;
  macdInterpretation: string;
  sma20: number;
  sma50: number;
  sma200: number;
  smaTrend: string;
  bollingerUpper: number;
  bollingerMiddle: number;
  bollingerLower: number;
  bollingerPosition: string;
}

export interface AnalysisResult {
  ticker: string;
  name: string;
  recommendation: "strong_buy" | "buy" | "hold" | "sell" | "strong_sell";
  confidence: number;
  indicators: TechnicalIndicators;
  summary: string;
}

export interface ChartDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20?: number;
  sma50?: number;
  sma200?: number;
  bollingerUpper?: number;
  bollingerMiddle?: number;
  bollingerLower?: number;
  rsi?: number;
  macdLine?: number;
  macdSignal?: number;
  macdHistogram?: number;
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
  nameKo: string;
  price: number;
  change: number;
  changePercent: number;
  unit: string;
}
