import axios from "axios";
import type {
  AnalysisResult,
  ChartDataPoint,
  CommodityPrice,
  NewsArticle,
  Sector,
  Stock,
} from "@/types";

const api = axios.create({
  baseURL: "/api",
  timeout: 60000, // 60s timeout for slow endpoints like checklist-live
});

// Auto-retry on failure (network errors, timeouts, 5xx)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (!config || config._retryCount >= 2) return Promise.reject(error);
    const status = error.response?.status;
    const isRetryable = !status || status >= 500 || error.code === "ECONNABORTED";
    if (!isRetryable) return Promise.reject(error);
    config._retryCount = (config._retryCount || 0) + 1;
    await new Promise((r) => setTimeout(r, 1000 * config._retryCount));
    return api(config);
  }
);

type ChartApiResponse = {
  ticker: string;
  data: ChartDataPoint[];
  indicators?: Record<string, (number | null)[]>;
};

export async function fetchSectors(): Promise<Sector[]> {
  const res = await api.get<Sector[]>("/sectors");
  return res.data;
}

export async function fetchSectorStocks(sectorName: string): Promise<Stock[]> {
  const res = await api.get<Stock[]>(`/sectors/${encodeURIComponent(sectorName)}/stocks`);
  return res.data;
}

export async function fetchAnalysis(ticker: string): Promise<AnalysisResult> {
  const res = await api.get<AnalysisResult>(`/analysis/${encodeURIComponent(ticker)}`);
  return res.data;
}

export async function fetchChartData(
  ticker: string,
  period: string = "6mo"
): Promise<ChartDataPoint[]> {
  const res = await api.get<ChartApiResponse>(
    `/analysis/${encodeURIComponent(ticker)}/chart-data`,
    { params: { period } }
  );

  const { data, indicators } = res.data;
  if (!indicators) {
    return data;
  }

  return data.map((point, index) => ({
    ...point,
    sma_20: indicators.sma_20?.[index] ?? point.sma_20,
    sma_50: indicators.sma_50?.[index] ?? point.sma_50,
    sma_200: indicators.sma_200?.[index] ?? point.sma_200,
    bollinger_upper: indicators.bollinger_upper?.[index] ?? point.bollinger_upper,
    bollinger_middle: indicators.bollinger_middle?.[index] ?? point.bollinger_middle,
    bollinger_lower: indicators.bollinger_lower?.[index] ?? point.bollinger_lower,
    rsi: indicators.rsi?.[index] ?? point.rsi,
    macd: indicators.macd?.[index] ?? point.macd,
    macd_signal: indicators.macd_signal?.[index] ?? point.macd_signal,
    macd_histogram: indicators.macd_histogram?.[index] ?? point.macd_histogram,
  }));
}

export async function fetchNews(sectorName: string): Promise<NewsArticle[]> {
  const res = await api.get<NewsArticle[]>(`/news/${encodeURIComponent(sectorName)}`);
  return res.data;
}

export async function fetchCommodities(): Promise<CommodityPrice[]> {
  const res = await api.get<CommodityPrice[]>("/commodities");
  return res.data;
}

export async function searchNews(keyword: string): Promise<NewsArticle[]> {
  const res = await api.get<NewsArticle[]>(`/news/search/${encodeURIComponent(keyword)}`);
  return res.data;
}

export async function fetchEarnings(ticker: string): Promise<any> {
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/earnings`);
  return res.data;
}

export async function fetchPatternAnalysis(ticker: string): Promise<any> {
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/pattern`);
  return res.data;
}

export async function fetchCommodityHistory(
  symbol: string,
  period: string = "6mo"
): Promise<{ date: string; close: number }[]> {
  const res = await api.get<{ symbol: string; data: { date: string; close: number }[] }>(
    `/commodities/history/${encodeURIComponent(symbol)}`,
    { params: { period } }
  );
  return res.data.data;
}

export async function fetchPrediction(ticker: string): Promise<any> {
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/prediction`);
  return res.data;
}

export async function fetchMoveReasons(ticker: string, period: string = "3mo"): Promise<any> {
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/move-reasons`, {
    params: { period },
  });
  return res.data;
}

export async function fetchChecklistLive(ticker: string): Promise<any> {
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/checklist-live`);
  return res.data;
}

export async function fetchSectorPulse(sectorId: string): Promise<any> {
  const res = await api.get(`/analysis/sector/${encodeURIComponent(sectorId)}/pulse`);
  return res.data;
}

export async function searchStocks(query: string): Promise<any> {
  const res = await api.get(`/analysis/stock-search/${encodeURIComponent(query)}`);
  return res.data;
}
