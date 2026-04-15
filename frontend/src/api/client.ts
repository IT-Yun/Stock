import axios from "axios";
import type {
  Sector,
  Stock,
  AnalysisResult,
  ChartDataPoint,
  NewsArticle,
  CommodityPrice,
} from "@/types";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

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
  const res = await api.get<{ ticker: string; data: ChartDataPoint[] }>(
    `/analysis/${encodeURIComponent(ticker)}/chart-data`,
    { params: { period } }
  );
  return res.data.data;
}

export async function fetchNews(sectorName: string): Promise<NewsArticle[]> {
  const res = await api.get<NewsArticle[]>(
    `/news/${encodeURIComponent(sectorName)}`
  );
  return res.data;
}

export async function fetchCommodities(): Promise<CommodityPrice[]> {
  const res = await api.get<CommodityPrice[]>("/commodities");
  return res.data;
}

export async function searchNews(keyword: string): Promise<NewsArticle[]> {
  const res = await api.get<NewsArticle[]>(
    `/news/search/${encodeURIComponent(keyword)}`
  );
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

export async function fetchCommodityHistory(symbol: string, period: string = "6mo"): Promise<{ date: string; close: number }[]> {
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
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/move-reasons`, { params: { period } });
  return res.data;
}

export async function fetchChecklistLive(ticker: string): Promise<any> {
  const res = await api.get(`/analysis/${encodeURIComponent(ticker)}/checklist-live`);
  return res.data;
}
