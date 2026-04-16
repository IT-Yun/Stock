import axios from "axios";
import { SECTORS } from "@/data/sectors";
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

const inflightRequests = new Map<string, Promise<any>>();
const responseCachePrefix = "stock-api-cache:";
const responseCacheTtlMs = 1000 * 60 * 60 * 6;

function buildRequestKey(url: string, params?: unknown) {
  return `${url}::${JSON.stringify(params ?? null)}`;
}

function readResponseCache<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(`${responseCachePrefix}${key}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { ts: number; data: T };
    if (!parsed || typeof parsed.ts !== "number") return null;
    if (Date.now() - parsed.ts > responseCacheTtlMs) return parsed.data ?? null;
    return parsed.data ?? null;
  } catch {
    return null;
  }
}

function writeResponseCache<T>(key: string, data: T) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(
      `${responseCachePrefix}${key}`,
      JSON.stringify({ ts: Date.now(), data })
    );
  } catch {
    // Ignore quota/storage errors and keep runtime behavior intact.
  }
}

function buildStaticTopRankedFallback() {
  const rankings = SECTORS.flatMap((sector) =>
    sector.picks.map((pick) => ({
      ticker: pick.ticker,
      name: pick.name,
      price: 0,
      change_1m: null,
      score: 50,  // neutral — real scores come from API
      rsi: null,
      sector_id: sector.id,
      sector_name: sector.name,
      flag: pick.flag,
      source: "static-fallback",
    }))
  ).slice(0, 10);

  return { rankings };
}

function dedupedGet<T>(url: string, config?: { params?: unknown; timeout?: number }): Promise<{ data: T }> {
  const key = buildRequestKey(url, config?.params);
  const existing = inflightRequests.get(key);
  if (existing) {
    return existing;
  }

  const request = api
    .get<T>(url, config)
    .then((response) => {
      writeResponseCache(key, response.data);
      return response;
    })
    .catch((error) => {
      const fallback = readResponseCache<T>(key);
      if (fallback !== null) {
        return { data: fallback };
      }
      throw error;
    })
    .finally(() => {
      inflightRequests.delete(key);
    });
  inflightRequests.set(key, request);
  return request;
}

// Attach auth header to every request (URI-encode to avoid non-ASCII header errors)
api.interceptors.request.use((config) => {
  const nickname = localStorage.getItem("stock-nickname");
  if (nickname) {
    config.headers["X-Auth-Nickname"] = encodeURIComponent(nickname);
  }
  return config;
});

// Auto-retry on failure (network errors, timeouts, 5xx)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (!config || config._retryCount >= 2) return Promise.reject(error);
    const status = error.response?.status;
    // Retry on server errors, timeouts, and transient 403s (deployment race)
    const isRetryable = !status || status >= 500 || status === 403 || error.code === "ECONNABORTED";
    if (!isRetryable) return Promise.reject(error);
    config._retryCount = (config._retryCount || 0) + 1;
    await new Promise((r) => setTimeout(r, 1500 * config._retryCount));
    return api(config);
  }
);

type ChartApiResponse = {
  ticker: string;
  data: ChartDataPoint[];
  indicators?: Record<string, (number | null)[]>;
};

export async function fetchSectors(): Promise<Sector[]> {
  const res = await dedupedGet<Sector[]>("/sectors");
  return res.data;
}

export async function fetchSectorStocks(sectorName: string): Promise<Stock[]> {
  const res = await dedupedGet<Stock[]>(`/sectors/${encodeURIComponent(sectorName)}/stocks`);
  return res.data;
}

export async function fetchAnalysis(ticker: string): Promise<AnalysisResult> {
  const res = await dedupedGet<AnalysisResult>(`/analysis/${encodeURIComponent(ticker)}`);
  return res.data;
}

export async function fetchChartData(
  ticker: string,
  period: string = "6mo"
): Promise<ChartDataPoint[]> {
  const res = await dedupedGet<ChartApiResponse>(
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
  const res = await dedupedGet<NewsArticle[]>(`/news/${encodeURIComponent(sectorName)}`);
  return res.data;
}

export async function fetchCommodities(): Promise<CommodityPrice[]> {
  const res = await dedupedGet<CommodityPrice[]>("/commodities");
  return res.data;
}

export async function searchNews(keyword: string): Promise<NewsArticle[]> {
  const res = await dedupedGet<NewsArticle[]>(`/news/search/${encodeURIComponent(keyword)}`);
  return res.data;
}

export async function fetchEarnings(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/earnings`);
  return res.data;
}

export async function fetchPatternAnalysis(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/pattern`);
  return res.data;
}

export async function fetchCommodityHistory(
  symbol: string,
  period: string = "6mo"
): Promise<{ date: string; close: number }[]> {
  const res = await dedupedGet<{ symbol: string; data: { date: string; close: number }[] }>(
    `/commodities/history/${encodeURIComponent(symbol)}`,
    { params: { period } }
  );
  return res.data.data;
}

export async function fetchPrediction(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/prediction`);
  return res.data;
}

export async function fetchMoveReasons(ticker: string, period: string = "3mo"): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/move-reasons`, {
    params: { period },
  });
  return res.data;
}

export async function fetchChecklistLive(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/checklist-live`, {
    timeout: 90000, // 90s — checklist is the slowest endpoint
  });
  return res.data;
}

export async function fetchSectorPulse(sectorId: string): Promise<any> {
  const res = await dedupedGet(`/analysis/sector/${encodeURIComponent(sectorId)}/pulse`);
  return res.data;
}

export async function searchStocks(query: string): Promise<any> {
  const res = await api.get(`/analysis/stock-search/${encodeURIComponent(query)}`, {
    params: { _t: Date.now() },  // cache-bust to avoid stale browser cache
  });
  return res.data;
}

export async function fetchTopRanked(): Promise<any> {
  try {
    const res = await dedupedGet("/sectors/top-ranked");
    const payload = res.data as any;
    if (payload?.rankings?.length) {
      console.log(`[TOP-RANKED] API returned ${payload.rankings.length} stocks (analyzed: ${payload.total_analyzed})`);
      return payload;
    }
    console.warn("[TOP-RANKED] API returned empty rankings, trying cache");
  } catch (e) {
    console.warn("[TOP-RANKED] API failed, trying cache:", e);
  }

  const cached = readResponseCache<any>(buildRequestKey("/sectors/top-ranked"));
  if (cached?.rankings?.length) {
    console.log("[TOP-RANKED] Using cached data");
    return cached;
  }

  console.log("[TOP-RANKED] Using static fallback");
  return buildStaticTopRankedFallback();
}

export async function fetchTradingTargets(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/trading-targets`);
  return res.data;
}

export async function fetchMacroEvents(): Promise<any> {
  const res = await dedupedGet("/analysis/macro-events");
  return res.data;
}

export async function fetchResearch(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/research`);
  return res.data;
}

export async function fetchNewsAnalysis(ticker: string): Promise<any> {
  const res = await dedupedGet(`/analysis/${encodeURIComponent(ticker)}/news-analysis`);
  return res.data;
}

export async function fetchRefreshStatus(): Promise<any> {
  const res = await api.get("/refresh-status");
  return res.data;
}

export async function triggerRefreshNow(): Promise<any> {
  const res = await api.post("/refresh-now");
  return res.data;
}
