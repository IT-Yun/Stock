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
  timeout: 15000,
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
  period: string = "6M"
): Promise<ChartDataPoint[]> {
  const res = await api.get<ChartDataPoint[]>(
    `/chart/${encodeURIComponent(ticker)}`,
    { params: { period } }
  );
  return res.data;
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
  const res = await api.get<NewsArticle[]>("/news/search", {
    params: { keyword },
  });
  return res.data;
}
