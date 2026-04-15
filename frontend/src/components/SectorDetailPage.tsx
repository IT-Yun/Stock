import { useEffect, useState, useCallback, useMemo } from "react";
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
import { SECTORS } from "@/data/sectors";
import type { SectorDef, StockPick } from "@/data/sectors";
import { fetchChartData, fetchAnalysis, fetchEarnings, fetchPatternAnalysis, fetchCommodityHistory, searchNews, fetchPrediction, fetchMoveReasons, fetchChecklistLive, fetchSectorPulse, fetchMacroEvents, fetchTradingTargets } from "@/api/client";
import type { ChartDataPoint, AnalysisResult, NewsArticle } from "@/types";

const periods = [
  { label: "1개월", value: "1mo" },
  { label: "3개월", value: "3mo" },
  { label: "6개월", value: "6mo" },
  { label: "1년", value: "1y" },
] as const;

/* ── Internal analysis engine (user never sees raw indicators) ── */

/** Convert a 0-100 score to label + color. Single source of truth for all verdicts. */
function scoreToVerdict(score: number): { label: string; color: string; action: string } {
  if (score >= 80) return { label: "적극 매수", color: "#16a34a", action: "목표 비중 80~100% 투자" };
  if (score >= 65) return { label: "매수 추천", color: "#22c55e", action: "목표 비중 50~70% 분할 매수" };
  if (score >= 45) return { label: "관망", color: "#eab308", action: "신규 진입 보류, 기존 보유 유지" };
  if (score >= 30) return { label: "비중 축소", color: "#ef4444", action: "보유분 30~50% 익절 고려" };
  return { label: "매도 권고", color: "#dc2626", action: "보유분 전량 정리 검토" };
}

function analyzeChart(analysis: AnalysisResult | null, chartData: ChartDataPoint[]): {
  score100: number;
  label: string;
  color: string;
  reason: string;
} {
  if (!analysis) return { score100: 50, label: "분석 중", color: "#64748b", reason: "데이터 로딩 중" };
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
  if (ind.rsi != null) reasons.push(`RSI ${ind.rsi.toFixed(0)}${ind.rsi > 70 ? "(과매수)" : ind.rsi < 30 ? "(과매도)" : ""}`);
  if (ind.macd != null && ind.macd_signal != null) reasons.push(`MACD ${ind.macd > ind.macd_signal ? "골든" : "데드"}크로스`);
  if (ind.sma_20 != null && ind.sma_50 != null) reasons.push(`SMA ${ind.sma_20 > ind.sma_50 ? "상승" : "하락"}추세`);

  const v = scoreToVerdict(score100);
  return { score100, label: v.label, color: v.color, reason: reasons.join(" · ") };
}

function analyzeFundamentals(earnings: any, patternData: any, checklistLive: any): {
  score100: number;
  label: string;
  color: string;
  reason: string;
} {
  // ── PRIMARY: Use checklist score if available (most comprehensive, per-stock analysis) ──
  // The checklist already evaluates earnings, commodities, sector health, and news per stock
  if (checklistLive?.summary?.score != null) {
    const clScore = checklistLive.summary.score as number;
    const items = checklistLive?.checklist ?? [];
    const positives = items.filter((c: any) => c.status === "positive").length;
    const negatives = items.filter((c: any) => c.status === "negative").length;
    const reasons: string[] = [];

    // Enrich with earnings data if available
    let earningsBonus = 0;
    if (earnings && !earnings.error) {
      if (earnings.revenue_growth != null) {
        if (earnings.revenue_growth > 0.2) { earningsBonus += 5; reasons.push(`매출 +${(earnings.revenue_growth * 100).toFixed(0)}%`); }
        else if (earnings.revenue_growth > 0.05) { earningsBonus += 2; reasons.push(`매출 +${(earnings.revenue_growth * 100).toFixed(0)}%`); }
        else if (earnings.revenue_growth < -0.05) { earningsBonus -= 5; reasons.push(`매출 ${(earnings.revenue_growth * 100).toFixed(0)}%`); }
      }
      if (earnings.earnings_growth != null) {
        if (earnings.earnings_growth > 0.3) earningsBonus += 4;
        else if (earnings.earnings_growth > 0) earningsBonus += 1;
        else if (earnings.earnings_growth < -0.1) earningsBonus -= 4;
      }
      if (earnings.pe_ratio != null && earnings.forward_pe != null) {
        if (earnings.forward_pe < earnings.pe_ratio * 0.7) {
          earningsBonus += 3;
          reasons.push(`Forward PE ${earnings.forward_pe.toFixed(0)} < Trailing ${earnings.pe_ratio.toFixed(0)}`);
        } else if (earnings.forward_pe > earnings.pe_ratio * 1.2) {
          earningsBonus -= 2;
        }
      }
      if (earnings.profit_margin != null) {
        if (earnings.profit_margin > 0.2) earningsBonus += 2;
        else if (earnings.profit_margin < 0) { earningsBonus -= 3; reasons.push("순손실 상태"); }
      }
    }

    // Pattern analysis bonus
    if (patternData?.summary) {
      if (patternData.summary.up_probability > 65) { earningsBonus += 3; reasons.push(`패턴 상승확률 ${patternData.summary.up_probability}%`); }
      else if (patternData.summary.up_probability < 35) { earningsBonus -= 3; reasons.push(`패턴 상승확률 ${patternData.summary.up_probability}%`); }
    }

    // Combine: checklist score (primary) + earnings/pattern bonus (secondary)
    // Checklist score is 0-100; earningsBonus is small adjustment ±15 max
    const finalScore = Math.round(Math.max(0, Math.min(100, clScore + earningsBonus)));

    if (positives > 0) reasons.push(`핵심지표 ${positives}개 긍정`);
    if (negatives > 0) reasons.push(`${negatives}개 위험`);

    const v = scoreToVerdict(finalScore);
    return { score100: finalScore, label: v.label, color: v.color, reason: reasons.join(" · ") };
  }

  // ── FALLBACK: earnings-only scoring when checklist not loaded yet ──
  if (!earnings || earnings.error) return { score100: 50, label: "데이터 없음", color: "#64748b", reason: "" };

  let score = 0;
  let checks = 0;
  const reasons: string[] = [];

  if (earnings.revenue_growth != null) {
    checks++;
    if (earnings.revenue_growth > 0.2) { score += 2; reasons.push(`매출 +${(earnings.revenue_growth * 100).toFixed(0)}%`); }
    else if (earnings.revenue_growth > 0) { score += 1; reasons.push(`매출 +${(earnings.revenue_growth * 100).toFixed(0)}%`); }
    else { score -= 1; reasons.push(`매출 ${(earnings.revenue_growth * 100).toFixed(0)}%`); }
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
    else if (earnings.profit_margin < 0) { score -= 2; reasons.push("순손실 상태"); }
  }
  if (earnings.roe != null) {
    checks++;
    if (earnings.roe > 0.2) score += 1;
    else if (earnings.roe < 0) score -= 1;
  }
  if (patternData?.summary) {
    checks++;
    if (patternData.summary.up_probability > 60) { score += 1; reasons.push(`패턴 상승확률 ${patternData.summary.up_probability}%`); }
    else if (patternData.summary.up_probability < 40) { score -= 1; reasons.push(`패턴 상승확률 ${patternData.summary.up_probability}%`); }
  }

  const norm = checks > 0 ? score / checks : 0;
  const score100 = Math.round(Math.max(0, Math.min(100, (norm + 1) * 50)));

  const v = scoreToVerdict(score100);
  return { score100, label: v.label, color: v.color, reason: reasons.join(" · ") };
}

/* ── Stock checklist & momentum data ── */

type MomentumItem = { title: string; detail: string; condition: string };
const STOCK_META: Record<string, { checklist: string[]; momentum: MomentumItem[] }> = {
  "NVDA": {
    checklist: ["데이터센터 매출 성장률 (QoQ)", "HBM/GPU ASP 추이", "AI 캡엑스 지출 (MSFT/GOOG/META)", "중국 수출 규제 변동", "경쟁사 AMD MI300 점유율"],
    momentum: [
      { title: "Blackwell Ultra 출시 (2026 H2)", detail: "차세대 GPU 출시로 데이터센터 교체 수요가 본격화됩니다", condition: "출시 일정이 지켜지고, 주요 고객(MS/Google/Meta)의 사전 주문이 유지되어야 합니다" },
      { title: "데이터센터 캡엑스 $200B+ 지속", detail: "빅테크 AI 인프라 투자가 계속 확대되고 있어 GPU 수요를 뒷받침합니다", condition: "빅테크 실적 발표에서 AI 캡엑스 가이던스가 유지/상향되어야 합니다" },
      { title: "자율주행/로봇 GPU 수요 신규", detail: "자동차·로봇 분야에서 새로운 GPU 수요처가 열리고 있습니다", condition: "Tesla FSD, Waymo 등 자율주행 실적이 가시화되어야 합니다" },
      { title: "중국 규제 완화 가능성", detail: "미중 관계 개선 시 수출 규제 완화로 중국 매출 회복 가능", condition: "미국 정부의 수출 규제 정책 변화 여부를 모니터링해야 합니다" },
    ],
  },
  "TSM": {
    checklist: ["3nm/2nm 가동률", "웨이퍼 ASP 변동", "월별 매출 공시 (MoM)", "지정학 리스크 (대만 해협)", "CAPEX 집행률"],
    momentum: [
      { title: "2nm 양산 시작 (2026)", detail: "차세대 2nm 공정 양산이 시작되면 ASP 상승과 점유율 확대가 기대됩니다", condition: "2nm 수율이 목표치에 도달하고, Apple/NVDA 등 핵심 고객 주문이 확정되어야 합니다" },
      { title: "미국 애리조나 팹 가동", detail: "미국 현지 생산으로 지정학 리스크 완화 + 미국 정부 보조금 수혜", condition: "팹 가동률이 경제성 있는 수준까지 올라야 하며, 인력 확보가 순조로워야 합니다" },
    ],
  },
  "AVGO": {
    checklist: ["커스텀 AI칩 수주 현황", "VMware 통합 시너지", "네트워킹 매출 비중", "배당 성장률", "Google TPU 계약"],
    momentum: [
      { title: "Google TPU v6 대량 수주", detail: "Google 커스텀 AI칩 수주가 매출 성장의 핵심 동력입니다", condition: "Google의 AI 인프라 투자가 유지되고, TPU 점유율이 NVDA GPU 대비 확대되어야 합니다" },
      { title: "AI 네트워킹 스위치 수요 급증", detail: "AI 데이터센터 확장에 필수적인 네트워킹 장비 수요가 폭발적으로 증가 중", condition: "데이터센터 신규 건설 속도가 유지되어야 합니다" },
    ],
  },
  "000660.KS": {
    checklist: ["DRAM 현물/계약가격 추이", "HBM 출하량/ASP", "재고 수준 (bit growth)", "NVDA HBM 공급 비중", "영업이익률 추이"],
    momentum: [
      { title: "HBM4 양산 (2026)", detail: "차세대 HBM4 양산으로 NVDA 독점 공급 지위를 공고히 합니다", condition: "HBM4 수율이 양산 가능 수준이고, NVDA의 차세대 GPU에 채택이 확정되어야 합니다" },
      { title: "DRAM 업사이클 진입", detail: "서버 DRAM 가격 상승 사이클이 시작되어 실적 개선이 가속화됩니다", condition: "DRAM 현물가격이 계약가격 대비 프리미엄을 유지해야 합니다. 재고가 쌓이면 사이클이 꺾입니다" },
    ],
  },
  "005930.KS": {
    checklist: ["DRAM/NAND 가격 추이", "파운드리 수율 개선", "HBM 수율 이슈", "갤럭시 판매량", "자사주 매입"],
    momentum: [
      { title: "HBM3E 수율 개선 기대", detail: "HBM 수율 문제가 해결되면 NVDA 공급 확대로 실적이 크게 개선됩니다", condition: "HBM3E 수율이 경쟁사(SK하이닉스) 수준까지 올라야 하며, NVDA 인증을 통과해야 합니다" },
      { title: "밸류업 프로그램 (주주환원)", detail: "자사주 매입·소각으로 주당가치 상승이 기대됩니다", condition: "자사주 매입 규모가 기대 이상이어야 하며, 지속적인 주주환원 정책이 확인되어야 합니다" },
    ],
  },
  "TSLA": {
    checklist: ["차량 인도량 (QoQ)", "Optimus 로봇 진행상황", "FSD 라이센싱 수익", "마진율 추이", "에너지 사업 매출"],
    momentum: [
      { title: "Optimus 2027 공장 투입", detail: "휴머노이드 로봇이 공장에 투입되면 로봇 사업의 매출 가시성이 생깁니다", condition: "2027년 일정이 지켜져야 하며, 로봇 성능이 실제 공장 작업에 적합해야 합니다" },
      { title: "로보택시 출시", detail: "자율주행 택시 서비스가 시작되면 소프트웨어 반복매출이 폭발합니다", condition: "규제 승인과 안전 기록이 확보되어야 하며, 사고 리스크가 통제되어야 합니다" },
    ],
  },
  "ISRG": {
    checklist: ["다빈치 시술 건수 (QoQ)", "시스템 설치 대수", "반복매출 비중", "경쟁사 진입 여부", "중국 시장 확대"],
    momentum: [
      { title: "다빈치 5 신규 설치 가속", detail: "최신 다빈치 5 시스템 설치가 빨라지면 반복매출(소모품)이 크게 증가합니다", condition: "병원들의 설비 투자 예산이 유지되고, 경쟁 로봇(Medtronic Hugo)이 점유율을 빼앗지 않아야 합니다" },
    ],
  },
  "CEG": {
    checklist: ["원전 가동률", "전력 계약 가격(PPA)", "Microsoft/Google 전력 계약", "규제 환경 변화", "전력 수요 전망"],
    momentum: [
      { title: "AI 데이터센터 전력 수요 폭증", detail: "AI 데이터센터 확장으로 안정적인 원전 전력 수요가 급증하고 있습니다", condition: "빅테크의 데이터센터 건설 계획이 유지되고, 전력 장기계약(PPA) 가격이 상승 추세여야 합니다" },
    ],
  },
  "CCJ": {
    checklist: ["우라늄 현물가격", "장기 계약가격", "공급 부족 규모", "카자흐스탄 생산량", "러시아 수출 제재"],
    momentum: [
      { title: "우라늄 $100/lb 돌파", detail: "우라늄 가격 상승은 CCJ 매출과 이익에 직결됩니다", condition: "러시아 우라늄 수출 제재가 유지되고, 신규 원전 건설 수주가 계속되어야 합니다" },
    ],
  },
  "CRWD": {
    checklist: ["ARR 성장률", "고객당 모듈 수", "순유지율(NRR)", "경쟁사 대비 점유율", "보안사고 리스크"],
    momentum: [
      { title: "AI 기반 위협탐지 확대", detail: "AI 보안 솔루션 수요가 기존 방화벽을 대체하며 빠르게 성장합니다", condition: "ARR 성장률 30%+ 유지와 신규 모듈 채택률이 증가해야 합니다. 블루스크린 같은 보안사고 재발 시 급락 위험" },
    ],
  },
  "CRSP": {
    checklist: ["임상시험 진행 단계", "FDA 승인 일정", "적응증 확대 파이프라인", "현금 보유량(런웨이)", "경쟁 유전자치료 동향"],
    momentum: [
      { title: "Casgevy FDA 승인 완료", detail: "겸상적혈구병 유전자치료제가 FDA 승인을 받아 상업화 매출이 시작됩니다", condition: "보험사 커버리지 확대로 환자 접근성이 높아져야 하고, 경쟁 치료제(블루버드바이오) 대비 효능 우위가 유지되어야 합니다" },
      { title: "적응증 확대 (암, 심혈관)", detail: "유전자편집 기술을 암·심혈관 질환으로 확장하면 시장이 수십배 커집니다", condition: "임상 2/3상 결과가 긍정적이어야 하며, FDA의 유전자치료 안전성 기준이 강화되지 않아야 합니다" },
      { title: "유전자편집 기술 특허 독점", detail: "CRISPR 원천기술 특허로 경쟁사 진입을 막고 라이센스 수익이 가능합니다", condition: "특허 소송에서 승리해야 하며, 차세대 편집 기술(프라임 에디팅)이 CRISPR를 대체하지 않아야 합니다" },
    ],
  },
  "LLY": {
    checklist: ["비만약(GLP-1) 처방 데이터", "분기별 매출 서프라이즈", "파이프라인 임상 결과", "경쟁사(NVO) 동향", "보험 커버리지 확대"],
    momentum: [
      { title: "비만약 시장 $100B 성장", detail: "GLP-1 비만약 시장이 2030년까지 $100B 이상으로 성장할 전망입니다", condition: "보험사 커버리지 확대 + 공급 부족 해소가 필요합니다. 노보노디스크와의 경쟁에서 점유율을 지켜야 합니다" },
      { title: "알츠하이머 신약 도나네맙", detail: "알츠하이머 치료제 시장은 연간 $10B+ 규모로, 승인 시 큰 매출원이 됩니다", condition: "임상 데이터가 경쟁약(레카네맙) 대비 우월해야 하며, 보험 급여가 확대되어야 합니다" },
    ],
  },
  "IONQ": {
    checklist: ["큐비트 수 로드맵 진척", "매출 증가율", "현금 소진율", "정부/기업 계약", "기술적 마일스톤"],
    momentum: [
      { title: "양자 우위 달성 임박", detail: "양자 컴퓨터가 기존 슈퍼컴퓨터를 넘는 순간 시장이 폭발합니다", condition: "큐비트 수 로드맵이 지켜지고, 오류율이 실용 수준으로 낮아져야 합니다. 현금이 바닥나기 전에 성과를 내야 합니다" },
    ],
  },
  "RKLB": {
    checklist: ["발사 횟수/성공률", "Neutron 로켓 개발 진척", "우주시스템 매출 비중", "수주잔고", "경쟁사(SpaceX) 동향"],
    momentum: [
      { title: "Neutron 첫 발사 예정", detail: "중형 로켓 Neutron 성공 시 발사 시장 점유율이 크게 확대됩니다", condition: "발사 일정이 지켜지고, 첫 발사가 성공해야 합니다. 실패 시 주가 30%+ 급락 위험" },
    ],
  },
  "BE": {
    checklist: ["SOFC 주문 잔고", "매출총이익률 추이", "AI 데이터센터 계약", "수소 전환 로드맵", "정부 보조금 현황"],
    momentum: [
      { title: "AI 데이터센터 분산전원 계약", detail: "데이터센터가 그리드 전력 부족으로 분산전원(연료전지)을 도입하고 있습니다", condition: "대형 데이터센터 계약이 추가되어야 하며, 전력 단가가 그리드 대비 경쟁력을 가져야 합니다" },
      { title: "흑자 전환 임박", detail: "매출 확대와 원가 개선으로 흑자 전환이 예상됩니다", condition: "매출총이익률이 25%+ 유지되고, 운영비 증가를 통제해야 합니다" },
    ],
  },
};

function getStockMeta(ticker: string) {
  const meta = STOCK_META[ticker] || STOCK_META[ticker.replace(".KS", "").replace(".KQ", "")];
  if (meta) return meta;
  return {
    checklist: ["분기 실적 발표 확인", "경쟁사 대비 밸류에이션", "산업 성장률 전망", "규제 환경 변화"],
    momentum: [
      { title: "분기 실적 발표 예정", detail: "다음 분기 실적이 시장 기대치를 충족하는지가 핵심입니다", condition: "매출 성장률과 이익률이 전분기 대비 개선되어야 합니다" },
      { title: "산업 트렌드 수혜", detail: "해당 산업의 구조적 성장이 이 종목의 실적으로 이어지고 있습니다", condition: "산업 성장률이 유지되고, 경쟁사 대비 점유율이 유지/확대되어야 합니다" },
    ],
  };
}

/* ── StockAnalysisCard ── */

function StockAnalysisCard({ pick, sectorColor }: { pick: StockPick; sectorColor: string }) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [earnings, setEarnings] = useState<any>(null);
  const [patternData, setPatternData] = useState<any>(null);
  const [prediction, setPrediction] = useState<any>(null);
  const [moveReasons, setMoveReasons] = useState<any>(null);
  const [checklistLive, setChecklistLive] = useState<any>(null);
  const [macroEvents, setMacroEvents] = useState<any>(null);
  const [tradingTargets, setTradingTargets] = useState<any>(null);
  const [showTargetReasons, setShowTargetReasons] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>("3mo");
  const [loading, setLoading] = useState(true);
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadStage, setLoadStage] = useState("초기화 중...");
  const [chartLoading, setChartLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [partialDataWarning, setPartialDataWarning] = useState(false);

  // Load ticker-dependent data in sequential phases with progress tracking.
  // Each phase completes before the next starts to avoid overwhelming the backend.
  const loadTickerData = useCallback(async (t: string) => {
    setLoadError(false);
    setPartialDataWarning(false);
    setLoadProgress(5);
    setLoadStage("차트 데이터 수집 중...");

    // Phase 1: Chart + Analysis (essential, must succeed)
    setLoadStage("기술적 분석 수행 중...");
    setLoadProgress(15);
    const [analysisRes, earningsRes] = await Promise.allSettled([
      fetchAnalysis(t).then((d) => { setAnalysis(d); setLoadProgress(25); return d; }),
      fetchEarnings(t).then((d) => { setEarnings(d); setLoadProgress(35); return d; }),
    ]);
    if (analysisRes.status === "rejected" && earningsRes.status === "rejected") {
      setPartialDataWarning(true);
    }

    // Phase 2: Pattern + Prediction + Targets (important, sequential batch)
    setLoadStage("패턴 분석 & AI 예측 중...");
    setLoadProgress(40);
    await Promise.allSettled([
      fetchPatternAnalysis(t).then((d) => { setPatternData(d); setLoadProgress(50); }),
      fetchPrediction(t).then((d) => { setPrediction(d); setLoadProgress(55); }),
      fetchTradingTargets(t).then((d) => { setTradingTargets(d); setLoadProgress(60); }),
    ]);

    // Phase 3: Move reasons + Macro (medium priority)
    setLoadStage("뉴스 & 이벤트 분석 중...");
    setLoadProgress(65);
    await Promise.allSettled([
      fetchMoveReasons(t, period).then((d) => { setMoveReasons(d); setLoadProgress(75); }),
      fetchMacroEvents().then((d) => { setMacroEvents(d); setLoadProgress(80); }),
    ]);

    // Phase 4: Checklist (slowest — fetch last, with retry)
    setLoadStage("투자 체크리스트 검증 중...");
    setLoadProgress(85);
    try {
      const cl = await fetchChecklistLive(t);
      setChecklistLive(cl);
    } catch {
      setPartialDataWarning(true);
      // Auto-retry once
      try {
        await new Promise((r) => setTimeout(r, 2000));
        const cl2 = await fetchChecklistLive(t);
        setChecklistLive(cl2);
      } catch {
        // Give up on checklist — show rest of data
      }
    }

    setLoadProgress(100);
    setLoadStage("완료!");
  }, [period]);

  // Ticker-dependent data — re-fetches when stock changes or retry
  useEffect(() => {
    setLoading(true);
    setLoadProgress(0);
    setLoadStage("데이터 준비 중...");
    setAnalysis(null);
    setEarnings(null);
    setPatternData(null);
    setPrediction(null);
    setChecklistLive(null);
    setTradingTargets(null);
    setShowTargetReasons(null);

    // Load chart and ticker data together
    const loadAll = async () => {
      setChartLoading(true);
      setLoadError(false);

      // Chart data (with retry)
      setLoadStage("주가 차트 로딩 중...");
      setLoadProgress(5);
      let chartOk = false;
      try {
        const data = await fetchChartData(pick.ticker, period);
        setChartData(data);
        chartOk = Boolean(data?.length);
      } catch {
        try {
          await new Promise((r) => setTimeout(r, 1200));
          const retried = await fetchChartData(pick.ticker, period);
          setChartData(retried);
          chartOk = Boolean(retried?.length);
        } catch {
          setLoadError(true);
        }
      }
      setLoadProgress(10);
      setChartLoading(false);

      if (!chartOk) setPartialDataWarning(true);

      // Now load all other data sequentially
      await loadTickerData(pick.ticker);

      // Only dismiss loading when done
      setLoading(false);
    };

    loadAll();
  }, [pick.ticker, period, retryCount, loadTickerData]);

  // Auto-refresh every 5 min — only refresh analysis & checklist (not chart, to avoid UI jump)
  useEffect(() => {
    const t = pick.ticker;
    const intervalId = window.setInterval(() => {
      fetchAnalysis(t).then(setAnalysis).catch(() => {});
      fetchChecklistLive(t).then(setChecklistLive).catch(() => {});
    }, 300_000);
    return () => window.clearInterval(intervalId);
  }, [pick.ticker, period]);

  const latestPrice = chartData.length > 0 ? chartData[chartData.length - 1].close : null;
  const chartVerdict = analyzeChart(analysis, chartData);
  const fundVerdict = analyzeFundamentals(earnings, patternData, checklistLive);
  const meta = getStockMeta(pick.ticker);

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

  // Unified scoring: chart 40% + fundamentals 30% + prediction 30%
  const chartScore100 = chartVerdict.score100;
  const fundScore100 = fundVerdict.score100;
  const predScore100 = prediction?.overall_score != null ? Math.round(Math.max(0, Math.min(100, (prediction.overall_score + 100) / 2))) : null;
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
    { score: chartScore100, weight: 0.3 },
    { score: fundScore100, weight: 0.25 },
    { score: checklistScore100, weight: 0.2 },
    { score: predScore100, weight: 0.25 },
  ].filter((part) => part.score != null) as { score: number; weight: number }[];
  const totalWeight = weightedParts.reduce((sum, part) => sum + part.weight, 0);
  const overallScore100 = totalWeight > 0
    ? Math.round(weightedParts.reduce((sum, part) => sum + part.score * part.weight, 0) / totalWeight)
    : 50;
  const overall = scoreToVerdict(overallScore100);
  const momentumNotes = checklistLive?.summary?.momentum_notes?.length
    ? checklistLive.summary.momentum_notes
    : null; // null = still loading, don't show stale static data
  const liveImpactNews = checklistLive?.summary?.live_impact_news?.length
    ? checklistLive.summary.live_impact_news
    : [];

  return (
    <div className="space-y-4">
      {/* ═══ OVERALL VERDICT — BIG & PROMINENT ═══ */}
      {!loading && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
          <div
            className="px-5 py-5"
            style={{ background: `linear-gradient(135deg, ${overall.color}20, ${overall.color}05)`, borderBottom: `2px solid ${overall.color}40` }}
          >
            {/* Top row: company name + price + score */}
            <div className="flex items-center gap-4 mb-4">
              <div className="flex-1 min-w-0">
                <h2 className="text-2xl font-black text-[var(--color-text-primary)] truncate">{pick.name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm font-mono text-[var(--color-text-muted)]">{pick.ticker}</span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full font-bold"
                    style={{ background: pick.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)", color: pick.flag === "US" ? "#60a5fa" : "#f87171" }}
                  >{pick.flag}</span>
                </div>
                <div className="flex items-center gap-3 mt-2">
                  {latestPrice && (
                    <span className="text-xl font-mono font-black text-[var(--color-text-primary)]">
                      {currency}{Math.round(latestPrice).toLocaleString()}
                    </span>
                  )}
                  <span className="text-sm font-bold px-3 py-1 rounded-lg" style={{ background: `${overall.color}18`, color: overall.color, border: `1px solid ${overall.color}30` }}>
                    {overall.label}
                  </span>
                  <span className="text-xs text-[var(--color-text-secondary)]">{overall.action}</span>
                </div>
              </div>
              {/* Big score circle */}
              <div className="flex flex-col items-center shrink-0">
                <div
                  className="w-18 h-18 rounded-full flex items-center justify-center border-4"
                  style={{ borderColor: overall.color, background: `${overall.color}10`, width: 72, height: 72 }}
                >
                  <span className="text-2xl font-black" style={{ color: overall.color }}>{overallScore100}</span>
                </div>
                <span className="text-[9px] text-[var(--color-text-muted)] mt-1">종합 점수</span>
              </div>
            </div>

            {/* Chart + Fundamentals score badges */}
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1 rounded-xl px-3 py-2" style={{ background: `${chartVerdict.color}10`, border: `1px solid ${chartVerdict.color}25` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--color-text-muted)]">차트 분석</span>
                  <span className="text-sm font-black" style={{ color: chartVerdict.color }}>{chartScore100}점</span>
                </div>
                <div className="mt-1 h-1.5 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${chartScore100}%`, background: chartVerdict.color }} />
                </div>
                <span className="text-[10px] font-bold mt-1 block" style={{ color: chartVerdict.color }}>{chartVerdict.label}</span>
              </div>
              <span className="text-lg font-black text-[var(--color-text-muted)]">+</span>
              <div className="flex-1 rounded-xl px-3 py-2" style={{ background: `${fundVerdict.color}10`, border: `1px solid ${fundVerdict.color}25` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--color-text-muted)]">실적/펀더멘탈</span>
                  <span className="text-sm font-black" style={{ color: fundVerdict.color }}>{fundScore100}점</span>
                </div>
                <div className="mt-1 h-1.5 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${fundScore100}%`, background: fundVerdict.color }} />
                </div>
                <span className="text-[10px] font-bold mt-1 block" style={{ color: fundVerdict.color }}>{fundVerdict.label}</span>
              </div>
              <span className="text-lg font-black text-[var(--color-text-muted)]">=</span>
              <div className="flex-1 rounded-xl px-3 py-2" style={{ background: `${overall.color}10`, border: `1px solid ${overall.color}25` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--color-text-muted)]">종합</span>
                  <span className="text-sm font-black" style={{ color: overall.color }}>{overallScore100}점</span>
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
                  <span className="text-[10px] text-[var(--color-text-muted)] animate-pulse">차트 분석 기반 매매 타점 계산 중...</span>
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
                { key: "buy", label: "매수 타점", price: tt.buy.price, pct: tt.buy.pct, reasons: tt.buy.reasons, color: "#3b82f6", pctLabel: "이하 시 분할매수" },
                { key: "sell", label: "매도 타점", price: tt.sell.price, pct: tt.sell.pct, reasons: tt.sell.reasons, color: "#22c55e", pctLabel: "이상 시 분할매도" },
                { key: "stop", label: "손절 라인", price: tt.stop.price, pct: tt.stop.pct, reasons: tt.stop.reasons, color: "#ef4444", pctLabel: "이하 시 손절" },
              ];

              return (
                <div className="space-y-3">
                  {/* Risk/Reward ratio bar */}
                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--color-bg-hover)]">
                    <span className="text-[10px] font-bold text-[var(--color-text-muted)]">손익비</span>
                    <div className="flex-1 h-2 rounded-full bg-[var(--color-bg-primary)] overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{
                        width: `${Math.min(100, rr / 5 * 100)}%`,
                        background: rr >= 2 ? "#22c55e" : rr >= 1 ? "#eab308" : "#ef4444"
                      }} />
                    </div>
                    <span className={`text-xs font-black ${rr >= 2 ? "text-[#22c55e]" : rr >= 1 ? "text-[#eab308]" : "text-[#ef4444]"}`}>
                      1:{rr.toFixed(1)} {rr >= 2.5 ? "매우 유리" : rr >= 1.5 ? "유리" : rr >= 1 ? "보통" : "불리"}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    {cards.map(card => (
                      <div key={card.key}
                        className="rounded-xl p-3 cursor-pointer transition-all hover:scale-[1.02]"
                        style={{ background: `${card.color}11`, border: `1px solid ${card.color}40` }}
                        onClick={() => setShowTargetReasons(showTargetReasons === card.key ? null : card.key)}
                      >
                        <p className="text-[10px] font-bold mb-1" style={{ color: card.color }}>{card.label}</p>
                        <p className="text-lg font-black" style={{ color: card.color }}>{fmt(card.price)}</p>
                        <p className="text-[10px] mt-0.5" style={{ color: `${card.color}99` }}>
                          {card.pct >= 0 ? "+" : ""}{card.pct.toFixed(1)}% {card.pctLabel}
                        </p>
                        <p className="text-[9px] mt-1 underline" style={{ color: `${card.color}80` }}>
                          {showTargetReasons === card.key ? "닫기 ▲" : "근거 보기 ▼"}
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
                      <p className="text-[10px] font-bold text-[var(--color-text-muted)] mb-1.5">차트 지표 분석</p>
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

      {loadError && !loading && chartData.length === 0 && (
        <div className="bg-[var(--color-bg-card)] border border-[rgba(239,68,68,0.3)] rounded-2xl p-6 text-center">
          <p className="text-sm text-[var(--color-text-primary)] font-semibold">데이터를 불러오지 못했습니다</p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">서버가 준비 중이거나 네트워크 문제일 수 있습니다</p>
          <button
            onClick={() => setRetryCount((c) => c + 1)}
            className="mt-3 px-5 py-2 rounded-xl text-sm font-bold text-white transition-all"
            style={{ background: sectorColor }}
          >
            다시 시도
          </button>
        </div>
      )}

      {!loadError && partialDataWarning && (
        <div className="bg-[var(--color-bg-card)] border border-[rgba(234,179,8,0.25)] rounded-2xl px-4 py-3">
          <p className="text-xs text-[var(--color-text-secondary)]">
            일부 실시간 소스 응답이 지연되어 최근 정상 캐시 데이터를 함께 표시하고 있습니다.
          </p>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${sectorColor}15`, border: `2px solid ${sectorColor}30` }}>
            <Activity size={24} style={{ color: sectorColor }} className="animate-pulse" />
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[var(--color-text-primary)]">AI 분석 중... {loadProgress}%</p>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">{pick.name} ({pick.ticker})</p>
            <p className="text-xs mt-2" style={{ color: sectorColor }}>{loadStage}</p>
          </div>
          <div className="w-64 h-2 rounded-full bg-[var(--color-bg-hover)] overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500 ease-out" style={{ background: `linear-gradient(90deg, ${sectorColor}, ${sectorColor}cc)`, width: `${Math.max(5, loadProgress)}%` }} />
          </div>
          <p className="text-[10px] text-[var(--color-text-muted)]">
            {loadProgress < 30 ? "서버에서 데이터를 가져오고 있습니다..." :
             loadProgress < 60 ? "기술적 지표를 분석하고 있습니다..." :
             loadProgress < 85 ? "뉴스와 이벤트를 수집하고 있습니다..." :
             "체크리스트 최종 검증 중..."}
          </p>
        </div>
      ) : (
        <>
          {/* ═══ CHART — dots on big moves, hover for reason ═══ */}
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
            <div className="px-5 pt-3 pb-3">
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
              {chartLoading && <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--color-bg-card)]/60 rounded-lg"><span className="text-xs text-[var(--color-text-muted)] animate-pulse">차트 로딩중...</span></div>}
              <ResponsiveContainer width="100%" height={260}>
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="date" tick={{ fill: "var(--color-text-muted)", fontSize: 9 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis domain={["auto", "auto"]} tick={{ fill: "var(--color-text-muted)", fontSize: 9 }} />
                  <Tooltip
                    content={({ active, payload }: any) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0]?.payload;
                      if (!d) return null;
                      const moveInfo = findMoveReason(d.date);
                      const bigMove = bigMoves.find((m) => m.date === d.date);
                      return (
                        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-3.5 shadow-2xl max-w-[340px]" style={{ backdropFilter: "blur(8px)" }}>
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
                                {moveInfo?.issue_summary || moveInfo?.reason || (bigMove.pctChange > 0 ? "모멘텀 상승 / 수급 개선" : "차익실현 / 시장 조정")}
                              </p>
                              {moveInfo?.issue_category && (
                                <p className="text-[10px] text-[var(--color-text-muted)] mb-1">
                                  핵심 이슈: {moveInfo.issue_category}
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
                  {/* Event dots on big moves */}
                  {bigMoves.map((m, i) => {
                    const dp = chartData.find((d) => d.date === m.date);
                    if (!dp) return null;
                    return (
                      <ReferenceDot
                        key={`move-${i}`}
                        x={m.date}
                        y={dp.close}
                        r={Math.abs(m.pctChange) > 5 ? 8 : 6}
                        fill={m.pctChange > 0 ? "#22c55e" : "#ef4444"}
                        stroke="#fff"
                        strokeWidth={2}
                        style={{ cursor: "pointer", filter: `drop-shadow(0 0 6px ${m.pctChange > 0 ? "rgba(34,197,94,0.7)" : "rgba(239,68,68,0.7)"})` }}
                        label={{ value: `${m.pctChange > 0 ? "+" : ""}${m.pctChange.toFixed(0)}%`, position: "top", fontSize: 9, fill: m.pctChange > 0 ? "#22c55e" : "#ef4444", fontWeight: 700 }}
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
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${sectorColor}18`, border: `1px solid ${sectorColor}25` }}>
                <Zap size={16} style={{ color: sectorColor }} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">현재 주가 기대감</h3>
                <p className="text-[10px] text-[var(--color-text-muted)]">최신 뉴스 기반 실시간 분석 — 지금 주가를 밀고 있는 기대와 깨지는 조건</p>
              </div>
            </div>
            {!momentumNotes ? (
              <div className="px-4 py-6 text-center">
                <div className="w-8 h-8 rounded-full mx-auto mb-2 flex items-center justify-center" style={{ background: `${sectorColor}15` }}>
                  <Zap size={14} style={{ color: sectorColor }} className="animate-pulse" />
                </div>
                <p className="text-xs text-[var(--color-text-muted)] animate-pulse">최신 뉴스를 분석하여 기대감을 생성 중...</p>
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
                              <span className="font-bold text-[var(--color-text-secondary)]">깨지는 조건:</span> {m.expected_condition}
                            </p>
                          </div>
                        )}
                        {m.window && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">유효 구간: {m.window}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ═══ 실시간 뉴스 — 호재/악재 분류 ═══ */}
          {liveImpactNews.length > 0 && (
            <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-[rgba(99,102,241,0.1)] border border-[rgba(99,102,241,0.2)]">
                  <Newspaper size={16} className="text-[#6366f1]" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">실시간 뉴스 분석</h3>
                  <p className="text-[10px] text-[var(--color-text-muted)]">최신 뉴스를 호재/악재로 분류 — 주가 영향 분석</p>
                </div>
              </div>
              {(() => {
                const positiveNews = liveImpactNews.filter((a: any) =>
                  a.impact_direction === "positive" || (!(a.impact_direction === "negative") && ((a.explanation || "").includes("상승") || (a.explanation || "").includes("호재") || (a.explanation || "").includes("긍정") || (a.explanation || "").includes("수혜")))
                );
                const negativeNews = liveImpactNews.filter((a: any) =>
                  a.impact_direction === "negative" || (!(a.impact_direction === "positive") && ((a.explanation || "").includes("하락") || (a.explanation || "").includes("악재") || (a.explanation || "").includes("위험") || (a.explanation || "").includes("우려")))
                );
                const neutralNews = liveImpactNews.filter((a: any) => !positiveNews.includes(a) && !negativeNews.includes(a));

                return (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-[var(--color-bg-hover)]">
                      <span className="text-xs font-bold text-[#22c55e]">호재 {positiveNews.length}</span>
                      <div className="flex-1 h-2 rounded-full bg-[var(--color-bg-primary)] overflow-hidden flex">
                        {positiveNews.length > 0 && <div className="h-full bg-[#22c55e]" style={{ width: `${positiveNews.length / liveImpactNews.length * 100}%` }} />}
                        {neutralNews.length > 0 && <div className="h-full bg-[#eab308]" style={{ width: `${neutralNews.length / liveImpactNews.length * 100}%` }} />}
                        {negativeNews.length > 0 && <div className="h-full bg-[#ef4444]" style={{ width: `${negativeNews.length / liveImpactNews.length * 100}%` }} />}
                      </div>
                      <span className="text-xs font-bold text-[#ef4444]">악재 {negativeNews.length}</span>
                    </div>

                    {positiveNews.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-[#22c55e] uppercase tracking-widest mb-2 flex items-center gap-1"><TrendingUp size={12} /> 호재</p>
                        <div className="space-y-1.5">
                          {positiveNews.map((a: any, i: number) => (
                            <div key={`pos-${i}`} className="px-3 py-2.5 rounded-xl" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.15)" }}>
                              <p className="text-sm font-semibold text-[var(--color-text-primary)]">{a.title}</p>
                              {a.explanation && <p className="text-xs text-[var(--color-text-secondary)] mt-1">{a.explanation}</p>}
                              {a.source && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{a.source}{a.published_at ? ` · ${a.published_at}` : ""}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {negativeNews.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-[#ef4444] uppercase tracking-widest mb-2 flex items-center gap-1"><TrendingDown size={12} /> 악재</p>
                        <div className="space-y-1.5">
                          {negativeNews.map((a: any, i: number) => (
                            <div key={`neg-${i}`} className="px-3 py-2.5 rounded-xl" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                              <p className="text-sm font-semibold text-[var(--color-text-primary)]">{a.title}</p>
                              {a.explanation && <p className="text-xs text-[var(--color-text-secondary)] mt-1">{a.explanation}</p>}
                              {a.source && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{a.source}{a.published_at ? ` · ${a.published_at}` : ""}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {neutralNews.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-[#eab308] uppercase tracking-widest mb-2 flex items-center gap-1"><MinusCircle size={12} /> 중립</p>
                        <div className="space-y-1.5">
                          {neutralNews.map((a: any, i: number) => (
                            <div key={`neu-${i}`} className="px-3 py-2.5 rounded-xl" style={{ background: "rgba(234,179,8,0.04)", border: "1px solid rgba(234,179,8,0.12)" }}>
                              <p className="text-sm font-semibold text-[var(--color-text-primary)]">{a.title}</p>
                              {a.explanation && <p className="text-xs text-[var(--color-text-secondary)] mt-1">{a.explanation}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          )}

          {/* ═══ MACRO / GEOPOLITICAL EVENTS ═══ */}
          {macroEvents?.events?.length > 0 && (
            <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)]">
                  <Globe size={16} className="text-[#ef4444]" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">글로벌 매크로 & 지정학 이슈</h3>
                  <p className="text-[10px] text-[var(--color-text-muted)]">한국 증시에 영향을 미치는 글로벌 이벤트</p>
                </div>
                {macroEvents.summary && (
                  <div className="ml-auto flex items-center gap-2">
                    <span className={`text-xs font-bold px-2 py-1 rounded-lg ${
                      macroEvents.summary.market_sentiment.includes("부정") ? "bg-[rgba(239,68,68,0.1)] text-[#ef4444]"
                      : macroEvents.summary.market_sentiment.includes("긍정") ? "bg-[rgba(34,197,94,0.1)] text-[#22c55e]"
                      : "bg-[rgba(234,179,8,0.1)] text-[#eab308]"
                    }`}>
                      시장 분위기: {macroEvents.summary.market_sentiment}
                    </span>
                  </div>
                )}
              </div>
              {macroEvents.summary && (
                <div className="mb-4 px-3 py-2.5 rounded-xl bg-[var(--color-bg-hover)]">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-[#22c55e]">호재 {macroEvents.summary.positive}</span>
                    <div className="flex-1 h-2 rounded-full bg-[var(--color-bg-primary)] overflow-hidden flex">
                      {macroEvents.summary.positive > 0 && <div className="h-full bg-[#22c55e]" style={{ width: `${macroEvents.summary.positive / macroEvents.summary.total * 100}%` }} />}
                      {macroEvents.summary.neutral > 0 && <div className="h-full bg-[#eab308]" style={{ width: `${macroEvents.summary.neutral / macroEvents.summary.total * 100}%` }} />}
                      {macroEvents.summary.negative > 0 && <div className="h-full bg-[#ef4444]" style={{ width: `${macroEvents.summary.negative / macroEvents.summary.total * 100}%` }} />}
                    </div>
                    <span className="text-xs font-bold text-[#ef4444]">악재 {macroEvents.summary.negative}</span>
                  </div>
                  <p className="text-[10px] text-[var(--color-text-muted)] mt-1.5">{macroEvents.summary.sentiment_detail}</p>
                </div>
              )}
              <div className="space-y-3">
                {Object.entries(macroEvents.by_category || {}).map(([category, events]: [string, any]) => (
                  <div key={category}>
                    <p className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-widest mb-2 flex items-center gap-1">
                      {category === "지정학" ? "🌍" : category === "유가/원자재" ? "🛢️" : category === "금리/통화" ? "💵" : category === "관세/무역" ? "📦" : category === "경기/물가" ? "📊" : "📈"} {category}
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
                            }`}>{e.impact_direction === "negative" ? "악재" : e.impact_direction === "positive" ? "호재" : "중립"}</span>
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
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-[rgba(99,102,241,0.1)] border border-[rgba(99,102,241,0.2)]">
                <Shield size={16} className="text-[#6366f1]" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">투자 체크리스트 (실시간 모니터링)</h3>
                <p className="text-[10px] text-[var(--color-text-muted)]">주가와의 상관관계 분석 기반 — 중요도순 정렬</p>
              </div>
              {checklistLive === null && <span className="text-[10px] text-[var(--color-text-muted)] ml-auto animate-pulse">데이터 로딩 중...</span>}
              {checklistLive?.checklist && (() => {
                const total = checklistLive.checklist.length;
                const passed = checklistLive.checklist.filter((c: any) => c.status === "positive").length;
                const ratio = total > 0 ? passed / total : 0;
                const safetyColor = ratio >= 0.7 ? "#22c55e" : ratio >= 0.4 ? "#eab308" : "#ef4444";
                const safetyLabel = ratio >= 0.7 ? "안전" : ratio >= 0.4 ? "주의" : "위험";
                return (
                  <div className="flex items-center gap-2 ml-auto">
                    <div className="flex gap-0.5">
                      {checklistLive.checklist.map((_: any, ci: number) => (
                        <div key={ci} className="w-3 h-6 rounded-sm" style={{
                          background: checklistLive.checklist[ci].status === "positive" ? "#22c55e" : checklistLive.checklist[ci].status === "negative" ? "#ef4444" : "#eab30850"
                        }} />
                      ))}
                    </div>
                    <span className="text-lg font-black" style={{ color: safetyColor }}>{passed}/{total}</span>
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: safetyColor + "18", color: safetyColor, border: `1px solid ${safetyColor}30` }}>
                      {safetyLabel}
                    </span>
                  </div>
                );
              })()}
            </div>
            <div className="space-y-4">
              {checklistLive?.checklist?.map((item: any, i: number) => {
                const statusColor = item.status === "positive" ? "#22c55e" : item.status === "negative" ? "#ef4444" : "#eab308";
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
                    <div className="px-4 py-3 flex items-center justify-between" style={{ background: `${statusColor}12` }}>
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${statusColor}20` }}>
                          {item.status === "positive" ? <CheckCircle2 size={18} color="#22c55e" /> : item.status === "negative" ? <XCircle size={18} color="#ef4444" /> : <MinusCircle size={18} color="#eab308" />}
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <p className="text-sm font-bold text-[var(--color-text-primary)]">{item.name}</p>
                            {item.importance >= 60 && <span className="text-[9px] font-black px-1.5 py-0.5 rounded-full bg-[rgba(239,68,68,0.2)] text-[#ef4444]">핵심</span>}
                          </div>
                          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{item.detail || "—"}</p>
                          {item.why_it_matters && <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">{item.why_it_matters}</p>}
                          {item.expected_condition && <p className="text-[11px] text-[var(--color-text-muted)] mt-1">기대 조건: {item.expected_condition}</p>}
                          {item.window && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">체크 구간: {item.window}</p>}
                        </div>
                      </div>
                      {/* Big clear status — the ONE thing you need to see */}
                      <div className="shrink-0 text-right px-3 py-1.5 rounded-lg" style={{
                        background: item.status === "positive" ? "rgba(59,130,246,0.15)" : item.status === "negative" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                        border: `1.5px solid ${item.status === "positive" ? "rgba(59,130,246,0.3)" : item.status === "negative" ? "rgba(239,68,68,0.3)" : "rgba(245,158,11,0.3)"}`
                      }}>
                        <p className="text-lg font-black" style={{ color: item.status === "positive" ? "#3b82f6" : item.status === "negative" ? "#ef4444" : "#d97706" }}>
                          {item.status === "positive" ? "✓ 안전" : item.status === "negative" ? "⚠ 위험" : "◆ 주의"}
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
                          const monthLabel = d.date?.slice(5, 7) + "월";
                          const val = Math.round(d.close * 100) / 100;
                          rawPts.push(val);
                          chartPts.push({ label: monthLabel, value: val, expected: null });
                        }
                        const lastD = mergedData[mergedData.length - 1];
                        const lastLabel = lastD.date?.slice(5, 7) + "월";
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
                              label: `${futureMonth}월 (예상)`,
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
                          return { label: isPrelim ? `${y.slice(2)}'Q${qNum} (잠정)` : `${y.slice(2)}'Q${qNum}`, value: q.value, expected: null };
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
                              label: `${String(fy).slice(2)}'Q${fqNum} (예상)`,
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
                      const periodLabel = hasTrend ? `${months}개월` : `${actualPts.length}분기`;
                      let summaryParts: string[] = [];
                      summaryParts.push(`${periodLabel}간 ${totalChg >= 0 ? "상승" : "하락"} (${totalChg >= 0 ? "+" : ""}${totalChg.toFixed(1)}${hasTrend ? "%" : "%p"})`);
                      if (belowExpected && lastExpected != null) {
                        summaryParts.push(`현재 주가 유지하려면 ${unit}${lastExpected} 이상 필요 → 실제 ${unit}${currentVal} (하회)`);
                      } else if (lastExpected != null && currentVal != null) {
                        summaryParts.push(`예상 ${unit}${lastExpected} 대비 실제 ${unit}${currentVal} — 정상 범위`);
                      }
                      if (futureExpected != null) {
                        summaryParts.push(`향후 예상: ${unit}${futureExpected}`);
                      }
                      if (dangerLine != null && currentVal != null) {
                        if (isInDanger) {
                          summaryParts.push(`위험선(${unit}${dangerLine}) ${dangerDir === "below" ? "이탈" : "초과"} → 주가 하락 가능성`);
                        }
                      }

                      return (
                        <div className="px-4 pb-4 pt-2">
                          {/* Alert banners */}
                          {inDanger && (
                            <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg bg-[rgba(239,68,68,0.12)] border border-[rgba(239,68,68,0.3)]">
                              <AlertTriangle size={16} className="text-[#ef4444] shrink-0" />
                              <span className="text-xs font-bold text-[#ef4444]">⚠ 위험 구간 — 이 밑으로 내려가면 주가 하락 신호</span>
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
                              <ComposedChart data={chartPts} margin={{ top: 28, right: 20, bottom: 6, left: 20 }}>
                                <defs>
                                  <linearGradient id={`cg-${i}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={isInDanger ? "#ef4444" : "#1d4ed8"} stopOpacity={0.12} />
                                    <stop offset="100%" stopColor={isInDanger ? "#ef4444" : "#1d4ed8"} stopOpacity={0.01} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid horizontal vertical={false} stroke="#f1f5f9" />
                                <XAxis
                                  dataKey="label"
                                  tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
                                  axisLine={{ stroke: "#cbd5e1" }}
                                  tickLine={false}
                                />
                                <YAxis
                                  domain={[yMin, yMax]}
                                  tick={{ fill: "#94a3b8", fontSize: 9 }}
                                  tickFormatter={(v: number) => `${unit}${v >= 1000 ? (v/1000).toFixed(0) + "k" : Number(v.toFixed(1))}`}
                                  axisLine={false}
                                  tickLine={false}
                                  width={48}
                                />
                                {/* Danger zone — red fill */}
                                {dangerLine != null && (
                                  dangerDir === "below"
                                    ? <ReferenceArea y1={yMin} y2={dangerLine} fill="#ef4444" fillOpacity={0.12} />
                                    : <ReferenceArea y1={dangerLine} y2={yMax} fill="#ef4444" fillOpacity={0.12} />
                                )}
                                {/* Danger line */}
                                {dangerLine != null && (
                                  <ReferenceLine y={dangerLine} stroke="#ef4444" strokeWidth={2} strokeDasharray="8 4"
                                    label={{ value: `위험선 ${unit}${dangerLine}`, position: dangerDir === "below" ? "insideBottomLeft" : "insideTopLeft", fontSize: 9, fill: "#ef4444", fontWeight: 800 }} />
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
                                    const isPrelim = (payload.label || "").includes("잠정");
                                    const dotColor = isPrelim ? "#f59e0b" : isInDanger ? "#ef4444" : "#1e3a5f";
                                    return <circle key={`d-${di}`} cx={cx} cy={cy} r={isLast ? 7 : 4} fill={isPrelim ? "#fef3c7" : "#fff"} stroke={dotColor} strokeWidth={isLast ? 3 : 2} />;
                                  }}
                                  label={({ x, y, value, index }: any) => {
                                    if (value == null) return null;
                                    const isLast = index === actualPts.length - 1;
                                    const isPrelim = (chartPts[index]?.label || "").includes("잠정");
                                    const color = isPrelim ? "#d97706" : isLast ? (isInDanger ? "#ef4444" : "#1d4ed8") : "#334155";
                                    return (
                                      <text key={`l-${index}`} x={x} y={y - 12} textAnchor="middle" fill={color} fontSize={isLast ? 13 : 10} fontWeight={isLast ? 900 : 700}>
                                        {isPrelim ? "⚡" : ""}{typeof value === "number" ? (value >= 1000 ? `${(value/1000).toFixed(1)}k` : value.toFixed(value < 10 ? 2 : 1)) : value}
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
                                    return (
                                      <text key={`el-${index}`} x={x} y={y - 10} textAnchor="middle" fill="#3b82f6" fontSize={10} fontWeight={700}>
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
                            <div className="px-4 py-3 flex items-center justify-between" style={{
                              background: isInDanger ? "rgba(239,68,68,0.1)" : belowExpected ? "rgba(245,158,11,0.08)" : "rgba(59,130,246,0.06)"
                            }}>
                              <div>
                                <p className="text-base font-black" style={{ color: isInDanger ? "#ef4444" : belowExpected ? "#d97706" : "#3b82f6" }}>
                                  {isInDanger ? "⚠ 위험 — 주가 하락 가능성" : belowExpected ? "◆ 주의 — 주가 대비 지표 부족" : "✓ 안전 — 주가 상승 여력 있음"}
                                </p>
                                <p className="text-xs mt-0.5 text-[var(--color-text-muted)]">
                                  {lastExpected != null && currentVal != null
                                    ? belowExpected
                                      ? `현재 주가 유지하려면 ${unit}${lastExpected.toLocaleString()} 필요 → 실제 ${unit}${currentVal.toLocaleString()} (부족)`
                                      : `${unit}${lastExpected.toLocaleString()} 이상이면 주가 상승 가능 → 실제 ${unit}${currentVal.toLocaleString()} (충족)`
                                    : `현재 ${unit}${currentVal?.toLocaleString()}`}
                                  {futureExpected != null ? ` · 향후 예상 ${unit}${futureExpected.toLocaleString()}` : ""}
                                </p>
                              </div>
                              <span className="text-xl font-black font-mono" style={{ color: isInDanger ? "#ef4444" : belowExpected ? "#d97706" : "#1e293b" }}>
                                {unit}{currentVal?.toLocaleString()}
                              </span>
                            </div>
                            <div className="px-4 py-2 flex items-center gap-3" style={{ background: "rgba(0,0,0,0.02)" }}>
                              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-[#1e3a5f] inline-block rounded" /><span className="text-[10px] text-[var(--color-text-muted)]">실제</span></span>
                              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-[#3b82f6] inline-block rounded" style={{ borderTop: "2px dashed #3b82f6" }} /><span className="text-[10px] text-[#3b82f6]">예상 추세</span></span>
                              <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-sm bg-[rgba(239,68,68,0.25)] inline-block" /><span className="text-[10px] text-[#ef4444]">위험 구간</span></span>
                              <p className="text-[10px] text-[var(--color-text-muted)] ml-auto">{summaryParts[0]}</p>
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
                    <MinusCircle size={16} className="text-[var(--color-text-muted)] animate-pulse" />
                    <span className="text-sm text-[var(--color-text-secondary)]">{item}</span>
                  </div>
                  <div className="mt-3 h-20 bg-[var(--color-bg-hover)] rounded animate-pulse" />
                </div>
              ))}
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

const COMMODITY_SYMBOLS: Record<string, { symbol: string; name: string }[]> = {
  "ai-semi": [
    { symbol: "HG=F", name: "구리 (Copper)" },
    { symbol: "GC=F", name: "금 (Gold)" },
    { symbol: "SOXX", name: "반도체 지수 (SOX)" },
  ],
  "robotics": [
    { symbol: "HG=F", name: "구리 (Copper)" },
    { symbol: "ALI=F", name: "알루미늄" },
  ],
  "smr-nuclear": [
    { symbol: "URA", name: "우라늄 (URA ETF)" },
    { symbol: "NG=F", name: "천연가스" },
  ],
  "cybersec": [
    { symbol: "BUG", name: "사이버보안 (BUG ETF)" },
  ],
  "space": [
    { symbol: "UFO", name: "우주산업 (UFO ETF)" },
    { symbol: "ITA", name: "항공방산 (ITA ETF)" },
  ],
  "biotech": [
    { symbol: "XBI", name: "바이오텍 (XBI ETF)" },
    { symbol: "IBB", name: "바이오 (IBB ETF)" },
  ],
  "quantum": [
    { symbol: "QTUM", name: "양자컴퓨팅 (QTUM ETF)" },
  ],
  "hydrogen": [
    { symbol: "ICLN", name: "클린에너지 (ICLN ETF)" },
    { symbol: "PL=F", name: "백금 (Platinum)" },
  ],
};

function RiskSection({ sector }: { sector: SectorDef }) {
  const severityConfig = {
    high: { label: "높음", color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.18)" },
    medium: { label: "보통", color: "#eab308", bg: "rgba(234,179,8,0.08)", border: "rgba(234,179,8,0.18)" },
    low: { label: "낮음", color: "#22c55e", bg: "rgba(34,197,94,0.08)", border: "rgba(34,197,94,0.18)" },
  };

  const commodities = COMMODITY_SYMBOLS[sector.id] || [];

  return (
    <div className="space-y-6">
      {/* Commodity / Indicator Charts */}
      {commodities.length > 0 && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={16} style={{ color: sector.color }} />
            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">추종 지표 가격 차트 (6개월)</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {commodities.map((c) => (
              <CommodityChart key={c.symbol} symbol={c.symbol} name={c.name} sectorColor={sector.color} />
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
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={16} style={{ color: "#ef4444" }} />
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">섹터 리스크</h3>
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
    <div className="space-y-5 overflow-y-auto h-full pb-8 pr-1">
      {/* Sector description */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: `linear-gradient(135deg, ${sector.color}30, ${sector.color}10)`, border: `1.5px solid ${sector.color}50` }}
          >
            <sector.icon size={24} strokeWidth={1.5} style={{ color: sector.color }} />
          </div>
          <div>
            <h2 className="text-lg font-bold" style={{ color: sector.color }}>{sector.name}</h2>
            <p className="text-xs text-[var(--color-text-muted)]">Top {sector.picks.length}개 종목 · 왼쪽에서 종목 선택</p>
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

      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <Shield size={16} style={{ color: sector.color }} />
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">섹터 체크리스트 (실시간)</h3>
          {sectorPulse?.summary?.score != null && (
            <span
              className="ml-auto text-xs font-bold px-2.5 py-1 rounded-full"
              style={{
                background: sectorPulse.summary.score >= 60 ? "rgba(34,197,94,0.14)" : sectorPulse.summary.score <= 40 ? "rgba(239,68,68,0.14)" : "rgba(234,179,8,0.14)",
                color: sectorPulse.summary.score >= 60 ? "#22c55e" : sectorPulse.summary.score <= 40 ? "#ef4444" : "#eab308",
              }}
            >
              섹터 점수 {sectorPulse.summary.score}점
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
                      <p className="text-[11px] text-[var(--color-text-muted)] mt-1">현재: {item.detail}</p>
                      <p className="text-[11px] text-[var(--color-text-muted)] mt-1">필요 조건: {item.expected_condition}</p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-1">체크 구간: {item.window}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-lg font-black" style={{ color: tone }}>
                        {item.status === "positive" ? "긍정" : item.status === "negative" ? "경고" : "중립"}
                      </p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{item.symbol}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-[var(--color-text-muted)]">섹터 체크리스트를 불러오지 못했습니다.</p>
        )}
      </div>

      {/* News / Hot issues */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <Newspaper size={16} style={{ color: sector.color }} />
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">최신 뉴스 & 모멘텀</h3>
        </div>
        {newsLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-[var(--color-bg-hover)] rounded-lg animate-pulse" />
            ))}
          </div>
        ) : news.length === 0 ? (
          <p className="text-xs text-[var(--color-text-muted)]">뉴스를 찾을 수 없습니다.</p>
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
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedPick, setSelectedPick] = useState<StockPick | null>(null);

  const sector = SECTORS.find((s) => s.id === id);
  const isDynamic = searchParams.get("dynamic") === "1";
  const stockParam = searchParams.get("stock");

  // Auto-select stock from URL query param (?stock=NVDA)
  useEffect(() => {
    if (stockParam && sector) {
      const match = sector.picks.find((pk) => pk.ticker === stockParam || pk.ticker === decodeURIComponent(stockParam));
      if (match) {
        setSelectedPick(match);
        return;
      }
      const dynamicName = searchParams.get("name") || stockParam;
      const dynamicFlag = searchParams.get("flag") === "KR" ? "KR" : "US";
      setSelectedPick({
        ticker: stockParam,
        name: dynamicName,
        flag: dynamicFlag,
        desc: "AI 실시간 종합 분석",
      });
    }
  }, [sector, stockParam, searchParams]);

  if (!sector) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <p className="text-lg text-[var(--color-text-secondary)]">섹터를 찾을 수 없습니다.</p>
        <Link to="/" className="text-sm text-[var(--color-accent-blue)] hover:underline">마인드맵으로 돌아가기</Link>
      </div>
    );
  }

  // Dynamic stock: full-screen analysis without sector sidebar
  if (isDynamic && selectedPick) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="max-w-4xl mx-auto p-5">
          {/* Back button */}
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-white transition-colors mb-4"
          >
            <ArrowLeft size={16} /> 마인드맵으로 돌아가기
          </button>
          <StockAnalysisCard pick={selectedPick} sectorColor="#3b82f6" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* ─── Left Sidebar: Top 5 List ─── */}
      <div className="w-64 shrink-0 border-r border-[var(--color-border)] glass-strong flex flex-col overflow-hidden">
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
          className={`mx-3 mt-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
            selectedPick === null
              ? "text-white"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]"
          }`}
          style={selectedPick === null ? { background: sector.color, boxShadow: `0 4px 12px ${sector.color}30` } : {}}
        >
          섹터 개요 & 뉴스
        </button>

        {/* Divider */}
        <div className="mx-3 mt-3 mb-2">
          <p className="text-[9px] font-semibold text-[var(--color-text-muted)] uppercase tracking-widest">
            Top 5 종목
          </p>
        </div>

        {selectedPick && !sector.picks.some((pick) => pick.ticker === selectedPick.ticker) && (
          <div className="mx-3 mb-3 rounded-xl px-3 py-3 border border-[rgba(59,130,246,0.2)] bg-[rgba(59,130,246,0.08)]">
            <p className="text-[10px] font-semibold text-[var(--color-accent-blue)]">실시간 검색 종목</p>
            <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-1">{selectedPick.name}</p>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{selectedPick.ticker}</p>
          </div>
        )}

        {/* Stock list */}
        <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1">
          {sector.picks.map((pick, i) => {
            const isActive = selectedPick?.ticker === pick.ticker;
            return (
              <button
                key={pick.ticker}
                onClick={() => setSelectedPick(pick)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all duration-200 ${
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
      <div className="flex-1 overflow-y-auto p-5">
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
