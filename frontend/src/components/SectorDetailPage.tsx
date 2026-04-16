import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import {
  ComposedChart,
  Area,

  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Bar,
  ReferenceDot,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import { ArrowLeft, AlertTriangle, Activity, Newspaper, Zap, ChevronRight, TrendingUp, TrendingDown, CheckCircle2, XCircle, MinusCircle, Shield, Globe } from "lucide-react";
import { useLanguage, t as t_static, type TranslationKey } from "@/i18n";
import { SECTORS } from "@/data/sectors";
import type { SectorDef, StockPick } from "@/data/sectors";
import { fetchChartData, fetchAnalysis, fetchEarnings, fetchPatternAnalysis, fetchCommodityHistory, searchNews, fetchPrediction, fetchMoveReasons, fetchChecklistLive, fetchSectorPulse, fetchMacroEvents, fetchTradingTargets, fetchNewsAnalysis } from "@/api/client";
import type { ChartDataPoint, AnalysisResult, NewsArticle } from "@/types";

const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const h = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, []);
  return isMobile;
};

/* periods moved inside StockAnalysisCard for i18n */

/* ── Internal analysis engine (user never sees raw indicators) ── */

/** Convert a 0-100 score to label + color. Single source of truth for all verdicts. */
type TFn = (key: TranslationKey) => string;
function scoreToVerdict(score: number, t?: TFn): { label: string; color: string; action: string } {
  const tr: TFn = t ?? ((k) => t_static(k, "ko"));
  if (score >= 80) return { label: tr("verdictStrongBuy"), color: "#16a34a", action: tr("actionStrongBuy") };
  if (score >= 65) return { label: tr("verdictBuy"), color: "#22c55e", action: tr("actionBuy") };
  if (score >= 45) return { label: tr("verdictHold"), color: "#eab308", action: tr("actionHold") };
  if (score >= 30) return { label: tr("verdictReduce"), color: "#ef4444", action: tr("actionReduce") };
  return { label: tr("verdictSell"), color: "#dc2626", action: tr("actionSell") };
}

function analyzeChart(analysis: AnalysisResult | null, chartData: ChartDataPoint[], t?: TFn): {
  score100: number;
  label: string;
  color: string;
  reason: string;
} {
  const tr: TFn = t ?? ((k) => t_static(k, "ko"));
  if (!analysis) return { score100: 50, label: tr("analyzing"), color: "#64748b", reason: tr("dataLoadingMsg") };
  const ind = analysis.indicators;
  const price = chartData.length > 0 ? chartData[chartData.length - 1].close : null;
  let score = 0;
  let checks = 0;

  // RSI
  if (ind.rsi != null) {
    checks++;
    if (ind.rsi < 30) score += 2;
    else if (ind.rsi < 40) score += 1;
    else if (ind.rsi > 70) score -= 2;
    else if (ind.rsi > 60) score -= 1;
  }
  // MACD
  if (ind.macd != null && ind.macd_signal != null) {
    checks++;
    score += ind.macd > ind.macd_signal ? 1 : -1;
  }
  // Bollinger
  if (ind.bollinger_upper != null && ind.bollinger_lower != null && price) {
    checks++;
    const bbRange = ind.bollinger_upper - ind.bollinger_lower;
    if (bbRange > 0) {
      const pos = (price - ind.bollinger_lower) / bbRange;
      if (pos < 0.2) score += 2;
      else if (pos < 0.4) score += 1;
      else if (pos > 0.8) score -= 2;
      else if (pos > 0.6) score -= 1;
    }
  }
  // SMA trend
  if (ind.sma_20 != null && ind.sma_50 != null) { checks++; score += ind.sma_20 > ind.sma_50 ? 1 : -1; }
  if (ind.sma_200 != null && price) { checks++; score += price > ind.sma_200 ? 1 : -1; }
  // SMA20 distance
  if (ind.sma_20 != null && price) {
    checks++;
    const pct = ((price - ind.sma_20) / ind.sma_20) * 100;
    if (pct < -5) score += 1;
    else if (pct > 5) score -= 1;
  }
  // MACD histogram trend
  const histData = chartData.filter(d => d.macd_histogram != null).slice(-3);
  if (histData.length === 3) {
    checks++;
    const inc = histData[2].macd_histogram! > histData[1].macd_histogram! && histData[1].macd_histogram! > histData[0].macd_histogram!;
    const dec = histData[2].macd_histogram! < histData[1].macd_histogram! && histData[1].macd_histogram! < histData[0].macd_histogram!;
    if (inc) score += 1;
    if (dec) score -= 1;
  }
  // Volume trend
  if (chartData.length >= 10) {
    checks++;
    const recentVol = chartData.slice(-5).reduce((a, d) => a + d.volume, 0) / 5;
    const prevVol = chartData.slice(-10, -5).reduce((a, d) => a + d.volume, 0) / 5;
    if (prevVol > 0) {
      const priceUp = chartData[chartData.length - 1].close > chartData[chartData.length - 5].close;
      const volUp = recentVol > prevVol * 1.2;
      if (priceUp && volUp) score += 1;
      else if (!priceUp && volUp) score -= 1;
    }
  }

  // Normalize to 0-100 scale: norm ranges from about -2 to +2, map to 0-100
  const norm = checks > 0 ? score / checks : 0;
  const score100 = Math.round(Math.max(0, Math.min(100, (norm + 1) * 50)));

  const reasons: string[] = [];
  if (ind.rsi != null) reasons.push(`RSI ${ind.rsi.toFixed(0)}${ind.rsi > 70 ? `(${tr("overbought")})` : ind.rsi < 30 ? `(${tr("oversold")})` : ""}`);
  if (ind.macd != null && ind.macd_signal != null) reasons.push(`MACD ${ind.macd > ind.macd_signal ? tr("goldenCross") : tr("deadCross")}`);
  if (ind.sma_20 != null && ind.sma_50 != null) reasons.push(`SMA ${ind.sma_20 > ind.sma_50 ? tr("uptrendSMA") : tr("downtrendSMA")}`);

  const v = scoreToVerdict(score100, t);
  return { score100, label: v.label, color: v.color, reason: reasons.join(" · ") };
}

function analyzeFundamentals(earnings: any, patternData: any, t?: TFn): {
  score100: number;
  label: string;
  color: string;
  reason: string;
} {
  const tr: TFn = t ?? ((k) => t_static(k, "ko"));
  // Pure earnings/fundamentals scoring — matches backend score_stock() fund_score100.
  // Checklist score is handled separately in the overall weighted formula.
  if (!earnings || earnings.error) return { score100: 50, label: tr("noData"), color: "#64748b", reason: "" };

  let score = 0;
  let checks = 0;
  const reasons: string[] = [];

  if (earnings.revenue_growth != null) {
    checks++;
    if (earnings.revenue_growth > 0.2) { score += 2; reasons.push(`${tr("revenueShort")} +${(earnings.revenue_growth * 100).toFixed(0)}%`); }
    else if (earnings.revenue_growth > 0) { score += 1; reasons.push(`${tr("revenueShort")} +${(earnings.revenue_growth * 100).toFixed(0)}%`); }
    else { score -= 1; reasons.push(`${tr("revenueShort")} ${(earnings.revenue_growth * 100).toFixed(0)}%`); }
  }
  if (earnings.earnings_growth != null) {
    checks++;
    if (earnings.earnings_growth > 0.2) score += 2;
    else if (earnings.earnings_growth > 0) score += 1;
    else score -= 1;
  }
  if (earnings.pe_ratio != null && earnings.forward_pe != null) {
    checks++;
    if (earnings.forward_pe < earnings.pe_ratio * 0.8) { score += 1; reasons.push(`Forward PE ${earnings.forward_pe.toFixed(0)} < Trailing ${earnings.pe_ratio.toFixed(0)}`); }
    else if (earnings.forward_pe > earnings.pe_ratio) score -= 1;
  }
  if (earnings.profit_margin != null) {
    checks++;
    if (earnings.profit_margin > 0.2) score += 1;
    else if (earnings.profit_margin < 0) { score -= 2; reasons.push(tr("netLossState")); }
  }
  if (earnings.roe != null) {
    checks++;
    if (earnings.roe > 0.2) score += 1;
    else if (earnings.roe < 0) score -= 1;
  }
  if (patternData?.summary) {
    checks++;
    if (patternData.summary.up_probability > 60) { score += 1; reasons.push(`${tr("patternUpProb")} ${patternData.summary.up_probability}%`); }
    else if (patternData.summary.up_probability < 40) { score -= 1; reasons.push(`${tr("patternUpProb")} ${patternData.summary.up_probability}%`); }
  }

  const norm = checks > 0 ? score / checks : 0;
  const score100 = Math.round(Math.max(0, Math.min(100, (norm + 1) * 50)));

  const v = scoreToVerdict(score100, t);
  return { score100, label: v.label, color: v.color, reason: reasons.join(" · ") };
}

/* ── Stock checklist & momentum data (bilingual) ── */

type BiStr = { ko: string; en: string };
type MomentumItemBi = { title: BiStr; detail: BiStr; condition: BiStr };
type MomentumItem = { title: string; detail: string; condition: string };
const STOCK_META_BI: Record<string, { checklist: BiStr[]; momentum: MomentumItemBi[] }> = {
  "NVDA": {
    checklist: [
      { ko: "데이터센터 매출 성장률 (QoQ)", en: "Data center revenue growth (QoQ)" },
      { ko: "HBM/GPU ASP 추이", en: "HBM/GPU ASP trend" },
      { ko: "AI 캡엑스 지출 (MSFT/GOOG/META)", en: "AI capex (MSFT/GOOG/META)" },
      { ko: "중국 수출 규제 변동", en: "China export regulation changes" },
      { ko: "경쟁사 AMD MI300 점유율", en: "Competitor AMD MI300 share" },
    ],
    momentum: [
      { title: { ko: "Blackwell Ultra 출시 (2026 H2)", en: "Blackwell Ultra launch (2026 H2)" }, detail: { ko: "차세대 GPU 출시로 데이터센터 교체 수요가 본격화됩니다", en: "Next-gen GPU launch drives datacenter upgrade demand" }, condition: { ko: "출시 일정이 지켜지고, 주요 고객(MS/Google/Meta)의 사전 주문이 유지되어야 합니다", en: "Launch schedule must hold; key customer pre-orders (MS/Google/Meta) must be maintained" } },
      { title: { ko: "데이터센터 캡엑스 $200B+ 지속", en: "Datacenter capex $200B+ continues" }, detail: { ko: "빅테크 AI 인프라 투자가 계속 확대되고 있어 GPU 수요를 뒷받침합니다", en: "Big tech AI infra investment expansion supports GPU demand" }, condition: { ko: "빅테크 실적 발표에서 AI 캡엑스 가이던스가 유지/상향되어야 합니다", en: "Big tech must maintain/raise AI capex guidance" } },
      { title: { ko: "자율주행/로봇 GPU 수요 신규", en: "New autonomous/robotics GPU demand" }, detail: { ko: "자동차·로봇 분야에서 새로운 GPU 수요처가 열리고 있습니다", en: "New GPU demand from automotive and robotics sectors" }, condition: { ko: "Tesla FSD, Waymo 등 자율주행 실적이 가시화되어야 합니다", en: "Tesla FSD, Waymo must show tangible results" } },
      { title: { ko: "중국 규제 완화 가능성", en: "Potential China regulation easing" }, detail: { ko: "미중 관계 개선 시 수출 규제 완화로 중국 매출 회복 가능", en: "US-China improvement could ease export controls, recovering China revenue" }, condition: { ko: "미국 정부의 수출 규제 정책 변화 여부를 모니터링해야 합니다", en: "Monitor US government export regulation policy changes" } },
    ],
  },
  "TSM": {
    checklist: [
      { ko: "3nm/2nm 가동률", en: "3nm/2nm utilization" },
      { ko: "웨이퍼 ASP 변동", en: "Wafer ASP changes" },
      { ko: "월별 매출 공시 (MoM)", en: "Monthly revenue (MoM)" },
      { ko: "지정학 리스크 (대만 해협)", en: "Geopolitical risk (Taiwan Strait)" },
      { ko: "CAPEX 집행률", en: "CAPEX execution rate" },
    ],
    momentum: [
      { title: { ko: "2nm 양산 시작 (2026)", en: "2nm mass production (2026)" }, detail: { ko: "차세대 2nm 공정 양산이 시작되면 ASP 상승과 점유율 확대가 기대됩니다", en: "2nm production expected to drive ASP increase and market share gain" }, condition: { ko: "2nm 수율이 목표치에 도달하고, Apple/NVDA 등 핵심 고객 주문이 확정되어야 합니다", en: "2nm yield must hit targets; Apple/NVDA orders must be confirmed" } },
      { title: { ko: "미국 애리조나 팹 가동", en: "US Arizona fab ramp-up" }, detail: { ko: "미국 현지 생산으로 지정학 리스크 완화 + 미국 정부 보조금 수혜", en: "US local production mitigates geopolitical risk + government subsidies" }, condition: { ko: "팹 가동률이 경제성 있는 수준까지 올라야 하며, 인력 확보가 순조로워야 합니다", en: "Fab utilization must reach economic viability; talent acquisition must be smooth" } },
    ],
  },
  "AVGO": {
    checklist: [
      { ko: "커스텀 AI칩 수주 현황", en: "Custom AI chip orders" },
      { ko: "VMware 통합 시너지", en: "VMware integration synergies" },
      { ko: "네트워킹 매출 비중", en: "Networking revenue mix" },
      { ko: "배당 성장률", en: "Dividend growth rate" },
      { ko: "Google TPU 계약", en: "Google TPU contract" },
    ],
    momentum: [
      { title: { ko: "Google TPU v6 대량 수주", en: "Google TPU v6 large orders" }, detail: { ko: "Google 커스텀 AI칩 수주가 매출 성장의 핵심 동력입니다", en: "Google custom AI chip orders are the key revenue growth driver" }, condition: { ko: "Google의 AI 인프라 투자가 유지되고, TPU 점유율이 NVDA GPU 대비 확대되어야 합니다", en: "Google AI investment must continue; TPU share must expand vs NVDA GPU" } },
      { title: { ko: "AI 네트워킹 스위치 수요 급증", en: "AI networking switch demand surge" }, detail: { ko: "AI 데이터센터 확장에 필수적인 네트워킹 장비 수요가 폭발적으로 증가 중", en: "Explosive networking equipment demand for AI datacenter expansion" }, condition: { ko: "데이터센터 신규 건설 속도가 유지되어야 합니다", en: "New datacenter construction pace must be maintained" } },
    ],
  },
  "000660.KS": {
    checklist: [
      { ko: "DRAM 현물/계약가격 추이", en: "DRAM spot/contract price trend" },
      { ko: "HBM 출하량/ASP", en: "HBM shipment/ASP" },
      { ko: "재고 수준 (bit growth)", en: "Inventory (bit growth)" },
      { ko: "NVDA HBM 공급 비중", en: "NVDA HBM supply share" },
      { ko: "영업이익률 추이", en: "Operating margin trend" },
    ],
    momentum: [
      { title: { ko: "HBM4 양산 (2026)", en: "HBM4 mass production (2026)" }, detail: { ko: "차세대 HBM4 양산으로 NVDA 독점 공급 지위를 공고히 합니다", en: "Next-gen HBM4 solidifies exclusive NVDA supply position" }, condition: { ko: "HBM4 수율이 양산 가능 수준이고, NVDA의 차세대 GPU에 채택이 확정되어야 합니다", en: "HBM4 yield must be production-ready; adoption in NVDA next-gen GPU confirmed" } },
      { title: { ko: "DRAM 업사이클 진입", en: "DRAM upcycle entry" }, detail: { ko: "서버 DRAM 가격 상승 사이클이 시작되어 실적 개선이 가속화됩니다", en: "Server DRAM price upcycle accelerates earnings improvement" }, condition: { ko: "DRAM 현물가격이 계약가격 대비 프리미엄을 유지해야 합니다. 재고가 쌓이면 사이클이 꺾입니다", en: "DRAM spot must maintain premium over contract. Inventory buildup ends the cycle" } },
    ],
  },
  "005930.KS": {
    checklist: [
      { ko: "DRAM/NAND 가격 추이", en: "DRAM/NAND price trend" },
      { ko: "파운드리 수율 개선", en: "Foundry yield improvement" },
      { ko: "HBM 수율 이슈", en: "HBM yield issues" },
      { ko: "갤럭시 판매량", en: "Galaxy sales volume" },
      { ko: "자사주 매입", en: "Share buyback" },
    ],
    momentum: [
      { title: { ko: "HBM3E 수율 개선 기대", en: "HBM3E yield improvement expected" }, detail: { ko: "HBM 수율 문제가 해결되면 NVDA 공급 확대로 실적이 크게 개선됩니다", en: "Resolving HBM yield issues expands NVDA supply, significantly boosting earnings" }, condition: { ko: "HBM3E 수율이 경쟁사(SK하이닉스) 수준까지 올라야 하며, NVDA 인증을 통과해야 합니다", en: "HBM3E yield must reach SK Hynix levels; NVDA certification required" } },
      { title: { ko: "밸류업 프로그램 (주주환원)", en: "Value-up program (shareholder returns)" }, detail: { ko: "자사주 매입·소각으로 주당가치 상승이 기대됩니다", en: "Share buyback & cancellation expected to increase per-share value" }, condition: { ko: "자사주 매입 규모가 기대 이상이어야 하며, 지속적인 주주환원 정책이 확인되어야 합니다", en: "Buyback size must exceed expectations with continued shareholder return policy" } },
    ],
  },
  "TSLA": {
    checklist: [
      { ko: "차량 인도량 (QoQ)", en: "Vehicle deliveries (QoQ)" },
      { ko: "Optimus 로봇 진행상황", en: "Optimus robot progress" },
      { ko: "FSD 라이센싱 수익", en: "FSD licensing revenue" },
      { ko: "마진율 추이", en: "Margin trend" },
      { ko: "에너지 사업 매출", en: "Energy business revenue" },
    ],
    momentum: [
      { title: { ko: "Optimus 2027 공장 투입", en: "Optimus factory deployment 2027" }, detail: { ko: "휴머노이드 로봇이 공장에 투입되면 로봇 사업의 매출 가시성이 생깁니다", en: "Humanoid robot factory deployment creates robotics revenue visibility" }, condition: { ko: "2027년 일정이 지켜져야 하며, 로봇 성능이 실제 공장 작업에 적합해야 합니다", en: "2027 timeline must hold; robot must suit actual factory tasks" } },
      { title: { ko: "로보택시 출시", en: "Robotaxi launch" }, detail: { ko: "자율주행 택시 서비스가 시작되면 소프트웨어 반복매출이 폭발합니다", en: "Autonomous taxi launch drives explosive recurring software revenue" }, condition: { ko: "규제 승인과 안전 기록이 확보되어야 하며, 사고 리스크가 통제되어야 합니다", en: "Regulatory approval + safety record required; accident risk must be controlled" } },
    ],
  },
  "ISRG": {
    checklist: [
      { ko: "다빈치 시술 건수 (QoQ)", en: "Da Vinci procedures (QoQ)" },
      { ko: "시스템 설치 대수", en: "System installations" },
      { ko: "반복매출 비중", en: "Recurring revenue share" },
      { ko: "경쟁사 진입 여부", en: "Competitor entry" },
      { ko: "중국 시장 확대", en: "China market expansion" },
    ],
    momentum: [
      { title: { ko: "다빈치 5 신규 설치 가속", en: "Da Vinci 5 installation acceleration" }, detail: { ko: "최신 다빈치 5 시스템 설치가 빨라지면 반복매출(소모품)이 크게 증가합니다", en: "Faster Da Vinci 5 installations significantly increase recurring revenue" }, condition: { ko: "병원들의 설비 투자 예산이 유지되고, 경쟁 로봇(Medtronic Hugo)이 점유율을 빼앗지 않아야 합니다", en: "Hospital capex must hold; competitors (Medtronic Hugo) must not take share" } },
    ],
  },
  "CEG": {
    checklist: [
      { ko: "원전 가동률", en: "Nuclear utilization" },
      { ko: "전력 계약 가격(PPA)", en: "Power contract price (PPA)" },
      { ko: "Microsoft/Google 전력 계약", en: "Microsoft/Google power contracts" },
      { ko: "규제 환경 변화", en: "Regulatory changes" },
      { ko: "전력 수요 전망", en: "Power demand outlook" },
    ],
    momentum: [
      { title: { ko: "AI 데이터센터 전력 수요 폭증", en: "AI datacenter power demand surge" }, detail: { ko: "AI 데이터센터 확장으로 안정적인 원전 전력 수요가 급증하고 있습니다", en: "AI datacenter expansion drives surging nuclear power demand" }, condition: { ko: "빅테크의 데이터센터 건설 계획이 유지되고, 전력 장기계약(PPA) 가격이 상승 추세여야 합니다", en: "Big tech datacenter plans must continue; long-term PPA prices must trend up" } },
    ],
  },
  "CCJ": {
    checklist: [
      { ko: "우라늄 현물가격", en: "Uranium spot price" },
      { ko: "장기 계약가격", en: "Long-term contract price" },
      { ko: "공급 부족 규모", en: "Supply deficit" },
      { ko: "카자흐스탄 생산량", en: "Kazakhstan production" },
      { ko: "러시아 수출 제재", en: "Russia export sanctions" },
    ],
    momentum: [
      { title: { ko: "우라늄 $100/lb 돌파", en: "Uranium breaking $100/lb" }, detail: { ko: "우라늄 가격 상승은 CCJ 매출과 이익에 직결됩니다", en: "Rising uranium prices directly impact CCJ revenue and profits" }, condition: { ko: "러시아 우라늄 수출 제재가 유지되고, 신규 원전 건설 수주가 계속되어야 합니다", en: "Russia sanctions must persist; new nuclear plant orders must continue" } },
    ],
  },
  "CRWD": {
    checklist: [
      { ko: "ARR 성장률", en: "ARR growth rate" },
      { ko: "고객당 모듈 수", en: "Modules per customer" },
      { ko: "순유지율(NRR)", en: "Net retention (NRR)" },
      { ko: "경쟁사 대비 점유율", en: "Share vs competitors" },
      { ko: "보안사고 리스크", en: "Security incident risk" },
    ],
    momentum: [
      { title: { ko: "AI 기반 위협탐지 확대", en: "AI threat detection expansion" }, detail: { ko: "AI 보안 솔루션 수요가 기존 방화벽을 대체하며 빠르게 성장합니다", en: "AI security demand rapidly replacing traditional firewalls" }, condition: { ko: "ARR 성장률 30%+ 유지와 신규 모듈 채택률이 증가해야 합니다. 블루스크린 같은 보안사고 재발 시 급락 위험", en: "Must maintain 30%+ ARR growth. Blue screen-type incidents could trigger sharp decline" } },
    ],
  },
  "CRSP": {
    checklist: [
      { ko: "임상시험 진행 단계", en: "Clinical trial stage" },
      { ko: "FDA 승인 일정", en: "FDA approval timeline" },
      { ko: "적응증 확대 파이프라인", en: "Indication pipeline" },
      { ko: "현금 보유량(런웨이)", en: "Cash reserves (runway)" },
      { ko: "경쟁 유전자치료 동향", en: "Gene therapy competition" },
    ],
    momentum: [
      { title: { ko: "Casgevy FDA 승인 완료", en: "Casgevy FDA approved" }, detail: { ko: "겸상적혈구병 유전자치료제가 FDA 승인을 받아 상업화 매출이 시작됩니다", en: "Sickle cell gene therapy FDA-approved; commercial revenue begins" }, condition: { ko: "보험사 커버리지 확대로 환자 접근성이 높아져야 하고, 경쟁 치료제(블루버드바이오) 대비 효능 우위가 유지되어야 합니다", en: "Insurance coverage must expand; must maintain efficacy advantage over bluebird bio" } },
      { title: { ko: "적응증 확대 (암, 심혈관)", en: "Indication expansion (oncology, CV)" }, detail: { ko: "유전자편집 기술을 암·심혈관 질환으로 확장하면 시장이 수십배 커집니다", en: "Expanding gene editing to oncology/cardiovascular multiplies the market" }, condition: { ko: "임상 2/3상 결과가 긍정적이어야 하며, FDA의 유전자치료 안전성 기준이 강화되지 않아야 합니다", en: "Phase 2/3 results must be positive; FDA gene therapy standards must not tighten" } },
      { title: { ko: "유전자편집 기술 특허 독점", en: "Gene editing patent monopoly" }, detail: { ko: "CRISPR 원천기술 특허로 경쟁사 진입을 막고 라이센스 수익이 가능합니다", en: "CRISPR core patents block competitors and enable licensing revenue" }, condition: { ko: "특허 소송에서 승리해야 하며, 차세대 편집 기술(프라임 에디팅)이 CRISPR를 대체하지 않아야 합니다", en: "Must win patent litigation; prime editing must not replace CRISPR" } },
    ],
  },
  "LLY": {
    checklist: [
      { ko: "비만약(GLP-1) 처방 데이터", en: "Obesity drug (GLP-1) Rx data" },
      { ko: "분기별 매출 서프라이즈", en: "Quarterly revenue surprise" },
      { ko: "파이프라인 임상 결과", en: "Pipeline clinical results" },
      { ko: "경쟁사(NVO) 동향", en: "Competitor (NVO) trends" },
      { ko: "보험 커버리지 확대", en: "Insurance coverage expansion" },
    ],
    momentum: [
      { title: { ko: "비만약 시장 $100B 성장", en: "Obesity market growing to $100B" }, detail: { ko: "GLP-1 비만약 시장이 2030년까지 $100B 이상으로 성장할 전망입니다", en: "GLP-1 obesity market projected to exceed $100B by 2030" }, condition: { ko: "보험사 커버리지 확대 + 공급 부족 해소가 필요합니다. 노보노디스크와의 경쟁에서 점유율을 지켜야 합니다", en: "Insurance expansion + supply resolution needed. Must defend share vs Novo Nordisk" } },
      { title: { ko: "알츠하이머 신약 도나네맙", en: "Alzheimer's drug donanemab" }, detail: { ko: "알츠하이머 치료제 시장은 연간 $10B+ 규모로, 승인 시 큰 매출원이 됩니다", en: "Alzheimer's market is $10B+/yr; approval creates major revenue stream" }, condition: { ko: "임상 데이터가 경쟁약(레카네맙) 대비 우월해야 하며, 보험 급여가 확대되어야 합니다", en: "Clinical data must beat lecanemab; insurance reimbursement must expand" } },
    ],
  },
  "IONQ": {
    checklist: [
      { ko: "큐비트 수 로드맵 진척", en: "Qubit roadmap progress" },
      { ko: "매출 증가율", en: "Revenue growth rate" },
      { ko: "현금 소진율", en: "Cash burn rate" },
      { ko: "정부/기업 계약", en: "Government/enterprise contracts" },
      { ko: "기술적 마일스톤", en: "Technical milestones" },
    ],
    momentum: [
      { title: { ko: "양자 우위 달성 임박", en: "Quantum advantage imminent" }, detail: { ko: "양자 컴퓨터가 기존 슈퍼컴퓨터를 넘는 순간 시장이 폭발합니다", en: "Market explodes when quantum surpasses classical supercomputers" }, condition: { ko: "큐비트 수 로드맵이 지켜지고, 오류율이 실용 수준으로 낮아져야 합니다. 현금이 바닥나기 전에 성과를 내야 합니다", en: "Qubit roadmap must hold; error rates must drop. Must deliver before cash runs out" } },
    ],
  },
  "RKLB": {
    checklist: [
      { ko: "발사 횟수/성공률", en: "Launch count/success rate" },
      { ko: "Neutron 로켓 개발 진척", en: "Neutron development progress" },
      { ko: "우주시스템 매출 비중", en: "Space systems revenue share" },
      { ko: "수주잔고", en: "Order backlog" },
      { ko: "경쟁사(SpaceX) 동향", en: "Competitor (SpaceX) trends" },
    ],
    momentum: [
      { title: { ko: "Neutron 첫 발사 예정", en: "Neutron first launch" }, detail: { ko: "중형 로켓 Neutron 성공 시 발사 시장 점유율이 크게 확대됩니다", en: "Successful Neutron significantly expands launch market share" }, condition: { ko: "발사 일정이 지켜지고, 첫 발사가 성공해야 합니다. 실패 시 주가 30%+ 급락 위험", en: "Schedule must hold and first launch must succeed. Failure risks 30%+ drop" } },
    ],
  },
  "BE": {
    checklist: [
      { ko: "SOFC 주문 잔고", en: "SOFC order backlog" },
      { ko: "매출총이익률 추이", en: "Gross margin trend" },
      { ko: "AI 데이터센터 계약", en: "AI datacenter contracts" },
      { ko: "수소 전환 로드맵", en: "Hydrogen transition roadmap" },
      { ko: "정부 보조금 현황", en: "Government subsidies" },
    ],
    momentum: [
      { title: { ko: "AI 데이터센터 분산전원 계약", en: "AI datacenter distributed power" }, detail: { ko: "데이터센터가 그리드 전력 부족으로 분산전원(연료전지)을 도입하고 있습니다", en: "Datacenters adopting fuel cells due to grid power shortage" }, condition: { ko: "대형 데이터센터 계약이 추가되어야 하며, 전력 단가가 그리드 대비 경쟁력을 가져야 합니다", en: "Must add large datacenter contracts; cost must be competitive vs grid" } },
      { title: { ko: "흑자 전환 임박", en: "Profitability imminent" }, detail: { ko: "매출 확대와 원가 개선으로 흑자 전환이 예상됩니다", en: "Revenue growth + cost improvement expected to drive profitability" }, condition: { ko: "매출총이익률이 25%+ 유지되고, 운영비 증가를 통제해야 합니다", en: "Gross margin must stay above 25%; opex growth must be controlled" } },
    ],
  },
};

/** Resolve bilingual STOCK_META to current language */
function getStockMeta(ticker: string, lang: "ko" | "en" = "ko"): { checklist: string[]; momentum: MomentumItem[] } {
  const raw = STOCK_META_BI[ticker] || STOCK_META_BI[ticker.replace(".KS", "").replace(".KQ", "")];
  const pick = (b: BiStr) => b[lang] || b.ko;
  if (raw) return {
    checklist: raw.checklist.map(pick),
    momentum: raw.momentum.map(m => ({ title: pick(m.title), detail: pick(m.detail), condition: pick(m.condition) })),
  };
  return {
    checklist: [t_static("defaultChecklist1", lang), t_static("defaultChecklist2", lang), t_static("defaultChecklist3", lang), t_static("defaultChecklist4", lang)],
    momentum: [
      { title: t_static("defaultMomentum1Title", lang), detail: t_static("defaultMomentum1Detail", lang), condition: t_static("defaultMomentum1Cond", lang) },
      { title: t_static("defaultMomentum2Title", lang), detail: t_static("defaultMomentum2Detail", lang), condition: t_static("defaultMomentum2Cond", lang) },
    ],
  };
}

/* ── Elapsed timer for loading states ── */
function ElapsedTimer({ active }: { active: boolean }) {
  const { t } = useLanguage();
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!active) { setElapsed(0); return; }
    const start = Date.now();
    const id = window.setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => window.clearInterval(id);
  }, [active]);
  if (!active || elapsed < 3) return null;
  return <span className="text-[10px] text-[var(--color-text-muted)] tabular-nums">{elapsed}{t("elapsedSec")}</span>;
}

/* ── StockAnalysisCard ── */

function StockAnalysisCard({ pick, sectorColor }: { pick: StockPick; sectorColor: string }) {
  const { t, lang } = useLanguage();
  const mob = useIsMobile();
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [earnings, setEarnings] = useState<any>(null);
  const [patternData, setPatternData] = useState<any>(null);
  const [_prediction, setPrediction] = useState<any>(null);
  const [moveReasons, setMoveReasons] = useState<any>(null);
  const [checklistLive, setChecklistLive] = useState<any>(null);
  const [newsAnalysis, setNewsAnalysis] = useState<any>(null);
  const [macroEvents, setMacroEvents] = useState<any>(null);
  const [tradingTargets, setTradingTargets] = useState<any>(null);
  const [showTargetReasons, setShowTargetReasons] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>("3mo");
  const [loading, setLoading] = useState(true);
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadStage, setLoadStage] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [partialDataWarning, setPartialDataWarning] = useState(false);

  const periods = useMemo(() => [
    { label: t("period1m"), value: "1mo" },
    { label: t("period3m"), value: "3mo" },
    { label: t("period6m"), value: "6mo" },
    { label: t("period1y"), value: "1y" },
  ], [t]);

  // Track initial period so we can detect user-initiated period changes
  const initialPeriodRef = useRef(period);

  // Ticker-dependent data — re-fetches when stock changes or retry (NOT on period change)
  useEffect(() => {
    let cancelled = false;
    initialPeriodRef.current = period; // sync period ref on ticker change

    setLoading(true);
    setLoadProgress(0);
    setLoadStage(t("preparingData"));
    setLoadError(false);
    setAnalysis(null);
    setEarnings(null);
    setPatternData(null);
    setPrediction(null);
    setChecklistLive(null);
    setNewsAnalysis(null);
    setTradingTargets(null);
    setShowTargetReasons(null);
    setMoveReasons(null);
    setMacroEvents(null);

    const ticker = pick.ticker;
    console.log(`[LOAD] Starting data load for ${ticker} (retry=${retryCount})`);

    // ── Helper: safe fetch that NEVER throws ──
    async function safeFetch<T>(label: string, fn: () => Promise<T>): Promise<T | null> {
      try {
        const result = await fn();
        console.log(`[LOAD] ${label} OK`, typeof result === "object" && result ? "✓" : result);
        return result;
      } catch (err) {
        console.error(`[LOAD] ${label} FAILED`, err);
        return null;
      }
    }

    // ── Phase 1: Essential data (chart + analysis + earnings) ──
    async function loadEssentials() {
      setChartLoading(true);
      setLoadStage(t("loadingChartAnalysis"));
      setLoadProgress(10);

      const [chartResult, analysisResult, earningsResult] = await Promise.all([
        safeFetch("chart-data", () => fetchChartData(ticker, period)),
        safeFetch("analysis", () => fetchAnalysis(ticker)),
        safeFetch("earnings", () => fetchEarnings(ticker)),
      ]);

      if (cancelled) return false;

      // Set whatever data we got
      if (chartResult) setChartData(chartResult);
      if (analysisResult) setAnalysis(analysisResult);
      if (earningsResult) setEarnings(earningsResult);

      setChartLoading(false);
      setLoadProgress(60);

      const chartOk = Array.isArray(chartResult) && chartResult.length > 0;
      const hasAnalysis = analysisResult != null && typeof analysisResult === "object";
      const hasEarnings = earningsResult != null && typeof earningsResult === "object";

      console.log(`[LOAD] Essential results — chart:${chartOk} analysis:${hasAnalysis} earnings:${hasEarnings}`);

      // If chart failed, one retry
      if (!chartOk) {
        console.log("[LOAD] Chart retry...");
        await new Promise((r) => setTimeout(r, 1500));
        const retry = await safeFetch("chart-retry", () => fetchChartData(ticker, period));
        if (!cancelled && retry && Array.isArray(retry) && retry.length > 0) {
          setChartData(retry);
          return true; // chart retry succeeded
        }
      }

      return chartOk || hasAnalysis || hasEarnings;
    }

    // ── Phase 2: Background data (never blocks loading) ──
    function loadBackground() {
      const bg = (label: string, fn: () => Promise<any>, setter: (d: any) => void) =>
        safeFetch(label, fn).then((d) => { if (!cancelled && d) setter(d); });

      // Launch ALL background fetches in parallel — no sequential batching.
      Promise.allSettled([
        bg("pattern", () => fetchPatternAnalysis(ticker), setPatternData),
        bg("prediction", () => fetchPrediction(ticker), setPrediction),
        bg("targets", () => fetchTradingTargets(ticker), setTradingTargets),
        bg("move-reasons", () => fetchMoveReasons(ticker, period), setMoveReasons),
        bg("macro", () => fetchMacroEvents(), setMacroEvents),
        bg("news-analysis", () => fetchNewsAnalysis(ticker), setNewsAnalysis),
        bg("checklist", () => fetchChecklistLive(ticker), setChecklistLive),
      ]);
    }

    // ── Main execution ──
    loadEssentials()
      .then((hasData) => {
        if (cancelled) return;

        if (hasData) {
          console.log("[LOAD] ✓ Essential data loaded — showing page");
          setLoadProgress(100);
          setLoadStage(t("complete"));
          setLoading(false);
          loadBackground();
        } else if (retryCount < 3) {
          console.warn(`[LOAD] ✗ No essential data — auto-retry ${retryCount + 1}/3 in 5s`);
          setLoadError(true);
          setLoadStage(t("waitingServer"));
          setLoadProgress(0);
          setTimeout(() => { if (!cancelled) setRetryCount((c) => c + 1); }, 5000);
        } else {
          console.warn("[LOAD] ✗ Max retries reached — showing error");
          setLoadError(true);
          setLoadStage(t("cannotLoadData"));
          setLoadProgress(0);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("[LOAD] UNEXPECTED loadEssentials error", err);
        if (cancelled) return;
        setLoadError(true);
        setLoadStage(t("unexpectedError"));
        setLoadProgress(0);
        setLoading(false);
      });

    // Safety timeout: if loading hasn't finished after 20s, force-show whatever we have
    const safetyTimer = setTimeout(() => {
      if (!cancelled) {
        console.warn("[LOAD] Safety timeout — forcing loading=false");
        setLoading(false);
        setPartialDataWarning(true);
      }
    }, 20000);

    return () => {
      cancelled = true;
      clearTimeout(safetyTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pick.ticker, retryCount]);

  // Period change — only re-fetch chart data (no full reload)
  useEffect(() => {
    // Skip on initial mount (handled by the main effect above)
    if (period === initialPeriodRef.current) return;
    let cancelled = false;
    setChartLoading(true);
    fetchChartData(pick.ticker, period)
      .then((data) => {
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          setChartData(data);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setChartLoading(false); });
    return () => { cancelled = true; };
  }, [pick.ticker, period]);

  // Auto-refresh every 5 min — only refresh analysis & checklist (not chart, to avoid UI jump)
  useEffect(() => {
    const tkr = pick.ticker;
    const intervalId = window.setInterval(() => {
      fetchAnalysis(tkr).then(setAnalysis).catch(() => {});
      fetchChecklistLive(tkr).then(setChecklistLive).catch(() => {});
    }, 300_000);
    return () => window.clearInterval(intervalId);
  }, [pick.ticker]);

  const latestPrice = chartData.length > 0 ? chartData[chartData.length - 1].close : null;
  const chartVerdict = analyzeChart(analysis, chartData, t);
  const fundVerdict = analyzeFundamentals(earnings, patternData, t);
  const meta = getStockMeta(pick.ticker, lang);

  const isKRX = pick.ticker.endsWith(".KS") || pick.ticker.endsWith(".KQ");
  const currency = isKRX ? "₩" : "$";

  // Find significant moves — spread across entire chart, pick top 15 by magnitude
  const bigMoves = useMemo(() => {
    if (chartData.length <= 1) return [];
    const all: { date: string; pctChange: number }[] = [];
    for (let i = 1; i < chartData.length; i++) {
      const pct = ((chartData[i].close - chartData[i - 1].close) / chartData[i - 1].close) * 100;
      if (Math.abs(pct) >= 2.5) {
        all.push({ date: chartData[i].date, pctChange: pct });
      }
    }
    // Sort by magnitude (biggest moves first), take top 15, then re-sort by date for display
    all.sort((a, b) => Math.abs(b.pctChange) - Math.abs(a.pctChange));
    const top = all.slice(0, 15);
    top.sort((a, b) => a.date.localeCompare(b.date));
    return top;
  }, [chartData]);

  // Match move reasons to chart big moves
  const findMoveReason = useCallback((date: string) => {
    if (!moveReasons?.moves) return null;
    return moveReasons.moves.find((m: any) => m.date === date) || null;
  }, [moveReasons]);

  // Unified scoring — MUST match backend score_stock() formula:
  //   chart 30% + checklist 45% + fundamentals 25%
  const chartScore100 = chartVerdict.score100;
  const fundScore100 = fundVerdict.score100;
  const checklistScore100 = checklistLive?.summary?.score != null
    ? checklistLive.summary.score
    : (() => {
        const items = checklistLive?.checklist ?? [];
        if (!items.length) return null;
        const positives = items.filter((c: any) => c.status === "positive").length;
        const negatives = items.filter((c: any) => c.status === "negative").length;
        return Math.round(Math.max(0, Math.min(100, 50 + ((positives - negatives) / items.length) * 50)));
      })();
  const weightedParts = [
    { score: chartScore100, weight: 0.30 },
    { score: checklistScore100, weight: 0.45 },
    { score: fundScore100, weight: 0.25 },
  ].filter((part) => part.score != null) as { score: number; weight: number }[];
  const totalWeight = weightedParts.reduce((sum, part) => sum + part.weight, 0);
  const overallScore100 = totalWeight > 0
    ? Math.round(Math.max(5, Math.min(98, weightedParts.reduce((sum, part) => sum + part.score * part.weight, 0) / totalWeight)))
    : 50;
  const overall = scoreToVerdict(overallScore100, t);
  // Use fast newsAnalysis endpoint data immediately; upgrade to checklistLive data when it arrives
  const momentumNotes = checklistLive?.summary?.momentum_notes?.length
    ? checklistLive.summary.momentum_notes
    : newsAnalysis?.momentum_notes?.length
      ? newsAnalysis.momentum_notes
      : null; // null = still loading
  const liveImpactNews = checklistLive?.summary?.live_impact_news?.length
    ? checklistLive.summary.live_impact_news
    : newsAnalysis?.live_impact_news?.length
      ? newsAnalysis.live_impact_news
      : [];

  return (
    <div className="space-y-4">
      {/* ═══ OVERALL VERDICT — BIG & PROMINENT ═══ */}
      {!loading && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
          <div
            className="px-3 py-4 sm:px-5 sm:py-5"
            style={{ background: `linear-gradient(135deg, ${overall.color}20, ${overall.color}05)`, borderBottom: `2px solid ${overall.color}40` }}
          >
            {/* Top row: company name + price + score */}
            <div className="flex items-center gap-3 sm:gap-4 mb-4">
              <div className="flex-1 min-w-0">
                <h2 className="text-xl sm:text-2xl font-black text-[var(--color-text-primary)] truncate">{pick.name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm font-mono text-[var(--color-text-muted)]">{pick.ticker}</span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full font-bold"
                    style={{ background: pick.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)", color: pick.flag === "US" ? "#60a5fa" : "#f87171" }}
                  >{pick.flag}</span>
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:gap-3 mt-2">
                  {latestPrice && (
                    <span className="text-lg sm:text-xl font-mono font-black text-[var(--color-text-primary)]">
                      {currency}{Math.round(latestPrice).toLocaleString()}
                    </span>
                  )}
                  <span className="text-sm font-bold px-2 sm:px-3 py-1 rounded-lg" style={{ background: `${overall.color}18`, color: overall.color, border: `1px solid ${overall.color}30` }}>
                    {overall.label}
                  </span>
                  <span className="text-xs text-[var(--color-text-secondary)]">{overall.action}</span>
                </div>
              </div>
              {/* Big score circle */}
              <div className="flex flex-col items-center shrink-0">
                <div
                  className="rounded-full flex items-center justify-center border-4"
                  style={{ borderColor: overall.color, background: `${overall.color}10`, width: 60, height: 60 }}
                >
                  <span className="text-xl sm:text-2xl font-black" style={{ color: overall.color }}>{overallScore100}</span>
                </div>
                <span className="text-[9px] text-[var(--color-text-muted)] mt-1">{t("overallScore")}</span>
              </div>
            </div>

            {/* Chart + Fundamentals score badges */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 mb-4">
              <div className="flex-1 rounded-xl px-3 py-2" style={{ background: `${chartVerdict.color}10`, border: `1px solid ${chartVerdict.color}25` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--color-text-muted)]">{t("chartAnalysis")}</span>
                  <span className="text-sm font-black" style={{ color: chartVerdict.color }}>{chartScore100}{t("score")}</span>
                </div>
                <div className="mt-1 h-1.5 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${chartScore100}%`, background: chartVerdict.color }} />
                </div>
                <span className="text-[10px] font-bold mt-1 block" style={{ color: chartVerdict.color }}>{chartVerdict.label}</span>
              </div>
              <span className="hidden sm:block text-lg font-black text-[var(--color-text-muted)]">+</span>
              <div className="flex-1 rounded-xl px-3 py-2" style={{ background: `${fundVerdict.color}10`, border: `1px solid ${fundVerdict.color}25` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--color-text-muted)]">{t("earningsFundamentals")}</span>
                  <span className="text-sm font-black" style={{ color: fundVerdict.color }}>{fundScore100}{t("score")}</span>
                </div>
                <div className="mt-1 h-1.5 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${fundScore100}%`, background: fundVerdict.color }} />
                </div>
                <span className="text-[10px] font-bold mt-1 block" style={{ color: fundVerdict.color }}>{fundVerdict.label}</span>
              </div>
              <span className="hidden sm:block text-lg font-black text-[var(--color-text-muted)]">=</span>
              <div className="flex-1 rounded-xl px-3 py-2" style={{ background: `${overall.color}10`, border: `1px solid ${overall.color}25` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--color-text-muted)]">{t("overall")}</span>
                  <span className="text-sm font-black" style={{ color: overall.color }}>{overallScore100}{t("score")}</span>
                </div>
                <div className="mt-1 h-1.5 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${overallScore100}%`, background: overall.color }} />
                </div>
                <span className="text-[10px] font-bold mt-1 block" style={{ color: overall.color }}>{overall.label}</span>
              </div>
            </div>

            {/* Trading targets — chart-based entry/exit/stop */}
            {(() => {
              const tt = tradingTargets?.targets;
              if (!tt) return (
                <div className="text-center py-3">
                  <span className="text-[10px] text-[var(--color-text-muted)] animate-pulse">{t("tradingTargetCalc")}</span>
                </div>
              );

              const roundP = (v: number) => {
                if (v >= 100000) return Math.round(v / 1000) * 1000;
                if (v >= 10000) return Math.round(v / 100) * 100;
                if (v >= 100) return Math.round(v / 10) * 10;
                return Math.round(v * 10) / 10;
              };
              const fmt = (v: number) => `${currency}${roundP(v).toLocaleString()}`;
              const rr = tradingTargets.risk_reward_ratio;

              const cards = [
                { key: "buy", label: t("buyPoint"), price: tt.buy.price, pct: tt.buy.pct, reasons: tt.buy.reasons, color: "#3b82f6", pctLabel: t("belowBuy") },
                { key: "sell", label: t("sellPoint"), price: tt.sell.price, pct: tt.sell.pct, reasons: tt.sell.reasons, color: "#22c55e", pctLabel: t("aboveSell") },
                { key: "stop", label: t("stopLossLine"), price: tt.stop.price, pct: tt.stop.pct, reasons: tt.stop.reasons, color: "#ef4444", pctLabel: t("belowStop") },
              ];

              return (
                <div className="space-y-3">
                  {/* Risk/Reward ratio bar */}
                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--color-bg-hover)]">
                    <span className="text-[10px] font-bold text-[var(--color-text-muted)]">{t("profitLossRatio")}</span>
                    <div className="flex-1 h-2 rounded-full bg-[var(--color-bg-primary)] overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{
                        width: `${Math.min(100, rr / 5 * 100)}%`,
                        background: rr >= 2 ? "#22c55e" : rr >= 1 ? "#eab308" : "#ef4444"
                      }} />
                    </div>
                    <span className={`text-xs font-black ${rr >= 2 ? "text-[#22c55e]" : rr >= 1 ? "text-[#eab308]" : "text-[#ef4444]"}`}>
                      1:{rr.toFixed(1)} {rr >= 2.5 ? t("veryFavorable") : rr >= 1.5 ? t("favorable") : rr >= 1 ? t("average") : t("unfavorable")}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {cards.map(card => (
                      <div key={card.key}
                        className="rounded-xl p-3 cursor-pointer transition-all hover:scale-[1.02]"
                        style={{ background: `${card.color}11`, border: `1px solid ${card.color}40` }}
                        onClick={() => setShowTargetReasons(showTargetReasons === card.key ? null : card.key)}
                      >
                        <p className="text-[10px] font-bold mb-1" style={{ color: card.color }}>{card.label}</p>
                        <p className="text-base sm:text-lg font-black" style={{ color: card.color }}>{fmt(card.price)}</p>
                        <p className="text-[10px] mt-0.5" style={{ color: `${card.color}99` }}>
                          {card.pct >= 0 ? "+" : ""}{card.pct.toFixed(1)}% {card.pctLabel}
                        </p>
                        <p className="text-[9px] mt-1 underline" style={{ color: `${card.color}80` }}>
                          {showTargetReasons === card.key ? t("hideReasons") : t("showReasons")}
                        </p>
                        {showTargetReasons === card.key && (
                          <div className="mt-2 pt-2 border-t space-y-1" style={{ borderColor: `${card.color}30` }}>
                            {card.reasons.map((r: string, ri: number) => (
                              <p key={ri} className="text-[10px] leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                                • {r}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Strategy signals — chart indicator analysis */}
                  {tradingTargets.strategy_signals?.length > 0 && (
                    <div className="px-3 py-2.5 rounded-xl bg-[var(--color-bg-hover)]">
                      <p className="text-[10px] font-bold text-[var(--color-text-muted)] mb-1.5">{t("chartIndicatorAnalysis")}</p>
                      <div className="space-y-1">
                        {tradingTargets.strategy_signals.map((sig: string, si: number) => (
                          <p key={si} className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
                            {sig.includes("과매수") || sig.includes("데드크로스") || sig.includes("역배열") || sig.includes("하락") ? "🔴" :
                             sig.includes("과매도") || sig.includes("골든크로스") || sig.includes("정배열") || sig.includes("상승") || sig.includes("강함") ? "🟢" : "🟡"}{" "}
                            {sig}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Error state is now shown inside the loading screen — empty data never visible */}

      {!loadError && partialDataWarning && (
        <div className="bg-[var(--color-bg-card)] border border-[rgba(234,179,8,0.25)] rounded-2xl px-4 py-3">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {t("partialDataWarningMsg")}
          </p>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${sectorColor}15`, border: `2px solid ${sectorColor}30` }}>
            <Activity size={24} style={{ color: sectorColor }} className={loadError ? "" : "animate-pulse"} />
          </div>
          <div className="text-center">
            {loadError ? (
              <>
                <p className="text-base sm:text-lg font-bold text-[var(--color-text-primary)]">{t("waitingData")}</p>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">{pick.name} ({pick.ticker})</p>
                <p className="text-xs text-[rgba(234,179,8,0.9)] mt-2">
                  {retryCount < 3 ? `${t("autoRetrying")} (${retryCount}/3)` : t("checkServerConnection")}
                </p>
              </>
            ) : (
              <>
                <p className="text-base sm:text-lg font-bold text-[var(--color-text-primary)]">{t("aiAnalyzing")} {loadProgress}%</p>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">{pick.name} ({pick.ticker})</p>
                <p className="text-xs mt-2" style={{ color: sectorColor }}>{loadStage}</p>
              </>
            )}
          </div>
          {!loadError && (
            <div className="w-64 h-2 rounded-full bg-[var(--color-bg-hover)] overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500 ease-out" style={{ background: `linear-gradient(90deg, ${sectorColor}, ${sectorColor}cc)`, width: `${Math.max(5, loadProgress)}%` }} />
            </div>
          )}
          {loadError ? (
            <button
              onClick={() => setRetryCount((c) => c + 1)}
              className="mt-2 px-5 py-2 rounded-xl text-sm font-bold text-white transition-all"
              style={{ background: sectorColor }}
            >
              {t("retryButton")}
            </button>
          ) : (
            <p className="text-[10px] text-[var(--color-text-muted)]">
              {loadProgress < 30 ? t("fetchingFromServer") :
               loadProgress < 60 ? t("analyzingIndicators") :
               loadProgress < 85 ? t("collectingNewsEvents") :
               t("finalVerification")}
            </p>
          )}
        </div>
      ) : (
        <>
          {/* ═══ CHART — dots on big moves, hover for reason ═══ */}
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
            <div className="px-3 sm:px-5 pt-3 pb-3">
              <div className="flex items-center gap-1.5 mb-2">
                {periods.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setPeriod(p.value)}
                    className={`px-2.5 py-1 rounded text-[10px] font-medium transition-colors ${
                      period === p.value ? "text-white" : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                    }`}
                    style={period === p.value ? { backgroundColor: sectorColor } : {}}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <div className="relative">
              {chartLoading && <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--color-bg-card)]/60 rounded-lg"><span className="text-xs text-[var(--color-text-muted)] animate-pulse">{t("chartLoading")}</span></div>}
              <ResponsiveContainer width="100%" height={mob ? 220 : 260}>
                <ComposedChart data={chartData} margin={mob ? { top: 5, right: 5, bottom: 0, left: 0 } : undefined}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="date" tick={{ fill: "var(--color-text-muted)", fontSize: mob ? 8 : 9 }} tickFormatter={(v: string) => v.slice(5)} interval={mob ? "preserveStartEnd" : undefined} />
                  <YAxis domain={["auto", "auto"]} tick={{ fill: "var(--color-text-muted)", fontSize: mob ? 8 : 9 }} width={mob ? 40 : undefined} />
                  <Tooltip
                    content={({ active, payload }: any) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0]?.payload;
                      if (!d) return null;
                      const moveInfo = findMoveReason(d.date);
                      const bigMove = bigMoves.find((m) => m.date === d.date);
                      return (
                        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-3.5 shadow-2xl max-w-[calc(100vw-2rem)] sm:max-w-[340px]" style={{ backdropFilter: "blur(8px)" }}>
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-[10px] text-[var(--color-text-muted)]">{d.date}</p>
                            <p className="text-sm font-bold text-[var(--color-text-primary)]">{currency}{d.close?.toLocaleString()}</p>
                          </div>
                          {bigMove && (
                            <div className="mt-2 pt-2 border-t border-[var(--color-border)]">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: bigMove.pctChange > 0 ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)" }}>
                                  {bigMove.pctChange > 0 ? <TrendingUp size={16} className="text-[#22c55e]" /> : <TrendingDown size={16} className="text-[#ef4444]" />}
                                </div>
                                <div>
                                  <span className={`text-sm font-black ${bigMove.pctChange > 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
                                    {bigMove.pctChange > 0 ? "+" : ""}{bigMove.pctChange.toFixed(1)}%
                                  </span>
                                  {moveInfo?.move_type && <span className={`text-xs ml-1 font-bold ${bigMove.pctChange > 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>{moveInfo.move_type}</span>}
                                  {moveInfo?.vol_note && <span className="text-[10px] ml-2 px-1.5 py-0.5 rounded bg-[rgba(59,130,246,0.1)] text-[var(--color-accent-blue)] font-medium">{moveInfo.vol_note}</span>}
                                </div>
                              </div>
                              <p className="text-xs text-[var(--color-text-primary)] leading-relaxed font-semibold mb-1">
                                {moveInfo?.issue_summary || moveInfo?.reason || (bigMove.pctChange > 0 ? t("momentumUpSupply") : t("profitTakingCorrection"))}
                              </p>
                              {moveInfo?.issue_category && (
                                <p className="text-[10px] text-[var(--color-text-muted)] mb-1">
                                  {t("issueKeyword")} {moveInfo.issue_category}
                                </p>
                              )}
                              {moveInfo?.news?.length > 0 && (
                                <div className="mt-1.5 space-y-1">
                                  {moveInfo.news.slice(0, 2).map((n: any, ni: number) => (
                                    <p key={ni} className="text-[10px] text-[var(--color-text-secondary)] leading-snug pl-2 border-l-2 border-[var(--color-border)]">{typeof n === "string" ? n : n.title}{typeof n === "object" && n.source ? ` (${n.source})` : ""}</p>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="volume" fill={sectorColor} fillOpacity={0.08} yAxisId="vol" />
                  <YAxis yAxisId="vol" orientation="right" hide />
                  <Area type="monotone" dataKey="close" stroke={sectorColor} fill={sectorColor} fillOpacity={0.06} strokeWidth={2} />
                  {/* Event dots on big moves — show reason summary for large moves */}
                  {bigMoves.map((m, i) => {
                    const dp = chartData.find((d) => d.date === m.date);
                    if (!dp) return null;
                    const moveInfo = findMoveReason(m.date);
                    const isBig = Math.abs(m.pctChange) > 5;
                    const labelText = isBig && moveInfo?.issue_summary
                      ? moveInfo.issue_summary
                      : `${m.pctChange > 0 ? "+" : ""}${m.pctChange.toFixed(0)}%`;
                    return (
                      <ReferenceDot
                        key={`move-${i}`}
                        x={m.date}
                        y={dp.close}
                        r={mob ? (isBig ? 5 : 4) : (isBig ? 8 : 6)}
                        fill={m.pctChange > 0 ? "#22c55e" : "#ef4444"}
                        stroke="#fff"
                        strokeWidth={mob ? 1.5 : 2}
                        style={{ cursor: "pointer", filter: `drop-shadow(0 0 ${mob ? 3 : 6}px ${m.pctChange > 0 ? "rgba(34,197,94,0.7)" : "rgba(239,68,68,0.7)"})` }}
                        label={mob && !isBig ? undefined : { value: mob ? `${m.pctChange > 0 ? "+" : ""}${m.pctChange.toFixed(0)}%` : labelText, position: "top", fontSize: mob ? 7 : 9, fill: m.pctChange > 0 ? "#22c55e" : "#ef4444", fontWeight: 700 }}
                      />
                    );
                  })}
                  {/* Buy/Sell signal markers — only shown when user enters average price */}
                </ComposedChart>
              </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* ═══ EXPECTATION — 기대감 (실시간 뉴스 기반) ═══ */}
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${sectorColor}18`, border: `1px solid ${sectorColor}25` }}>
                <Zap size={16} style={{ color: sectorColor }} />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("currentExpectation")}</h3>
                <p className="text-[10px] text-[var(--color-text-muted)]">{t("expectationSubtitle")}</p>
              </div>
            </div>
            {!momentumNotes ? (
              <div className="px-4 py-5">
                {/* Animated progress bar */}
                <div className="w-full h-1.5 rounded-full bg-[var(--color-bg-hover)] overflow-hidden mb-3">
                  <div className="h-full rounded-full animate-pulse" style={{ background: sectorColor, width: "60%", animation: "pulse 1.5s ease-in-out infinite" }} />
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: `${sectorColor}15` }}>
                    <Zap size={14} style={{ color: sectorColor }} className="animate-spin" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[var(--color-text-primary)]">{t("analyzingExpectation")}</p>
                    <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{t("analyzingExpectationSub")}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-2">
                {momentumNotes.map((m: any, i: number) => (
                  <div
                    key={i}
                    className="px-4 py-3 rounded-xl transition-colors"
                    style={{
                      background: m.status === "negative" ? "rgba(239,68,68,0.08)" : `${sectorColor}08`,
                      border: `1px solid ${m.status === "negative" ? "rgba(239,68,68,0.2)" : `${sectorColor}15`}`,
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                        style={{
                          background: m.status === "negative" ? "#ef4444" : m.status === "positive" ? "#22c55e" : sectorColor,
                          boxShadow: `0 0 8px ${m.status === "negative" ? "rgba(239,68,68,0.6)" : m.status === "positive" ? "rgba(34,197,94,0.6)" : `${sectorColor}60`}`,
                        }}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-[var(--color-text-primary)]">{m.title}</p>
                        {m.detail && <p className="text-xs text-[var(--color-text-secondary)] mt-1 leading-relaxed">{m.detail}</p>}
                        {m.expected_condition && (
                          <div className="mt-2 px-3 py-2 rounded-lg bg-[var(--color-bg-hover)]">
                            <p className="text-[11px] text-[var(--color-text-muted)]">
                              <span className="font-bold text-[var(--color-text-secondary)]">{t("breakCondition")}</span> {m.expected_condition}
                            </p>
                          </div>
                        )}
                        {m.window && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{t("validWindow")} {m.window}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ═══ 재무 데이터 · 컨센서스 · 수급 · 동종업종 ═══ */}
          {checklistLive?.summary && (
            <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5 space-y-5">
              <div className="flex items-center gap-2">
                <Activity size={16} style={{ color: sectorColor }} />
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("financialData")}</h3>
              </div>

              {/* ── Row 1: Valuation + Consensus ── */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {(() => {
                  const val = checklistLive.summary.valuation || {};
                  const cards: {label: string; value: string; sub?: string}[] = [];
                  if (val.per != null) cards.push({ label: "PER", value: val.per.toFixed(1) + t("timesUnit"), sub: val.forward_per ? `${t("estimatedPrefix")} ${val.forward_per.toFixed(1)}${t("timesUnit")}` : undefined });
                  else if (val.forward_per != null) cards.push({ label: t("estimatedPER"), value: val.forward_per.toFixed(1) + t("timesUnit") });
                  if (val.pbr != null) cards.push({ label: "PBR", value: val.pbr.toFixed(2) + t("timesUnit") });
                  if (val.eps != null) cards.push({ label: "EPS", value: `${currency}${Math.round(val.eps).toLocaleString()}` });
                  if (val.dividend_yield != null) cards.push({ label: t("dividendYieldLabel"), value: `${(val.dividend_yield * 100).toFixed(2)}%` });
                  // 52w range
                  const h52 = checklistLive.summary.high_52w;
                  const l52 = checklistLive.summary.low_52w;
                  if (h52 && l52) cards.push({ label: t("52wRange"), value: `${currency}${Math.round(l52).toLocaleString()}`, sub: `~ ${currency}${Math.round(h52).toLocaleString()}` });
                  if (!cards.length) return null;
                  return cards.map((c, i) => (
                    <div key={i} className="px-3 py-2.5 rounded-xl bg-[var(--color-bg-hover)]">
                      <p className="text-[10px] text-[var(--color-text-muted)]">{c.label}</p>
                      <p className="text-sm font-black text-[var(--color-text-primary)] mt-0.5">{c.value}</p>
                      {c.sub && <p className="text-[9px] text-[var(--color-text-muted)] mt-0.5">{c.sub}</p>}
                    </div>
                  ));
                })()}
              </div>

              {/* ── Consensus target price ── */}
              {checklistLive.summary.consensus_target_price && (() => {
                const tp = checklistLive.summary.consensus_target_price;
                const upside = checklistLive.summary.consensus_upside;
                const opinion = checklistLive.summary.consensus_opinion || "";
                const uColor = upside > 0 ? "#22c55e" : upside < -5 ? "#ef4444" : "#eab308";
                return (
                  <div className="flex items-center gap-3 flex-wrap px-1">
                    <div className="flex items-center gap-2">
                      <Globe size={14} style={{ color: sectorColor }} />
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)]">{t("consensusLabel")}</span>
                    </div>
                    <div className="px-3 py-1.5 rounded-lg" style={{ background: `${uColor}08`, border: `1px solid ${uColor}18` }}>
                      <span className="text-xs font-black text-[var(--color-text-primary)]">{t("targetPriceLabel")} {currency}{Math.round(tp).toLocaleString()}</span>
                      {upside != null && <span className="text-xs font-black ml-2" style={{ color: uColor }}>({upside > 0 ? "+" : ""}{upside.toFixed(1)}%)</span>}
                    </div>
                    {opinion && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${sectorColor}12`, color: sectorColor }}>{opinion}</span>}
                  </div>
                );
              })()}

              {/* ── Investor flow (KRX) ── */}
              {checklistLive.summary.investor_flow && (() => {
                const flow = checklistLive.summary.investor_flow;
                const items = [
                  { label: t("foreignInvestor"), value: flow.foreign_net_5d },
                  { label: t("institutionInvestor"), value: flow.institution_net_5d },
                  { label: t("individualInvestor"), value: flow.individual_net_5d },
                ];
                const fmtQ = (v: number) => {
                  if (Math.abs(v) >= 1e6) return `${(v/1e6).toFixed(1)}M`;
                  if (Math.abs(v) >= 1e3) return `${(v/1e3).toFixed(0)}K`;
                  return v.toFixed(0);
                };
                return (
                  <div>
                    <div className="flex items-center gap-2 mb-2 px-1">
                      <TrendingUp size={14} style={{ color: sectorColor }} />
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)]">{t("supplyDemand5d")}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      {items.map((item) => {
                        const v = item.value || 0;
                        const c = v > 0 ? "#22c55e" : v < 0 ? "#ef4444" : "#6b7280";
                        return (
                          <div key={item.label} className="px-2 py-2 rounded-lg text-center" style={{ background: `${c}06`, border: `1px solid ${c}12` }}>
                            <p className="text-[10px] text-[var(--color-text-muted)]">{item.label}</p>
                            <p className="text-xs font-black" style={{ color: c }}>{v > 0 ? "+" : ""}{fmtQ(v)}{t("sharesUnit")}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              {/* ── Annual financials table ── */}
              {checklistLive.summary.annual_financials?.periods?.length > 0 && (() => {
                const fin = checklistLive.summary.annual_financials;
                const periods = fin.periods;
                const fmt = (v: number | null) => v == null ? "-" : v >= 10000 ? `${(v/10000).toFixed(1)}${t("trillionUnit")}` : `${Math.round(v).toLocaleString()}${t("hundredMillionUnit")}`;
                return (
                  <div>
                    <div className="flex items-center gap-2 mb-2 px-1">
                      <CheckCircle2 size={14} style={{ color: sectorColor }} />
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)]">{t("annualResults")}</span>
                      {fin.revenue_growth != null && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: fin.revenue_growth > 0 ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)", color: fin.revenue_growth > 0 ? "#22c55e" : "#ef4444" }}>
                          {t("revenuePrefix")}{fin.revenue_growth > 0 ? "+" : ""}{(fin.revenue_growth * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-[10px]">
                        <thead>
                          <tr className="border-b border-[var(--color-border)]">
                            <th className="text-left py-1 text-[var(--color-text-muted)] font-medium w-16"></th>
                            {periods.map((p: any) => (
                              <th key={p.key} className="text-right py-1 text-[var(--color-text-muted)] font-medium px-1">
                                {p.title}{p.is_consensus ? <span className="text-[8px] ml-0.5" style={{ color: sectorColor }}>(E)</span> : ""}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            { label: t("revenueLabel"), data: fin.revenue },
                            { label: t("operatingProfitLabel"), data: fin.operating_profit },
                            { label: t("netIncomeLabel"), data: fin.net_income },
                          ].filter(row => row.data).map((row) => (
                            <tr key={row.label} className="border-b border-[var(--color-border)]/30">
                              <td className="py-1.5 text-[var(--color-text-secondary)] font-medium">{row.label}</td>
                              {periods.map((p: any) => {
                                const v = row.data?.[p.key];
                                return <td key={p.key} className="text-right py-1.5 px-1 font-mono text-[var(--color-text-primary)]">{fmt(v)}</td>;
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })()}

              {/* ── Revenue/earnings growth (US fallback when no table) ── */}
              {!checklistLive.summary.annual_financials?.periods && checklistLive.summary.annual_financials && (() => {
                const fin = checklistLive.summary.annual_financials;
                const items: {label: string; value: number}[] = [];
                if (fin.revenue_growth != null) items.push({ label: t("revenueGrowthRate"), value: fin.revenue_growth });
                if (fin.earnings_growth != null) items.push({ label: t("earningsGrowthRate"), value: fin.earnings_growth });
                if (!items.length) return null;
                return (
                  <div className="flex gap-3 px-1">
                    {items.map((item) => {
                      const c = item.value > 0 ? "#22c55e" : item.value < 0 ? "#ef4444" : "#6b7280";
                      return (
                        <div key={item.label} className="px-3 py-2 rounded-lg" style={{ background: `${c}06`, border: `1px solid ${c}12` }}>
                          <p className="text-[10px] text-[var(--color-text-muted)]">{item.label}</p>
                          <p className="text-sm font-black" style={{ color: c }}>{item.value > 0 ? "+" : ""}{(item.value * 100).toFixed(1)}%</p>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}

              {/* ── Peers ── */}
              {checklistLive.summary.peers?.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2 px-1">
                    <Shield size={14} style={{ color: sectorColor }} />
                    <span className="text-[10px] font-bold text-[var(--color-text-muted)]">{t("peerGroup")}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {checklistLive.summary.peers.map((p: any) => {
                      const chg = p.change_pct;
                      const c = chg > 0 ? "#22c55e" : chg < 0 ? "#ef4444" : "#6b7280";
                      return (
                        <div key={p.code} className="px-2.5 py-1.5 rounded-lg" style={{ background: `${c}06`, border: `1px solid ${c}12` }}>
                          <span className="text-[10px] font-medium text-[var(--color-text-primary)]">{p.name}</span>
                          {chg != null && <span className="text-[10px] font-bold ml-1.5" style={{ color: c }}>{chg > 0 ? "+" : ""}{chg.toFixed(1)}%</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═══ AI 투자 논점 & 핵심 리스크 ═══ */}
          {checklistLive?.summary?.ai_investment_thesis && (
            <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${sectorColor}18`, border: `1px solid ${sectorColor}25` }}>
                  <Shield size={16} style={{ color: sectorColor }} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("aiInvestmentThesis")}</h3>
                  <p className="text-[10px] text-[var(--color-text-muted)]">{t("aiThesisSubtitle")}</p>
                </div>
                {checklistLive.summary.ai_confidence != null && (
                  <span className="ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${sectorColor}15`, color: sectorColor }}>
                    {t("aiConfidence")} {Math.round(checklistLive.summary.ai_confidence * 100)}%
                  </span>
                )}
              </div>

              {/* Investment thesis */}
              <div className="px-4 py-3 rounded-xl mb-3" style={{ background: `${sectorColor}06`, border: `1px solid ${sectorColor}12` }}>
                <p className="text-xs text-[var(--color-text-primary)] leading-relaxed">{checklistLive.summary.ai_investment_thesis}</p>
              </div>

              {/* Key risks */}
              {checklistLive.summary.ai_key_risks?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[10px] font-bold text-[var(--color-text-muted)] px-1">{t("keyRisks")}</p>
                  {checklistLive.summary.ai_key_risks.map((risk: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                      <AlertTriangle size={12} className="mt-0.5 shrink-0 text-[#ef4444]" />
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{risk}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* News alignment */}
              {checklistLive.summary.ai_news_alignment && (
                <div className="mt-3 px-3 py-2 rounded-lg bg-[var(--color-bg-hover)]">
                  <p className="text-[10px] text-[var(--color-text-muted)]">
                    <span className="font-bold text-[var(--color-text-secondary)]">{t("newsDataAlignment")}</span> {checklistLive.summary.ai_news_alignment}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ═══ 실시간 뉴스 ═══ */}
          {(() => {
            const deepArticles = newsAnalysis?.deep_articles ?? [];
            const hasDeep = deepArticles.length > 0;
            const articles = hasDeep ? deepArticles : liveImpactNews;

            if (articles.length === 0 && !newsAnalysis) {
              return (
                <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Newspaper size={16} className="text-[#6366f1]" />
                    <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("liveNewsDeepAnalysis")}</h3>
                  </div>
                  <div className="py-4 text-center">
                    <Newspaper size={18} className="text-[#6366f1] mx-auto mb-2 animate-pulse" />
                    <p className="text-xs text-[var(--color-text-muted)] animate-pulse">{t("collectingForwardPricing")}</p>
                  </div>
                </div>
              );
            }

            if (articles.length === 0) return null;

            const dirColor = (d: string) => d === "positive" ? "#22c55e" : d === "negative" ? "#ef4444" : "#eab308";
            const dirLabel = (d: string) => d === "positive" ? t("positive") : d === "negative" ? t("negative") : t("neutral");

            return (
              <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Newspaper size={16} className="text-[#6366f1]" />
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("liveNewsDeepAnalysis")}</h3>
                  <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">{articles.length}{t("articlesCount")}</span>
                </div>

                <div className="space-y-2">
                  {articles.map((a: any, i: number) => {
                    const dir = a.direction ?? a.impact_direction ?? "neutral";
                    const color = dirColor(dir);

                    return (
                      <div key={i} className="flex gap-3 px-3 py-2.5 rounded-xl" style={{ background: `${color}06`, border: `1px solid ${color}15` }}>
                        {/* Verdict badge */}
                        <div className="shrink-0 pt-0.5">
                          <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md text-white" style={{ background: color }}>
                            {dirLabel(dir)}
                          </span>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-[var(--color-text-primary)] leading-snug">{a.title}</p>
                          {a.explanation && (
                            <p className="text-xs text-[var(--color-text-secondary)] mt-1 leading-relaxed">{a.explanation}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[var(--color-text-muted)]">
                            {a.published_at && <span>{a.published_at}</span>}
                            {a.source && <span>· {a.source}</span>}
                            {a.url && <a href={a.url} target="_blank" rel="noopener noreferrer" className="text-[#6366f1] hover:underline ml-auto">{t("articleSource")}</a>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {/* ═══ MACRO / GEOPOLITICAL EVENTS ═══ */}
          {macroEvents?.events?.length > 0 && (
            <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] shrink-0">
                  <Globe size={16} className="text-[#ef4444]" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("globalMacroGeo")}</h3>
                  <p className="text-[10px] text-[var(--color-text-muted)]">{t("globalMacroSub")}</p>
                </div>
                {macroEvents.summary && (
                  <div className="w-full sm:w-auto sm:ml-auto flex items-center gap-2 mt-1 sm:mt-0">
                    <span className={`text-xs font-bold px-2 py-1 rounded-lg ${
                      macroEvents.summary.market_sentiment.includes("부정") ? "bg-[rgba(239,68,68,0.1)] text-[#ef4444]"
                      : macroEvents.summary.market_sentiment.includes("긍정") ? "bg-[rgba(34,197,94,0.1)] text-[#22c55e]"
                      : "bg-[rgba(234,179,8,0.1)] text-[#eab308]"
                    }`}>
                      {t("marketSentiment")} {macroEvents.summary.market_sentiment}
                    </span>
                  </div>
                )}
              </div>
              {macroEvents.summary && (
                <div className="mb-4 px-3 py-2.5 rounded-xl bg-[var(--color-bg-hover)]">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-[#22c55e]">{t("positive")} {macroEvents.summary.positive}</span>
                    <div className="flex-1 h-2 rounded-full bg-[var(--color-bg-primary)] overflow-hidden flex">
                      {macroEvents.summary.positive > 0 && <div className="h-full bg-[#22c55e]" style={{ width: `${macroEvents.summary.positive / macroEvents.summary.total * 100}%` }} />}
                      {macroEvents.summary.neutral > 0 && <div className="h-full bg-[#eab308]" style={{ width: `${macroEvents.summary.neutral / macroEvents.summary.total * 100}%` }} />}
                      {macroEvents.summary.negative > 0 && <div className="h-full bg-[#ef4444]" style={{ width: `${macroEvents.summary.negative / macroEvents.summary.total * 100}%` }} />}
                    </div>
                    <span className="text-xs font-bold text-[#ef4444]">{t("negative")} {macroEvents.summary.negative}</span>
                  </div>
                  <p className="text-[10px] text-[var(--color-text-muted)] mt-1.5">{macroEvents.summary.sentiment_detail}</p>
                </div>
              )}
              <div className="space-y-3">
                {Object.entries(macroEvents.by_category || {}).map(([category, events]: [string, any]) => (
                  <div key={category}>
                    <p className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-widest mb-2 flex items-center gap-1">
                      {category === "지정학" ? "🌍" : category === "유가/원자재" ? "🛢️" : category === "금리/통화" ? "💵" : category === "관세/무역" ? "📦" : category === "경기/물가" ? "📊" : "📈"} {(() => {
                        const catMap: Record<string, string> = { "지정학": t("geopolitics"), "유가/원자재": t("oilCommodities"), "금리/통화": t("ratesCurrency"), "관세/무역": t("tariffTrade"), "경기/물가": t("economyPrices") };
                        return catMap[category] || category;
                      })()}
                    </p>
                    <div className="space-y-1.5">
                      {events.slice(0, 4).map((e: any, i: number) => (
                        <div key={`${category}-${i}`} className="px-3 py-2.5 rounded-xl" style={{
                          background: e.impact_direction === "negative" ? "rgba(239,68,68,0.06)" : e.impact_direction === "positive" ? "rgba(34,197,94,0.06)" : "rgba(234,179,8,0.04)",
                          border: `1px solid ${e.impact_direction === "negative" ? "rgba(239,68,68,0.15)" : e.impact_direction === "positive" ? "rgba(34,197,94,0.15)" : "rgba(234,179,8,0.12)"}`,
                        }}>
                          <div className="flex items-start gap-2">
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded mt-0.5 ${
                              e.impact_direction === "negative" ? "bg-[rgba(239,68,68,0.15)] text-[#ef4444]"
                              : e.impact_direction === "positive" ? "bg-[rgba(34,197,94,0.15)] text-[#22c55e]"
                              : "bg-[rgba(234,179,8,0.15)] text-[#eab308]"
                            }`}>{e.impact_direction === "negative" ? t("negative") : e.impact_direction === "positive" ? t("positive") : t("neutral")}</span>
                            <div className="flex-1">
                              <p className="text-sm font-semibold text-[var(--color-text-primary)]">{e.title}</p>
                              {e.explanation && <p className="text-xs text-[var(--color-text-secondary)] mt-1">{e.explanation}</p>}
                              {e.source && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{e.source}{e.published_at ? ` · ${e.published_at}` : ""}</p>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══ LIVE CHECKLIST — FULL-SIZE CHARTS WITH THRESHOLDS ═══ */}
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-[rgba(99,102,241,0.1)] border border-[rgba(99,102,241,0.2)] shrink-0">
                <Shield size={16} className="text-[#6366f1]" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("investmentChecklistLive")}</h3>
                <p className="text-[10px] text-[var(--color-text-muted)]">{t("checklistCorrelation")}</p>
              </div>
              {checklistLive === null && (
                <div className="ml-auto flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-[#6366f1] border-t-transparent rounded-full animate-spin" />
                  <span className="text-[10px] text-[#6366f1] font-semibold">{t("analyzing")}</span>
                  <ElapsedTimer active={checklistLive === null} />
                </div>
              )}
              {checklistLive?.checklist && (() => {
                const filtered = checklistLive.checklist.filter((c: any) =>
                  !c.is_news_item && !c.name?.startsWith("뉴스:") && !c.name?.startsWith("이슈 모니터링:")
                );
                // Only count items with real data for safety ratio
                const withData = filtered.filter((c: any) => !c.data_missing && c.status !== "unknown");
                const total = withData.length;
                const passed = withData.filter((c: any) => c.status === "positive").length;
                const failed = withData.filter((c: any) => c.status === "negative").length;
                const ratio = total > 0 ? passed / total : 0;
                const failRatio = total > 0 ? failed / total : 0;
                const safetyColor = failRatio >= 0.5 ? "#ef4444" : ratio >= 0.6 ? "#22c55e" : ratio >= 0.3 ? "#eab308" : "#ef4444";
                const safetyLabel = failRatio >= 0.5 ? t("dangerous") : ratio >= 0.6 ? t("safe") : ratio >= 0.3 ? t("caution") : t("dangerous");
                return (
                  <div className="flex items-center gap-2 w-full sm:w-auto sm:ml-auto mt-1 sm:mt-0">
                    <div className="flex gap-0.5 overflow-hidden">
                      {filtered.map((_: any, ci: number) => {
                        const s = filtered[ci].status;
                        const missing = filtered[ci].data_missing || s === "unknown";
                        return (
                          <div key={ci} className="w-2 sm:w-3 h-5 sm:h-6 rounded-sm" style={{
                            background: missing ? "#64748b30" : s === "positive" ? "#22c55e" : s === "negative" ? "#ef4444" : "#eab30850"
                          }} />
                        );
                      })}
                    </div>
                    <span className="text-base sm:text-lg font-black" style={{ color: safetyColor }}>{passed}/{total}</span>
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: safetyColor + "18", color: safetyColor, border: `1px solid ${safetyColor}30` }}>
                      {safetyLabel}
                    </span>
                  </div>
                );
              })()}
            </div>
            <div className="space-y-4">
              {/* Loading progress banner when checklist is still loading */}
              {checklistLive === null && (
                <div className="rounded-xl p-4 bg-[rgba(99,102,241,0.06)] border border-[rgba(99,102,241,0.15)]">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-6 h-6 border-2 border-[#6366f1] border-t-transparent rounded-full animate-spin shrink-0" />
                    <div>
                      <p className="text-xs font-bold text-[var(--color-text-primary)]">{t("collectingIndicators")}</p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{t("indicatorSteps")}</p>
                    </div>
                  </div>
                  {/* Animated step indicator */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                    <span className="px-2 py-0.5 rounded bg-[#6366f1] text-white font-bold">1</span>
                    <span className="text-[var(--color-text-muted)]">{t("stepCollect")}</span>
                    <span className="text-[var(--color-text-muted)]">→</span>
                    <span className="px-2 py-0.5 rounded bg-[rgba(99,102,241,0.2)] text-[#6366f1] font-bold animate-pulse">2</span>
                    <span className="text-[var(--color-text-muted)] animate-pulse">{t("stepAnalyzing")}</span>
                    <span className="text-[var(--color-text-muted)]">→</span>
                    <span className="px-2 py-0.5 rounded bg-[var(--color-bg-hover)] text-[var(--color-text-muted)] font-bold">3</span>
                    <span className="text-[var(--color-text-muted)]">{t("stepComplete")}</span>
                    <span className="sm:ml-auto flex items-center gap-2 text-[var(--color-text-muted)]">
                      <ElapsedTimer active={checklistLive === null} />
                      <span>{t("aboutSeconds")}</span>
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full h-1 rounded-full bg-[var(--color-bg-hover)] mt-2 overflow-hidden">
                    <div className="h-full bg-[#6366f1] rounded-full" style={{ width: "45%", animation: "checklistProgress 30s linear forwards" }} />
                  </div>
                </div>
              )}
              {checklistLive?.checklist?.filter((item: any) =>
                // Filter out legacy news items from cached data — news is now in the dedicated section
                !item.is_news_item && !item.name?.startsWith("뉴스:") && !item.name?.startsWith("이슈 모니터링:")
              ).map((item: any, i: number) => {
                const isMissing = item.data_missing || item.status === "unknown";
                const statusColor = isMissing ? "#64748b" : item.status === "positive" ? "#22c55e" : item.status === "negative" ? "#ef4444" : "#eab308";
                const hasTrend = item.trend_data?.length > 3;

                // Merge trend_data with stock overlay + compute moving averages
                const mergedData = hasTrend ? item.trend_data.map((td: any, idx: number, arr: any[]) => {
                  const stockPt = item.stock_overlay?.find((s: any) => s.date === td.date);
                  // Simple moving averages for trend visualization
                  const ma5 = idx >= 4 ? arr.slice(idx - 4, idx + 1).reduce((s: number, p: any) => s + p.close, 0) / 5 : null;
                  const ma20 = idx >= 19 ? arr.slice(idx - 19, idx + 1).reduce((s: number, p: any) => s + p.close, 0) / 20 : null;
                  return { ...td, stock_norm: stockPt?.stock_norm ?? null, stock_price: stockPt?.stock_price ?? null, ma5: ma5 ? Math.round(ma5 * 100) / 100 : null, ma20: ma20 ? Math.round(ma20 * 100) / 100 : null };
                }) : [];

                // Is current price in the danger zone?
                const inDanger = item.thresholds?.danger_line != null && item.thresholds?.current != null && (
                  item.thresholds.danger_dir === "below" ? item.thresholds.current <= item.thresholds.danger_line : item.thresholds.current >= item.thresholds.danger_line
                );

                return (
                  <div key={i} className="rounded-xl overflow-hidden" style={{ border: `2px solid ${statusColor}40` }}>
                    {/* SIMPLE STATUS BANNER — name + big status only */}
                    <div className="px-3 sm:px-4 py-3 flex items-start sm:items-center justify-between gap-2" style={{ background: `${statusColor}12` }}>
                      <div className="flex items-start sm:items-center gap-2 sm:gap-2.5 flex-1 min-w-0">
                        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 sm:mt-0" style={{ background: `${statusColor}20` }}>
                          {isMissing ? <MinusCircle size={16} color="#64748b" /> : item.status === "positive" ? <CheckCircle2 size={16} color="#22c55e" /> : item.status === "negative" ? <XCircle size={16} color="#ef4444" /> : <MinusCircle size={16} color="#eab308" />}
                        </div>
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <p className="text-xs sm:text-sm font-bold text-[var(--color-text-primary)]">{item.name}</p>
                            {item.importance >= 60 && <span className="text-[9px] font-black px-1.5 py-0.5 rounded-full bg-[rgba(239,68,68,0.2)] text-[#ef4444]">{t("keyLabel")}</span>}
                          </div>
                          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{item.detail || "—"}</p>
                          {item.why_it_matters && <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">{item.why_it_matters}</p>}
                          {item.expected_condition && <p className="text-[11px] text-[var(--color-text-muted)] mt-1">{t("expectedCondition")} {item.expected_condition}</p>}
                          {item.window && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{t("checkWindow")} {item.window}</p>}
                        </div>
                      </div>
                      {/* Big clear status — the ONE thing you need to see */}
                      <div className="shrink-0 text-right px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg" style={{
                        background: item.status === "positive" ? "rgba(59,130,246,0.15)" : item.status === "negative" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                        border: `1.5px solid ${item.status === "positive" ? "rgba(59,130,246,0.3)" : item.status === "negative" ? "rgba(239,68,68,0.3)" : "rgba(245,158,11,0.3)"}`
                      }}>
                        <p className="text-sm sm:text-lg font-black whitespace-nowrap" style={{ color: item.status === "positive" ? "#3b82f6" : item.status === "negative" ? "#ef4444" : "#d97706" }}>
                          {item.status === "positive" ? t("safeStatus") : item.status === "negative" ? t("dangerStatus") : t("cautionStatus")}
                        </p>
                      </div>
                    </div>

                    {/* Unified chart — actual vs expected + danger zone */}
                    {(() => {
                      // Build chart data: monthly-sampled for commodity, quarterly for earnings
                      const qData: { quarter: string; value: number }[] = item.quarterly_chart || [];
                      let chartPts: { label: string; value: number; expected: number | null }[] = [];
                      let unit = "";

                      if (hasTrend && mergedData.length > 5) {
                        const step = Math.max(1, Math.floor(mergedData.length / 12));
                        const rawPts: number[] = [];
                        for (let si = 0; si < mergedData.length; si += step) {
                          const d = mergedData[si];
                          const monthLabel = d.date?.slice(5, 7) + t("monthLabel");
                          const val = Math.round(d.close * 100) / 100;
                          rawPts.push(val);
                          chartPts.push({ label: monthLabel, value: val, expected: null });
                        }
                        const lastD = mergedData[mergedData.length - 1];
                        const lastLabel = lastD.date?.slice(5, 7) + t("monthLabel");
                        if (chartPts[chartPts.length - 1]?.label !== lastLabel || chartPts[chartPts.length - 1]?.value !== lastD.close) {
                          const val = Math.round(lastD.close * 100) / 100;
                          rawPts.push(val);
                          chartPts.push({ label: lastLabel + "*", value: val, expected: null });
                        }
                        // Compute expected line + extend into future
                        if (rawPts.length >= 3) {
                          const n = rawPts.length;
                          const sumX = n * (n - 1) / 2;
                          const sumY = rawPts.reduce((s, v) => s + v, 0);
                          const sumXY = rawPts.reduce((s, v, xi) => s + xi * v, 0);
                          const sumX2 = n * (n - 1) * (2 * n - 1) / 6;
                          const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
                          const intercept = (sumY - slope * sumX) / n;
                          chartPts = chartPts.map((p, pi) => ({ ...p, expected: Math.round((intercept + slope * pi) * 100) / 100 }));
                          // Add 3 future projection points (value=null, expected continues)
                          const lastMonth = parseInt(chartPts[chartPts.length - 1].label) || 12;
                          for (let fi = 1; fi <= 3; fi++) {
                            const futureMonth = ((lastMonth - 1 + fi) % 12) + 1;
                            const futureIdx = n + fi - 1;
                            chartPts.push({
                              label: `${futureMonth}${t("monthLabel")} (${t("expectedLabel")})`,
                              value: null as any,
                              expected: Math.round((intercept + slope * futureIdx) * 100) / 100,
                            });
                          }
                        }
                        unit = "$";
                      } else if (qData.length >= 2) {
                        const rawPts = qData.map(q => q.value);
                        chartPts = qData.map((q: any) => {
                          const [y, m] = q.quarter.split("-");
                          const qNum = Math.ceil(parseInt(m) / 3);
                          const isPrelim = q.preliminary === true;
                          return { label: isPrelim ? `${y.slice(2)}'Q${qNum} (${t("prelimLabel")})` : `${y.slice(2)}'Q${qNum}`, value: q.value, expected: null };
                        });
                        // Linear trend expected line + future quarters
                        if (rawPts.length >= 3) {
                          const n = rawPts.length;
                          const sumX = n * (n - 1) / 2;
                          const sumY = rawPts.reduce((s, v) => s + v, 0);
                          const sumXY = rawPts.reduce((s, v, xi) => s + xi * v, 0);
                          const sumX2 = n * (n - 1) * (2 * n - 1) / 6;
                          const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
                          const intercept = (sumY - slope * sumX) / n;
                          chartPts = chartPts.map((p, pi) => ({ ...p, expected: Math.round((intercept + slope * pi) * 10) / 10 }));
                          // Add 2 future quarter projections
                          const lastQ = qData[qData.length - 1]?.quarter || "2025-04";
                          const [ly, lm] = lastQ.split("-").map(Number);
                          for (let fi = 1; fi <= 2; fi++) {
                            const fm = lm + fi * 3;
                            const fy = ly + Math.floor((fm - 1) / 12);
                            const fmMod = ((fm - 1) % 12) + 1;
                            const fqNum = Math.ceil(fmMod / 3);
                            chartPts.push({
                              label: `${String(fy).slice(2)}'Q${fqNum} (${t("expectedLabel")})`,
                              value: null as any,
                              expected: Math.round((intercept + slope * (n + fi - 1)) * 10) / 10,
                            });
                          }
                        }
                        unit = "%";
                      }

                      if (chartPts.length < 2) return null;

                      const dangerLine = item.thresholds?.danger_line;
                      const dangerDir = item.thresholds?.danger_dir;
                      // currentVal = last actual data point; lastExpected = where expected line says we SHOULD be now
                      const actualPts = chartPts.filter(p => p.value != null);
                      const currentVal = hasTrend ? (item.thresholds?.current ?? actualPts[actualPts.length - 1]?.value) : (item.thresholds?.current ?? item.value);
                      const lastExpected = actualPts[actualPts.length - 1]?.expected;
                      const futureExpected = chartPts[chartPts.length - 1]?.expected;
                      const isInDanger = dangerLine != null && currentVal != null && (
                        dangerDir === "below" ? currentVal <= dangerLine : currentVal >= dangerLine
                      );
                      // Check if actual is below expected trend (danger signal)
                      const belowExpected = lastExpected != null && currentVal != null && (
                        dangerDir === "below" || dangerDir == null ? currentVal < lastExpected : currentVal > lastExpected
                      );

                      const vals = chartPts.map(p => p.value).filter((v): v is number => v != null);
                      const expectedVals = chartPts.map(p => p.expected).filter((v): v is number => v != null);
                      const allVals = [...vals, ...expectedVals, ...(dangerLine != null ? [dangerLine] : [])];
                      const chartMin = Math.min(...allVals);
                      const chartMax = Math.max(...allVals);
                      const pad = (chartMax - chartMin) * 0.15 || 5;
                      const yMin = chartMin - pad;
                      const yMax = chartMax + pad;

                      // Trend analysis (actual data only)
                      const firstVal = actualPts[0]?.value ?? 0;
                      const lastVal = actualPts[actualPts.length - 1]?.value ?? 0;
                      const totalChg = firstVal !== 0 ? ((lastVal - firstVal) / Math.abs(firstVal) * 100) : 0;

                      // Summary — focus on expected vs actual
                      const months = hasTrend ? Math.max(1, Math.round(item.trend_data.length / 21)) : actualPts.length;
                      const periodLbl = hasTrend ? `${months}${t("monthsUnit")}` : `${actualPts.length}${t("quartersUnit")}`;
                      let summaryParts: string[] = [];
                      summaryParts.push(`${periodLbl}${t("periodChange")}${totalChg >= 0 ? t("rise") : t("fall")} (${totalChg >= 0 ? "+" : ""}${totalChg.toFixed(1)}${hasTrend ? "%" : "%p"})`);
                      if (belowExpected && lastExpected != null) {
                        summaryParts.push(`${unit}${lastExpected} → ${unit}${currentVal}`);
                      } else if (lastExpected != null && currentVal != null) {
                        summaryParts.push(`${t("expectedLabel")} ${unit}${lastExpected} / ${t("actualLabel")} ${unit}${currentVal}`);
                      }
                      if (futureExpected != null) {
                        summaryParts.push(`${t("forwardOutlook")}: ${unit}${futureExpected}`);
                      }
                      if (dangerLine != null && currentVal != null) {
                        if (isInDanger) {
                          summaryParts.push(`${t("dangerLineLabel")}(${unit}${dangerLine}) → ${t("dangerPriceDecline")}`);
                        }
                      }

                      return (
                        <div className="px-4 pb-4 pt-2">
                          {/* Alert banners */}
                          {inDanger && (
                            <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg bg-[rgba(239,68,68,0.12)] border border-[rgba(239,68,68,0.3)]">
                              <AlertTriangle size={16} className="text-[#ef4444] shrink-0" />
                              <span className="text-xs font-bold text-[#ef4444]">{t("dangerZoneAlert")}</span>
                            </div>
                          )}
                          {!inDanger && item.thresholds?.trend_warn && (
                            <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg bg-[rgba(234,179,8,0.08)] border border-[rgba(234,179,8,0.2)]">
                              <AlertTriangle size={14} className="text-[#eab308] shrink-0" />
                              <span className="text-[11px] font-bold text-[#eab308]">{item.thresholds.trend_warn}</span>
                            </div>
                          )}

                          {/* Chart — clean white, line + dots + value labels */}
                          <div className="h-44 rounded-xl overflow-hidden bg-white border border-[#e5e7eb] shadow-sm">
                            <ResponsiveContainer width="100%" height="100%">
                              <ComposedChart data={chartPts} margin={mob ? { top: 20, right: 8, bottom: 4, left: 4 } : { top: 28, right: 20, bottom: 6, left: 20 }}>
                                <defs>
                                  <linearGradient id={`cg-${i}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={isInDanger ? "#ef4444" : "#1d4ed8"} stopOpacity={0.12} />
                                    <stop offset="100%" stopColor={isInDanger ? "#ef4444" : "#1d4ed8"} stopOpacity={0.01} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid horizontal vertical={false} stroke="#f1f5f9" />
                                <XAxis
                                  dataKey="label"
                                  tick={{ fill: "#475569", fontSize: mob ? 9 : 11, fontWeight: 600 }}
                                  axisLine={{ stroke: "#cbd5e1" }}
                                  tickLine={false}
                                  interval={mob ? "preserveStartEnd" : 0}
                                />
                                <YAxis
                                  domain={[yMin, yMax]}
                                  tick={{ fill: "#94a3b8", fontSize: mob ? 8 : 9 }}
                                  tickFormatter={(v: number) => `${unit}${v >= 1000 ? (v/1000).toFixed(0) + "k" : Number(v.toFixed(1))}`}
                                  axisLine={false}
                                  tickLine={false}
                                  width={mob ? 36 : 48}
                                  tickCount={mob ? 4 : undefined}
                                />
                                {/* Danger zone — red fill */}
                                {dangerLine != null && (
                                  dangerDir === "below"
                                    ? <ReferenceArea y1={yMin} y2={dangerLine} fill="#ef4444" fillOpacity={0.12} />
                                    : <ReferenceArea y1={dangerLine} y2={yMax} fill="#ef4444" fillOpacity={0.12} />
                                )}
                                {/* Danger line */}
                                {dangerLine != null && (
                                  <ReferenceLine y={dangerLine} stroke="#ef4444" strokeWidth={mob ? 1.5 : 2} strokeDasharray="8 4"
                                    label={{ value: mob ? `${unit}${dangerLine}` : `${t("dangerLineLabel")} ${unit}${dangerLine}`, position: dangerDir === "below" ? "insideBottomLeft" : "insideTopLeft", fontSize: mob ? 8 : 9, fill: "#ef4444", fontWeight: 800 }} />
                                )}
                                {/* Expected trend line — dashed blue */}
                                <Area type="monotone" dataKey="expected" stroke="#3b82f6" strokeWidth={2} strokeDasharray="6 3" fill="none" dot={false} />
                                {/* Area fill under actual line */}
                                <Area type="monotone" dataKey="value" stroke="none" fill={`url(#cg-${i})`} connectNulls={false} />
                                {/* Actual line — bold, stops at current data */}
                                <Area
                                  type="monotone"
                                  dataKey="value"
                                  stroke={isInDanger ? "#ef4444" : "#1e3a5f"}
                                  strokeWidth={3}
                                  fill="none"
                                  connectNulls={false}
                                  dot={({ cx, cy, payload, index: di }: any) => {
                                    if (payload.value == null) return <g key={`d-${di}`} />;
                                    const isLast = di === actualPts.length - 1;
                                    const isPrelim = (payload.label || "").includes(t("prelimLabel"));
                                    const dotColor = isPrelim ? "#f59e0b" : isInDanger ? "#ef4444" : "#1e3a5f";
                                    const r = mob ? (isLast ? 5 : 3) : (isLast ? 7 : 4);
                                    return <circle key={`d-${di}`} cx={cx} cy={cy} r={r} fill={isPrelim ? "#fef3c7" : "#fff"} stroke={dotColor} strokeWidth={isLast ? 2.5 : 1.5} />;
                                  }}
                                  label={({ x, y, value, index }: any) => {
                                    if (value == null) return null;
                                    const isLast = index === actualPts.length - 1;
                                    const isPrelim = (chartPts[index]?.label || "").includes(t("prelimLabel"));
                                    const color = isPrelim ? "#d97706" : isLast ? (isInDanger ? "#ef4444" : "#1d4ed8") : "#334155";
                                    // Mobile: only show label on last and preliminary points to avoid overlap
                                    if (mob && !isLast && !isPrelim) return null;
                                    const fs = mob ? (isLast ? 10 : 8) : (isLast ? 13 : 10);
                                    // Alternate label position to reduce overlap
                                    const offsetY = mob ? (index % 2 === 0 ? -8 : -16) : -12;
                                    const fmtVal = typeof value === "number" ? (value >= 1000 ? `${(value/1000).toFixed(1)}k` : value.toFixed(value < 10 ? 2 : 1)) : value;
                                    return (
                                      <text key={`l-${index}`} x={x} y={y + offsetY} textAnchor="middle" fill={color} fontSize={fs} fontWeight={isLast ? 900 : 700}>
                                        {isPrelim ? "⚡" : ""}{fmtVal}
                                      </text>
                                    );
                                  }}
                                />
                                {/* Expected future labels */}
                                <Area
                                  type="monotone"
                                  dataKey="expected"
                                  stroke="none"
                                  fill="none"
                                  dot={false}
                                  label={({ x, y, value, index }: any) => {
                                    // Only label future points (where value is null)
                                    if (chartPts[index]?.value != null || value == null) return null;
                                    // On mobile, only show the last expected label
                                    if (mob && index < chartPts.length - 1 && chartPts[index + 1]?.value == null) return null;
                                    return (
                                      <text key={`el-${index}`} x={x} y={y - (mob ? 6 : 10)} textAnchor="middle" fill="#3b82f6" fontSize={mob ? 8 : 10} fontWeight={700}>
                                        {typeof value === "number" ? (value >= 1000 ? `${(value/1000).toFixed(1)}k` : value.toFixed(value < 10 ? 2 : 1)) : value}
                                      </text>
                                    );
                                  }}
                                />
                              </ComposedChart>
                            </ResponsiveContainer>
                          </div>

                          {/* Status + actual vs expected comparison */}
                          <div className="mt-3 rounded-xl overflow-hidden" style={{
                            border: `2px solid ${isInDanger ? "rgba(239,68,68,0.35)" : belowExpected ? "rgba(245,158,11,0.35)" : "rgba(59,130,246,0.3)"}`
                          }}>
                            <div className="px-3 sm:px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2" style={{
                              background: isInDanger ? "rgba(239,68,68,0.1)" : belowExpected ? "rgba(245,158,11,0.08)" : "rgba(59,130,246,0.06)"
                            }}>
                              <div className="min-w-0">
                                <p className="text-sm sm:text-base font-black" style={{ color: isInDanger ? "#ef4444" : belowExpected ? "#d97706" : "#3b82f6" }}>
                                  {isInDanger ? t("dangerPriceDecline") : belowExpected ? t("cautionIndicatorLag") : t("safeUpside")}
                                </p>
                                <p className="text-[11px] sm:text-xs mt-0.5 text-[var(--color-text-muted)]">
                                  {lastExpected != null && currentVal != null
                                    ? belowExpected
                                      ? `${t("needIndicatorForPrice")} ${unit}${lastExpected.toLocaleString()} ${t("needSuffix")} ${unit}${currentVal.toLocaleString()} ${t("insufficientLabel")}`
                                      : `${unit}${lastExpected.toLocaleString()} ${t("aboveForUpside")} ${unit}${currentVal.toLocaleString()} ${t("sufficientLabel")}`
                                    : `${t("currentPrefix")} ${unit}${currentVal?.toLocaleString()}`}
                                  {futureExpected != null ? `${t("futureExpectedPrefix")} ${unit}${futureExpected.toLocaleString()}` : ""}
                                </p>
                              </div>
                              <span className="text-lg sm:text-xl font-black font-mono" style={{ color: isInDanger ? "#ef4444" : belowExpected ? "#d97706" : "#1e293b" }}>
                                {unit}{currentVal?.toLocaleString()}
                              </span>
                            </div>
                            <div className="px-3 sm:px-4 py-2 flex flex-wrap items-center gap-2 sm:gap-3" style={{ background: "rgba(0,0,0,0.02)" }}>
                              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-[#1e3a5f] inline-block rounded" /><span className="text-[10px] text-[var(--color-text-muted)]">{t("actualLabel")}</span></span>
                              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-[#3b82f6] inline-block rounded" style={{ borderTop: "2px dashed #3b82f6" }} /><span className="text-[10px] text-[#3b82f6]">{t("expectedTrend")}</span></span>
                              <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-sm bg-[rgba(239,68,68,0.25)] inline-block" /><span className="text-[10px] text-[#ef4444]">{t("dangerZone")}</span></span>
                              <p className="text-[10px] text-[var(--color-text-muted)] sm:ml-auto">{summaryParts[0]}</p>
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* News headlines if present */}
                    {item.news_headlines?.length > 0 && (
                      <div className="px-4 pb-3">
                        <div className="space-y-1.5">
                          {item.news_headlines.map((headline: string, hi: number) => (
                            <div key={hi} className="flex items-start gap-2 px-3 py-2 rounded-lg bg-[var(--color-bg-hover)]">
                              <Newspaper size={12} className="text-[var(--color-text-muted)] shrink-0 mt-0.5" />
                              <p className="text-[11px] leading-snug text-[var(--color-text-secondary)]">{headline}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }) || meta.checklist.map((item, i) => (
                <div key={i} className="rounded-xl p-4 bg-[var(--color-bg-primary)] border border-[var(--color-border)]">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-[var(--color-text-muted)] border-t-transparent rounded-full animate-spin opacity-40" />
                    <span className="text-sm text-[var(--color-text-secondary)]">{item}</span>
                    <span className="text-[9px] text-[var(--color-text-muted)] ml-auto px-2 py-0.5 rounded bg-[var(--color-bg-hover)]">{t("collecting")}</span>
                  </div>
                  <div className="mt-3 h-16 bg-[var(--color-bg-hover)] rounded-lg overflow-hidden relative">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[rgba(99,102,241,0.05)] to-transparent" style={{ animation: "skeletonShimmer 2s infinite" }} />
                  </div>
                </div>
              ))}
              {/* Show missing meta items as "pending" — only for stocks with specific meta (not default fallback) */}
              {checklistLive?.checklist && (STOCK_META_BI[pick.ticker] || STOCK_META_BI[pick.ticker.replace(".KS", "").replace(".KQ", "")]) && (() => {
                const liveNames = new Set((checklistLive.checklist as any[]).map((c: any) => c.name?.toLowerCase()));
                const missing = meta.checklist.filter((item) => !liveNames.has(item.toLowerCase()));
                if (missing.length === 0) return null;
                return missing.map((item, i) => (
                  <div key={`meta-${i}`} className="rounded-xl p-4 bg-[var(--color-bg-primary)] border border-[var(--color-border)] opacity-60">
                    <div className="flex items-center gap-2">
                      <MinusCircle size={16} className="text-[var(--color-text-muted)]" />
                      <span className="text-sm text-[var(--color-text-secondary)]">{item}</span>
                      <span className="text-[9px] text-[var(--color-text-muted)] ml-auto">{t("dataCollecting")}</span>
                    </div>
                  </div>
                ));
              })()}
            </div>
          </div>

          {/* AI prediction detail removed — score already shown in verdict */}
        </>
      )}
    </div>
  );
}

/* ── Commodity History Chart ── */

function CommodityChart({ symbol, name }: { symbol: string; name: string; sectorColor: string }) {
  const [data, setData] = useState<{ date: string; close: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCommodityHistory(symbol, "6mo")
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) return <div className="h-24 bg-[var(--color-bg-hover)] rounded-lg animate-pulse" />;
  if (data.length === 0) return null;

  const first = data[0].close;
  const last = data[data.length - 1].close;
  const changePercent = ((last - first) / first) * 100;
  const isUp = changePercent >= 0;

  return (
    <div className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-xl p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-[var(--color-text-primary)]">{name}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-[var(--color-text-secondary)]">${last.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
          <span className={`text-[10px] font-bold ${isUp ? "text-[var(--color-accent-green)]" : "text-[var(--color-accent-red)]"}`}>
            {isUp ? "+" : ""}{changePercent.toFixed(1)}%
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={60}>
        <ComposedChart data={data}>
          <Area
            type="monotone"
            dataKey="close"
            stroke={isUp ? "#22c55e" : "#ef4444"}
            fill={isUp ? "#22c55e" : "#ef4444"}
            fillOpacity={0.08}
            strokeWidth={1.5}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── Risk Section ── */

const COMMODITY_SYMBOLS: Record<string, { symbol: string; nameKey: string }[]> = {
  "ai-semi": [
    { symbol: "HG=F", nameKey: "copperName" },
    { symbol: "GC=F", nameKey: "goldName" },
    { symbol: "SOXX", nameKey: "soxIndexName" },
  ],
  "robotics": [
    { symbol: "HG=F", nameKey: "copperName" },
    { symbol: "ALI=F", nameKey: "aluminumName" },
  ],
  "smr-nuclear": [
    { symbol: "URA", nameKey: "uraniumName" },
    { symbol: "NG=F", nameKey: "natGasName" },
  ],
  "cybersec": [
    { symbol: "BUG", nameKey: "cyberEtfName" },
  ],
  "space": [
    { symbol: "UFO", nameKey: "spaceEtfName" },
    { symbol: "ITA", nameKey: "defenseEtfName" },
  ],
  "biotech": [
    { symbol: "XBI", nameKey: "biotechXbiName" },
    { symbol: "IBB", nameKey: "biotechIbbName" },
  ],
  "quantum": [
    { symbol: "QTUM", nameKey: "quantumEtfName" },
  ],
  "hydrogen": [
    { symbol: "ICLN", nameKey: "cleanEnergyName" },
    { symbol: "PL=F", nameKey: "platinumName" },
  ],
};

function RiskSection({ sector }: { sector: SectorDef }) {
  const { t } = useLanguage();
  const severityConfig = {
    high: { label: t("highRisk"), color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.18)" },
    medium: { label: t("mediumRisk"), color: "#eab308", bg: "rgba(234,179,8,0.08)", border: "rgba(234,179,8,0.18)" },
    low: { label: t("lowRisk"), color: "#22c55e", bg: "rgba(34,197,94,0.08)", border: "rgba(34,197,94,0.18)" },
  };

  const commodities = COMMODITY_SYMBOLS[sector.id] || [];

  return (
    <div className="space-y-6">
      {/* Commodity / Indicator Charts */}
      {commodities.length > 0 && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={16} style={{ color: sector.color }} />
            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("trackingIndicatorChart")}</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {commodities.map((c) => (
              <CommodityChart key={c.symbol} symbol={c.symbol} name={t(c.nameKey as any)} sectorColor={sector.color} />
            ))}
          </div>
          {/* Tracking indicators list */}
          <div className="mt-3 flex flex-wrap gap-2">
            {sector.trackingIndicators.map((ind, i) => (
              <span key={i} className="px-2.5 py-1 rounded-lg text-[10px] font-medium" style={{ background: sector.color + "10", color: sector.color, border: `1px solid ${sector.color}20` }}>
                {ind}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sector Risks */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={16} style={{ color: "#ef4444" }} />
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("sectorRisk")}</h3>
        </div>
        <div className="space-y-2">
          {sector.risks.map((risk, i) => {
            const cfg = severityConfig[risk.severity];
            return (
              <div key={i} className="rounded-lg px-3 py-2.5" style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-bold" style={{ color: cfg.color }}>{risk.title}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: cfg.color + "15", color: cfg.color }}>
                    {cfg.label}
                  </span>
                </div>
                <p className="text-[11px] text-[var(--color-text-secondary)]">{risk.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Related materials */}
      {sector.materials.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {sector.materials.map((m) => (
            <span key={m} className="px-3 py-1.5 rounded-lg text-xs font-medium" style={{ background: sector.color + "10", color: sector.color, border: `1px solid ${sector.color}20` }}>
              {m}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main Page ── */

/* ── Sector News keywords for Korean search ── */
const SECTOR_NEWS_KEYWORDS: Record<string, string> = {
  "ai-semi": "반도체",
  "robotics": "로봇",
  "smr-nuclear": "원자력",
  "cybersec": "사이버보안",
  "space": "우주항공",
  "biotech": "바이오",
  "quantum": "양자컴퓨팅",
  "hydrogen": "수소",
};

/* ── Sector Overview (default view) ── */

function SectorOverview({ sector }: { sector: SectorDef }) {
  const { t } = useLanguage();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [sectorPulse, setSectorPulse] = useState<any>(null);
  const [sectorPulseLoading, setSectorPulseLoading] = useState(true);

  useEffect(() => {
    const keyword = SECTOR_NEWS_KEYWORDS[sector.id] || sector.name;
    searchNews(keyword)
      .then(setNews)
      .catch(() => {})
      .finally(() => setNewsLoading(false));
  }, [sector.id, sector.name]);

  useEffect(() => {
    setSectorPulseLoading(true);
    fetchSectorPulse(sector.id)
      .then(setSectorPulse)
      .catch(() => {})
      .finally(() => setSectorPulseLoading(false));
  }, [sector.id]);

  return (
    <div className="space-y-5 overflow-y-auto h-full pb-8 sm:pr-1">
      {/* Sector description */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: `linear-gradient(135deg, ${sector.color}30, ${sector.color}10)`, border: `1.5px solid ${sector.color}50` }}
          >
            <sector.icon size={24} strokeWidth={1.5} style={{ color: sector.color }} />
          </div>
          <div>
            <h2 className="text-lg font-bold" style={{ color: sector.color }}>{sector.name}</h2>
            <p className="text-xs text-[var(--color-text-muted)]">Top {sector.picks.length}{t("topStocksCount")}</p>
          </div>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{sector.desc}</p>

        {/* Materials */}
        {sector.materials.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {sector.materials.map((m) => (
              <span key={m} className="px-2.5 py-1 rounded-full text-[10px] font-medium" style={{ background: sector.color + "10", color: sector.color, border: `1px solid ${sector.color}20` }}>
                {m}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
        <div className="flex items-center gap-2 mb-3">
          <Shield size={16} style={{ color: sector.color }} />
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("sectorChecklistLive")}</h3>
          {sectorPulse?.summary?.score != null && (
            <span
              className="ml-auto text-xs font-bold px-2.5 py-1 rounded-full"
              style={{
                background: sectorPulse.summary.score >= 60 ? "rgba(34,197,94,0.14)" : sectorPulse.summary.score <= 40 ? "rgba(239,68,68,0.14)" : "rgba(234,179,8,0.14)",
                color: sectorPulse.summary.score >= 60 ? "#22c55e" : sectorPulse.summary.score <= 40 ? "#ef4444" : "#eab308",
              }}
            >
              {t("sectorScore")} {sectorPulse.summary.score}{t("score")}
            </span>
          )}
        </div>
        {sectorPulseLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-[var(--color-bg-hover)] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : sectorPulse?.checklist?.length ? (
          <div className="space-y-3">
            {sectorPulse.checklist.map((item: any, i: number) => {
              const tone = item.status === "positive" ? "#22c55e" : item.status === "negative" ? "#ef4444" : "#eab308";
              return (
                <div
                  key={i}
                  className="rounded-xl px-4 py-3"
                  style={{ background: `${tone}10`, border: `1px solid ${tone}22` }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[var(--color-text-primary)]">{item.name}</p>
                      <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">{item.why_it_matters}</p>
                      <p className="text-[11px] text-[var(--color-text-muted)] mt-1">{t("currentLabel")} {item.detail}</p>
                      <p className="text-[11px] text-[var(--color-text-muted)] mt-1">{t("requiredCondition")} {item.expected_condition}</p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{t("checkWindow")} {item.window}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-lg font-black" style={{ color: tone }}>
                        {item.status === "positive" ? t("bullish") : item.status === "negative" ? t("warning") : t("neutral")}
                      </p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{item.symbol}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-[var(--color-text-muted)]">{t("sectorChecklistFailed")}</p>
        )}
      </div>

      {/* News / Hot issues */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-3 sm:p-5">
        <div className="flex items-center gap-2 mb-3">
          <Newspaper size={16} style={{ color: sector.color }} />
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{t("latestNewsMomentum")}</h3>
        </div>
        {newsLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-[var(--color-bg-hover)] rounded-lg animate-pulse" />
            ))}
          </div>
        ) : news.length === 0 ? (
          <p className="text-xs text-[var(--color-text-muted)]">{t("newsNotFound")}</p>
        ) : (
          <div className="space-y-1.5">
            {news.slice(0, 10).map((article, i) => (
              <a
                key={i}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2 px-3 py-2 rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors group"
              >
                <Zap size={12} className="mt-0.5 shrink-0" style={{ color: sector.color }} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[var(--color-text-primary)] group-hover:text-white line-clamp-2 leading-relaxed">
                    {article.title}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-[var(--color-text-muted)]">{article.source}</span>
                    {article.publishedAt && (
                      <span className="text-[10px] text-[var(--color-text-muted)]">{article.publishedAt}</span>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Risk & Tracking */}
      <RiskSection sector={sector} />
    </div>
  );
}

/* ── Main Page ── */

export default function SectorDetailPage() {
  const { t } = useLanguage();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedPick, setSelectedPick] = useState<StockPick | null>(null);

  const sector = SECTORS.find((s) => s.id === id);
  const isDynamic = searchParams.get("dynamic") === "1";
  const stockParam = searchParams.get("stock");

  // Auto-select stock from URL query param (?stock=NVDA)
  useEffect(() => {
    if (stockParam) {
      // First check if it's a top pick in the current sector
      if (sector) {
        const match = sector.picks.find((pk) => pk.ticker === stockParam || pk.ticker === decodeURIComponent(stockParam));
        if (match) {
          setSelectedPick(match);
          return;
        }
      }
      // Also check ALL sectors for the stock
      for (const s of SECTORS) {
        const match = s.picks.find((pk) => pk.ticker === stockParam || pk.ticker === decodeURIComponent(stockParam));
        if (match) {
          setSelectedPick(match);
          return;
        }
      }
      // Dynamic stock: not a top pick in any sector
      const dynamicName = searchParams.get("name") || stockParam;
      const dynamicFlag = searchParams.get("flag") === "KR" ? "KR" : "US";
      setSelectedPick({
        ticker: stockParam,
        name: dynamicName,
        flag: dynamicFlag,
        desc: t("aiLiveAnalysis"),
      });
    }
  }, [sector, stockParam, searchParams]);

  // Dynamic stock: full-screen analysis (works even without a valid sector)
  if (isDynamic && selectedPick) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="max-w-4xl mx-auto p-3 sm:p-5">
          {/* Back button */}
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-white transition-colors mb-4"
          >
            <ArrowLeft size={16} /> {t("backToMindmap")}
          </button>
          <StockAnalysisCard pick={selectedPick} sectorColor="#3b82f6" />
        </div>
      </div>
    );
  }

  // Dynamic stock loading: stock param exists but selectedPick not yet set
  if (isDynamic && stockParam && !selectedPick) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#3b82f6] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-[var(--color-text-secondary)]">{t("loadingStockInfo")}</p>
        </div>
      </div>
    );
  }

  if (!sector) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <p className="text-lg text-[var(--color-text-secondary)]">{t("sectorNotFound")}</p>
        <Link to="/" className="text-sm text-[var(--color-accent-blue)] hover:underline">{t("backToMindmap")}</Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row h-full overflow-hidden">
      {/* ─── Left Sidebar: Top 5 List ─── */}
      <div className="sm:w-64 shrink-0 border-b sm:border-b-0 sm:border-r border-[var(--color-border)] glass-strong flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[var(--color-border)] flex items-center gap-2">
          <button
            onClick={() => navigate("/")}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-white hover:bg-white/10 transition-colors"
          >
            <ArrowLeft size={14} />
          </button>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${sector.color}20`, border: `1px solid ${sector.color}30` }}
            >
              <sector.icon size={16} strokeWidth={1.5} style={{ color: sector.color }} />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold truncate" style={{ color: sector.color }}>{sector.name}</h2>
            </div>
          </div>
        </div>

        {/* Sector Overview button */}
        <button
          onClick={() => setSelectedPick(null)}
          className={`hidden sm:block mx-3 mt-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
            selectedPick === null
              ? "text-white"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]"
          }`}
          style={selectedPick === null ? { background: sector.color, boxShadow: `0 4px 12px ${sector.color}30` } : {}}
        >
          {t("sectorOverviewNews")}
        </button>

        {/* Divider */}
        <div className="hidden sm:block mx-3 mt-3 mb-2">
          <p className="text-[9px] font-semibold text-[var(--color-text-muted)] uppercase tracking-widest">
            {t("top5Stocks")}
          </p>
        </div>

        {selectedPick && !sector.picks.some((pick) => pick.ticker === selectedPick.ticker) && (
          <div className="hidden sm:block mx-3 mb-3 rounded-xl px-3 py-3 border border-[rgba(59,130,246,0.2)] bg-[rgba(59,130,246,0.08)]">
            <p className="text-[10px] font-semibold text-[var(--color-accent-blue)]">{t("liveSearchStock")}</p>
            <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-1">{selectedPick.name}</p>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{selectedPick.ticker}</p>
          </div>
        )}

        {/* Stock list */}
        <div className="flex sm:flex-col sm:flex-1 overflow-x-auto sm:overflow-x-hidden sm:overflow-y-auto px-3 pb-2 sm:pb-4 gap-1 sm:gap-0 sm:space-y-1 scrollbar-hide">
          {sector.picks.map((pick, i) => {
            const isActive = selectedPick?.ticker === pick.ticker;
            return (
              <button
                key={pick.ticker}
                onClick={() => setSelectedPick(pick)}
                className={`shrink-0 sm:shrink sm:w-full flex items-center gap-2 sm:gap-2.5 px-3 py-2 sm:py-2.5 rounded-xl text-left transition-all duration-200 ${
                  isActive ? "text-white" : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]"
                }`}
                style={isActive ? {
                  background: `linear-gradient(135deg, ${sector.color}cc, ${sector.color}99)`,
                  boxShadow: `0 4px 16px ${sector.color}30`,
                } : {}}
              >
                <div
                  className="w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0"
                  style={isActive ? {
                    background: "rgba(255,255,255,0.2)",
                    color: "#fff",
                  } : {
                    background: `${sector.color}15`,
                    color: sector.color,
                    border: `1px solid ${sector.color}20`,
                  }}
                >
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-xs font-semibold truncate ${isActive ? "text-white" : ""}`}>
                      {pick.name}
                    </span>
                    <span
                      className="text-[8px] px-1 py-0.5 rounded font-bold shrink-0"
                      style={{
                        background: pick.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                        color: pick.flag === "US" ? "#60a5fa" : "#f87171",
                      }}
                    >
                      {pick.flag}
                    </span>
                  </div>
                  <p className={`text-[10px] truncate mt-0.5 ${isActive ? "text-white/70" : "text-[var(--color-text-muted)]"}`}>
                    {pick.ticker}
                  </p>
                </div>
                <ChevronRight size={12} className={`shrink-0 ${isActive ? "text-white/60" : "text-[var(--color-text-muted)]"}`} />
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── Right Main Area ─── */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-5">
        {selectedPick === null ? (
          <SectorOverview sector={sector} />
        ) : (
          <div className="space-y-4 pb-8">
            <StockAnalysisCard pick={selectedPick} sectorColor={sector.color} />
          </div>
        )}
      </div>
    </div>
  );
}
