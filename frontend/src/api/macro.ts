// Macro 4페이지 API 클라이언트
import axios from "axios";
import type {
  CommoditiesResponse,
  IndicatorsResponse,
  OutlookResponse,
  ValueChainResponse,
  WikiPageResponse,
  MacroPageName,
  RegimeResponse,
} from "@/types/macro";

const api = axios.create({
  baseURL: "/api/macro",
  timeout: 30000,
});

export async function fetchCommodities(): Promise<CommoditiesResponse> {
  const { data } = await api.get<CommoditiesResponse>("/commodities");
  return data;
}

export async function fetchIndicators(sectorId?: string): Promise<IndicatorsResponse> {
  const { data } = await api.get<IndicatorsResponse>("/indicators", {
    params: sectorId ? { sector_id: sectorId } : undefined,
  });
  return data;
}

export async function fetchOutlook(): Promise<OutlookResponse> {
  const { data } = await api.get<OutlookResponse>("/outlook");
  return data;
}

export async function fetchValueChain(sectorId?: string): Promise<ValueChainResponse> {
  const { data } = await api.get<ValueChainResponse>("/value-chain", {
    params: sectorId ? { sector_id: sectorId } : undefined,
  });
  return data;
}

export async function fetchWikiPage(name: MacroPageName): Promise<WikiPageResponse> {
  const { data } = await api.get<WikiPageResponse>(`/page/${name}`);
  return data;
}

export async function fetchRegime(): Promise<RegimeResponse> {
  const { data } = await api.get<RegimeResponse>("/regime");
  return data;
}
