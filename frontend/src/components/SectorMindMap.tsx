import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Factory, Search, X, Trophy, TrendingUp, TrendingDown, ChevronDown, ChevronUp } from "lucide-react";
import { useLanguage } from "@/i18n";
import { SECTORS, normalizeWeights } from "@/data/sectors";
import type { SectorDef } from "@/data/sectors";
import { searchStocks, fetchChartData, fetchAnalysis, fetchChecklistLive, fetchEarnings, fetchNews, fetchTopRanked } from "@/api/client";

/* ───────────────────────── HELPERS ───────────────────────── */

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

const STOCK_EVAL_CRITERIA: Record<string, string[]> = {
  "NVDA": ["AI CAPEX 지속 여부", "데이터센터 매출 성장률", "HBM 공급 타이트 유지", "영업이익률 방어"],
  "TSM": ["파운드리 가동률", "주요 고객 수요", "매출 성장 추세", "고마진 유지"],
  "AVGO": ["AI 네트워킹 수요", "커스텀칩 기대", "VMware 시너지", "영업이익률 확장"],
  "000660.KS": ["DRAM 업황 선행 신호", "HBM 믹스 확대", "영업이익률 피크아웃 여부", "환율 수혜"],
  "005930.KS": ["메모리 업황 회복", "HBM/파운드리 개선", "반도체 이익률", "밸류 부담"],
  "TSLA": ["자동차 마진 회복", "인도량과 판가", "Optimus/FSD 기대", "배터리 원가 부담"],
  "ISRG": ["수술 건수 성장", "설치 대수 확대", "이익률 유지", "고객 락인 강화"],
  "CEG": ["전력 수요 증가", "원전 장기계약", "유틸리티 흐름", "정책 리스크"],
  "CCJ": ["우라늄 가격 추세", "공급 부족 기대", "장기 계약 가격", "이익률 확장"],
  "CRWD": ["ARR 성장 유지", "플랫폼 확장", "대형 계약 증가", "운영 리스크 재발 여부"],
  "PANW": ["플랫폼 통합 확장", "보안 지출 유지", "성장률 방어", "수익성 유지"],
  "FTNT": ["방화벽/OT 수요", "성장 재가속", "고이익률 유지", "보안 섹터 심리"],
  "ZS": ["제로트러스트 확산", "고성장 유지", "흑자전환", "멀티플 방어"],
  "S": ["초고성장 유지", "적자폭 축소", "보안 섹터 심리", "자금조달 우려"],
  "RKLB": ["수주/발사 모멘텀", "Neutron 일정", "우주 테마 심리", "정부 예산 기대"],
  "LMT": ["방산/우주 수주", "예산 안정성", "현금흐름 방어", "우주 옵션 가치"],
  "BA": ["턴어라운드 신뢰 회복", "품질/규제 이슈", "생산 정상화", "우주 사업 기대"],
  "CRSP": ["임상/승인 일정", "현금 런웨이", "바이오 위험선호", "상업화 초기 매출"],
  "LLY": ["GLP-1 처방 모멘텀", "공급 확장", "경쟁사 점유율", "이익률 유지"],
  "ILMN": ["시퀀싱 수요 회복", "장비 CAPEX 흐름", "이익률 방어", "바이오 심리"],
  "207940.KS": ["CDMO 수주잔고", "증설 효과", "고마진 유지", "환율 수혜"],
  "068270.KS": ["미국 판매 확대", "가격 경쟁 압박", "이익률 방어", "환율 효과"],
  "IONQ": ["기술 로드맵 진척", "현금 소진 속도", "양자 섹터 심리", "수주/매출 성장"],
  "GOOG": ["본업 현금창출", "양자 옵션 가치", "클라우드 성장", "빅테크 위험선호"],
  "IBM": ["기업용 양자 신뢰", "본업 성장 바닥", "현금흐름 유지", "배당 매력"],
  "RGTI": ["기술 검증 기대", "자금조달 압박", "양자 심리", "매출 성장 유지"],
  "MSFT": ["Azure/AI 성장", "대형 CAPEX 유지", "고이익률 방어", "양자 옵션"],
  "BE": ["데이터센터 전력 수요", "매출 성장 전환", "흑자전환", "클린에너지 심리"],
  "PLUG": ["정책/보조금 기대", "적자폭 축소", "클린에너지 심리", "자금조달 리스크"],
  "ENPH": ["태양광 수요 회복", "금리 부담", "고마진 유지", "설치 경기 회복"],
  "005380.KS": ["친환경차 믹스", "자동차 섹터 심리", "이익률 유지", "환율 효과"],
  "336260.KS": ["수소발전 정책", "프로젝트 수주", "흑자전환", "클린에너지 심리"],
};

function getEvalCriteria(ticker: string, sectorName: string) {
  return (
    STOCK_EVAL_CRITERIA[ticker] ??
    [
      `${sectorName} 업황 방향`,
      "매출 성장과 이익률",
      "핵심 선행 지표 추세",
      "기대감이 꺾이는 위험 신호",
    ]
  );
}

/* ───────────────────────── COMPONENT ───────────────────────── */

export default function SectorMindMap() {
  const { t } = useLanguage();
  const [year, setYear] = useState(1); // 2026년 기본값
  const [selected, setSelected] = useState<SectorDef | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [topRanked, setTopRanked] = useState<any[]>([]);
  const [topRankedLoading, setTopRankedLoading] = useState(true);
  const [evaluatingStock, setEvaluatingStock] = useState<null | {
    ticker: string;
    name: string;
    sectorName: string;
    criteria: string[];
    sectorId?: string;
    flag?: "KR" | "US";
  }>(null);
  const [showTopRanked, setShowTopRanked] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: typeof window !== "undefined" ? window.innerWidth : 1200, h: typeof window !== "undefined" ? window.innerHeight : 800 });
  const isMobile = dims.w < 768;
  const navigate = useNavigate();
  const navigationTimeoutRef = useRef<number | null>(null);
  const searchTimeoutRef = useRef<number | null>(null);

  const measure = useCallback(() => {
    if (containerRef.current) {
      const r = containerRef.current.getBoundingClientRect();
      setDims({ w: r.width, h: r.height });
    }
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  // Fetch top 10 ranked stocks
  useEffect(() => {
    setTopRankedLoading(true);
    fetchTopRanked()
      .then((data) => setTopRanked(data?.rankings ?? []))
      .catch(() => {})
      .finally(() => setTopRankedLoading(false));
    // Refresh every 5 min
    const id = window.setInterval(() => {
      fetchTopRanked().then((data) => setTopRanked(data?.rankings ?? [])).catch(() => {});
    }, 300_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    return () => {
      if (navigationTimeoutRef.current !== null) {
        window.clearTimeout(navigationTimeoutRef.current);
      }
      if (searchTimeoutRef.current !== null) {
        window.clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  const cx = dims.w / 2;
  const cy = dims.h / 2;
  const orbitR = Math.min(dims.w, dims.h) * 0.34;
  const normalizedQuery = query.trim().toLowerCase();

  const yearIdx = year - 1; // 0-based index
  const weights = normalizeWeights(SECTORS, yearIdx);

  useEffect(() => {
    if (!normalizedQuery) {
      setSearchResults([]);
      setSearchLoading(false);
      return;
    }
    if (searchTimeoutRef.current !== null) {
      window.clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = window.setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await searchStocks(query.trim());
        setSearchResults(Array.isArray(res?.results) ? res.results : []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 220);
  }, [normalizedQuery, query]);

  // Analysis loading progress
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisStage, setAnalysisStage] = useState("");
  const analysisAbortRef = useRef(false);

  const openStock = useCallback((stock: { ticker: string; name: string; sectorName: string; sectorId?: string; flag?: "KR" | "US" }) => {
    setQuery("");
    setSearchOpen(false);
    const resolvedSectorName = (stock as any).sector_name ?? stock.sectorName ?? t("realtimeAnalysis");
    const resolvedSectorId = (stock as any).sector_id ?? stock.sectorId;
    const resolvedFlag = stock.flag ?? (stock.ticker.endsWith(".KS") || stock.ticker.endsWith(".KQ") ? "KR" : "US");

    // For top-pick stocks, navigate directly to sector page
    const isTopPick = SECTORS.some(s => s.picks.some(p => p.ticker === stock.ticker));
    if (isTopPick && resolvedSectorId) {
      navigate(`/sector/${resolvedSectorId}?stock=${encodeURIComponent(stock.ticker)}`);
      return;
    }

    // For non-top-pick stocks: show loading screen, pre-fetch data, then show modal
    const criteria = getEvalCriteria(stock.ticker, resolvedSectorName);
    setEvaluatingStock({
      ticker: stock.ticker,
      name: stock.name,
      sectorName: resolvedSectorName,
      criteria,
      sectorId: resolvedSectorId,
      flag: resolvedFlag as "KR" | "US",
    });
    setAnalysisProgress(0);
    setAnalysisStage(t("gatheringBasicInfo"));
    analysisAbortRef.current = false;

    // Pre-fetch all data with progress tracking
    const tkr = stock.ticker;
    const sectorId = resolvedSectorId || SECTORS[0].id;
    const steps = [
      { label: t("gatheringChartData"), weight: 25, fn: () => fetchChartData(tkr, "3mo") },
      { label: t("analyzingTechnical"), weight: 20, fn: () => fetchAnalysis(tkr) },
      { label: t("gatheringEarnings"), weight: 20, fn: () => fetchEarnings(tkr) },
      { label: t("analyzingNews"), weight: 15, fn: () => fetchNews(resolvedSectorName).catch(() => []) },
      { label: t("creatingChecklist"), weight: 20, fn: () => fetchChecklistLive(tkr).catch(() => null) },
    ];

    let completed = 0;
    (async () => {
      for (const step of steps) {
        if (analysisAbortRef.current) return;
        setAnalysisStage(step.label);
        try {
          await step.fn();
        } catch {
          // Continue even if one step fails
        }
        completed += step.weight;
        setAnalysisProgress(Math.min(completed, 99));
      }
      if (analysisAbortRef.current) return;
      setAnalysisProgress(100);
      setAnalysisStage(t("analysisComplete"));

      // Brief pause at 100% then navigate to analysis page
      await new Promise(r => setTimeout(r, 600));
      if (analysisAbortRef.current) return;

      setEvaluatingStock(null);
      const params = new URLSearchParams({
        stock: stock.ticker,
        name: stock.name,
        flag: resolvedFlag,
        dynamic: "1",
      });
      // Use _dynamic as fallback sector ID for non-top-pick stocks
      const navSectorId = SECTORS.some(s => s.id === sectorId) ? sectorId : "_dynamic";
      navigate(`/sector/${navSectorId}?${params.toString()}`);
    })();
  }, [navigate]);

  return (
    <div className="flex h-full">
      {/* ─── Stock Panel (left slide) — desktop only ─── */}
      {!isMobile && <div
        className="shrink-0 overflow-y-auto overflow-x-hidden border-r border-white/5 glass-strong transition-all duration-500 ease-out"
        style={{ width: selected ? 340 : 0, opacity: selected ? 1 : 0 }}
      >
        {selected && (
          <div className="p-6 space-y-5" style={{ animation: "fadeInUp 0.35s ease-out" }}>
            {/* Header */}
            <div className="flex items-center gap-3">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{
                  background: `linear-gradient(135deg, ${selected.color}30, ${selected.color}10)`,
                  border: `1.5px solid ${selected.color}50`,
                  boxShadow: `0 8px 32px ${selected.color}20`,
                }}
              >
                <selected.icon size={26} strokeWidth={1.5} style={{ color: selected.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-bold" style={{ color: selected.color }}>
                  {selected.name}
                </h3>
                <p className="text-[11px] text-[var(--color-text-muted)]">
                  {2025 + year}{t("investmentWeightFor")}{" "}
                  <span style={{ color: selected.color, fontWeight: 700 }}>
                    {Math.round((weights.get(selected.id) ?? 0) * 100)}%
                  </span>
                </p>
              </div>
              <button
                className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-white hover:bg-white/10 transition-all"
                onClick={() => setSelected(null)}
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
              {selected.desc}
            </p>

            {/* Materials tags */}
            {selected.materials.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {selected.materials.map((m) => (
                  <span
                    key={m}
                    className="px-2.5 py-1 rounded-full text-[10px] font-medium"
                    style={{
                      background: `linear-gradient(135deg, ${selected.color}15, ${selected.color}08)`,
                      color: selected.color,
                      border: `1px solid ${selected.color}25`,
                    }}
                  >
                    {m}
                  </span>
                ))}
              </div>
            )}

            {/* Divider */}
            <div className="h-px w-full" style={{ background: `linear-gradient(90deg, transparent, ${selected.color}30, transparent)` }} />

            {/* TOP PICKS */}
            <div>
              <p className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-widest mb-3">
                Top 5 Picks
              </p>
              <div className="space-y-2">
                {selected.picks.map((pick, i) => (
                  <div
                    key={pick.ticker}
                    className="flex items-center gap-3 px-3.5 py-3 rounded-xl cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(255,255,255,0.02)",
                      border: "1px solid rgba(255,255,255,0.04)",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = `${selected.color}12`;
                      e.currentTarget.style.borderColor = `${selected.color}30`;
                      e.currentTarget.style.transform = "translateX(4px)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.04)";
                      e.currentTarget.style.transform = "translateX(0)";
                    }}
                    onClick={() => navigate(`/sector/${selected.id}?stock=${encodeURIComponent(pick.ticker)}`)}
                  >
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-bold shrink-0"
                      style={{
                        background: `linear-gradient(135deg, ${selected.color}, ${selected.color}bb)`,
                        color: "#fff",
                        boxShadow: `0 4px 12px ${selected.color}30`,
                      }}
                    >
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-white transition-colors">
                          {pick.name}
                        </span>
                        <span
                          className="text-[9px] px-1.5 py-0.5 rounded font-bold"
                          style={{
                            background: pick.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                            color: pick.flag === "US" ? "#60a5fa" : "#f87171",
                          }}
                        >
                          {pick.flag}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--color-text-muted)] truncate mt-0.5">
                        {pick.desc}
                      </p>
                    </div>
                    <svg className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-white/60 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                ))}
              </div>
            </div>

            {/* Sector Detail Button */}
            <button
              className="w-full py-3 rounded-xl text-sm font-bold transition-all duration-300"
              style={{
                background: `linear-gradient(135deg, ${selected.color}, ${selected.color}bb)`,
                color: "#fff",
                boxShadow: `0 4px 20px ${selected.color}40`,
                border: "1px solid rgba(255,255,255,0.1)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = `0 8px 30px ${selected.color}60`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = `0 4px 20px ${selected.color}40`;
              }}
              onClick={() => navigate(`/sector/${selected.id}`)}
            >
              {t("sectorDetailAnalysis")}
            </button>
          </div>
        )}
      </div>}

      {/* ─── Mind Map Canvas ─── */}
      {/* ─── Canvas (holds both mobile & desktop) ─── */}
      <div
        ref={containerRef}
        className="flex-1 relative overflow-hidden bg-[var(--color-bg-primary)] bg-dot-grid"
      >
        {/* ═══════════ MOBILE LAYOUT ═══════════ */}
        {isMobile ? (
          <div className="h-full overflow-y-auto pb-24">
            {/* Search bar — full width */}
            <div className="px-4 pt-4 pb-2">
              <div
                className="glass rounded-2xl px-4 py-3 border border-white/10"
                style={{ boxShadow: "0 8px 24px rgba(0,0,0,0.3)" }}
              >
                <div className="flex items-center gap-3">
                  <Search size={16} className="text-[var(--color-text-muted)] shrink-0" />
                  <input
                    value={query}
                    onChange={(e) => { setQuery(e.target.value); setSearchOpen(true); }}
                    onFocus={() => setSearchOpen(true)}
                    onBlur={() => window.setTimeout(() => setSearchOpen(false), 150)}
                    onKeyDown={(e) => { if (e.key === "Enter" && searchResults[0]) openStock(searchResults[0]); }}
                    placeholder={t("stockSearch")}
                    className="w-full bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none"
                  />
                  {query && (
                    <button onClick={() => { setQuery(""); setSearchOpen(false); }} className="shrink-0 text-[var(--color-text-muted)]">
                      <X size={14} />
                    </button>
                  )}
                </div>
              </div>

              {/* Search results dropdown */}
              {searchOpen && normalizedQuery && (
                <div className="mt-2 glass rounded-2xl border border-white/10 overflow-hidden" style={{ boxShadow: "0 12px 36px rgba(0,0,0,0.4)" }}>
                  {searchLoading ? (
                    <div className="px-4 py-4 text-xs text-[var(--color-text-muted)] animate-pulse">{t("searchingStocks")}</div>
                  ) : searchResults.length > 0 ? (
                    searchResults.map((stock) => (
                      <button
                        key={stock.ticker}
                        className="w-full text-left px-4 py-3 hover:bg-white/5 active:bg-white/10 transition-colors border-b border-white/5 last:border-b-0"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => openStock(stock)}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-[var(--color-text-primary)]">{stock.name}</p>
                            <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">{stock.ticker} · {stock.sector_name ?? stock.sectorName ?? t("realtimeAnalysis")}</p>
                          </div>
                          <span className="text-[10px] px-2 py-1 rounded-full font-bold shrink-0" style={{
                            background: stock.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                            color: stock.flag === "US" ? "#60a5fa" : "#f87171",
                          }}>{stock.flag}</span>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-4 text-xs text-[var(--color-text-muted)]">{t("noStockResultsShort")}</div>
                  )}
                </div>
              )}
            </div>

            {/* Year slider — compact horizontal */}
            <div className="px-4 py-2">
              <div className="glass rounded-2xl px-4 py-2.5 border border-white/10">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] text-[var(--color-text-muted)] font-medium">{t("investmentTiming")}</span>
                  <span className="text-sm font-bold text-gradient">{2025 + year}{t("yearUnit")}</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(90deg, #3b82f6 ${((year - 1) / 29) * 100}%, rgba(255,255,255,0.08) ${((year - 1) / 29) * 100}%)`,
                    WebkitAppearance: "none",
                  }}
                />
                <div className="flex justify-between mt-1 px-0.5">
                  {[1, 5, 10, 15, 20, 25, 30].map((y) => (
                    <button key={y} onClick={() => setYear(y)} className={`text-[9px] font-mono transition-all ${y === year ? "text-white font-bold" : "text-[var(--color-text-muted)]"}`}>
                      {y}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Sector cards — 2 column grid, sized by allocation weight */}
            <div className="px-4 py-2">
              <div className="grid grid-cols-2 gap-3">
                {SECTORS.map((s, idx) => {
                  const w = weights.get(s.id) ?? 0;
                  const pct = Math.round(w * 100);
                  const isActive = selected?.id === s.id;
                  // Scale card dimensions by weight (0→1 range, typically 0.05-0.20)
                  const wNorm = Math.min(1, w * 6); // normalize: 0.17 → ~1.0
                  const cardHeight = Math.round(lerp(95, 150, wNorm));
                  const iconSize = Math.round(lerp(20, 32, wNorm));
                  const iconBox = Math.round(lerp(40, 56, wNorm));
                  const nameSize = lerp(11, 15, wNorm);
                  const pctSize = lerp(10, 13, wNorm);
                  return (
                    <button
                      key={s.id}
                      className="relative rounded-2xl p-3 flex flex-col items-center justify-center gap-1.5 transition-all duration-500 active:scale-95"
                      style={{
                        background: isActive
                          ? `linear-gradient(135deg, ${s.color}30, ${s.color}15)`
                          : `linear-gradient(135deg, rgba(255,255,255,${0.01 + wNorm * 0.04}), rgba(255,255,255,0.01))`,
                        border: `1.5px solid ${isActive ? s.color : `rgba(255,255,255,${0.04 + wNorm * 0.06})`}`,
                        boxShadow: isActive
                          ? `0 4px 20px ${s.color}25`
                          : wNorm > 0.5
                          ? `0 2px 12px ${s.color}10`
                          : "none",
                        minHeight: cardHeight,
                        animation: `fadeInUp 0.4s ease-out ${idx * 0.05}s both`,
                      }}
                      onClick={() => setSelected(isActive ? null : s)}
                    >
                      <div
                        className="rounded-xl flex items-center justify-center transition-all duration-500"
                        style={{
                          width: iconBox,
                          height: iconBox,
                          background: `linear-gradient(135deg, ${s.color}${Math.round(15 + wNorm * 20).toString(16).padStart(2, "0")}, ${s.color}10)`,
                          border: `1px solid ${s.color}30`,
                        }}
                      >
                        <s.icon size={iconSize} strokeWidth={1.5} style={{ color: s.color }} />
                      </div>
                      <span
                        className="font-bold text-[var(--color-text-primary)] text-center leading-tight transition-all duration-500"
                        style={{ fontSize: nameSize }}
                      >
                        {s.name}
                      </span>
                      <span
                        className="font-mono px-2 py-0.5 rounded-full font-bold transition-all duration-500"
                        style={{
                          fontSize: pctSize,
                          background: `linear-gradient(135deg, ${s.color}20, ${s.color}10)`,
                          color: s.color,
                          border: `1px solid ${s.color}20`,
                        }}
                      >
                        {pct}%
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Top 10 Ranking — collapsible */}
            <div className="px-4 py-2">
              <div className="glass rounded-2xl border border-white/10 overflow-hidden">
                <button
                  className="w-full px-4 py-3 flex items-center gap-2"
                  onClick={() => setShowTopRanked(!showTopRanked)}
                >
                  <Trophy size={14} className="text-[#f59e0b]" />
                  <span className="text-xs font-bold text-[var(--color-text-primary)]">{t("overallScoreTop10")}</span>
                  <span className="text-[10px] text-[var(--color-text-muted)] ml-auto mr-2">{t("realtime")}</span>
                  {showTopRanked ? <ChevronUp size={14} className="text-[var(--color-text-muted)]" /> : <ChevronDown size={14} className="text-[var(--color-text-muted)]" />}
                </button>
                {showTopRanked && (
                  <div className="border-t border-white/5">
                    {topRankedLoading ? (
                      <div className="px-4 py-6 text-xs text-[var(--color-text-muted)] animate-pulse text-center">{t("calculatingRanking")}</div>
                    ) : topRanked.length === 0 ? (
                      <div className="px-4 py-4 text-xs text-[var(--color-text-muted)] text-center">{t("loadingData")}</div>
                    ) : (
                      topRanked.map((stock, i) => (
                        <button
                          key={stock.ticker}
                          className="w-full flex items-center gap-3 px-4 py-2.5 active:bg-white/10 transition-colors border-b border-white/5 last:border-b-0"
                          onClick={() => {
                            const sector = SECTORS.find(sec => sec.picks.some(p => p.ticker === stock.ticker));
                            if (sector) {
                              navigate(`/sector/${sector.id}?stock=${encodeURIComponent(stock.ticker)}`);
                            } else {
                              openStock({ ticker: stock.ticker, name: stock.name, sectorName: stock.sector_name || "", sectorId: stock.sector_id, flag: stock.flag });
                            }
                          }}
                        >
                          <div
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-black shrink-0"
                            style={{
                              background: i < 3 ? "linear-gradient(135deg, #f59e0b, #d97706)" : "rgba(255,255,255,0.06)",
                              color: i < 3 ? "#fff" : "var(--color-text-muted)",
                              boxShadow: i < 3 ? "0 2px 8px rgba(245,158,11,0.3)" : "none",
                            }}
                          >{i + 1}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{stock.name}</span>
                              <span className="text-[8px] px-1 py-0.5 rounded font-bold shrink-0" style={{
                                background: stock.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                                color: stock.flag === "US" ? "#60a5fa" : "#f87171",
                              }}>{stock.flag}</span>
                            </div>
                            <p className="text-[10px] text-[var(--color-text-muted)] truncate">{stock.ticker} · {stock.sector_name}</p>
                          </div>
                          <div className="shrink-0 text-right">
                            <p className="text-sm font-black" style={{ color: stock.score >= 65 ? "#22c55e" : stock.score >= 45 ? "#eab308" : "#ef4444" }}>{stock.score}</p>
                            {stock.change_1m != null && (
                              <div className="flex items-center gap-0.5 justify-end">
                                {stock.change_1m >= 0 ? <TrendingUp size={10} className="text-[#22c55e]" /> : <TrendingDown size={10} className="text-[#ef4444]" />}
                                <span className={`text-[10px] font-mono ${stock.change_1m >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
                                  {stock.change_1m >= 0 ? "+" : ""}{stock.change_1m}%
                                </span>
                              </div>
                            )}
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* ═══════════ DESKTOP LAYOUT (unchanged SVG mind map) ═══════════ */
          <>
        <div className="absolute top-5 left-5 z-40 w-[min(360px,calc(100%-2.5rem))]">
          <div
            className="glass rounded-2xl px-4 py-3 border border-white/10"
            style={{ boxShadow: "0 12px 40px rgba(0,0,0,0.35)" }}
          >
            <div className="flex items-center gap-3">
              <Search size={16} className="text-[var(--color-text-muted)] shrink-0" />
              <input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSearchOpen(true);
                }}
                onFocus={() => setSearchOpen(true)}
                onBlur={() => window.setTimeout(() => setSearchOpen(false), 150)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && searchResults[0]) {
                    openStock(searchResults[0]);
                  }
                }}
                placeholder="AI 분석 개별종목 검색"
                className="w-full bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none"
              />
            </div>
          </div>

          {searchOpen && normalizedQuery && (
            <div
              className="mt-2 glass rounded-2xl border border-white/10 overflow-hidden"
              style={{ boxShadow: "0 12px 36px rgba(0,0,0,0.4)" }}
            >
              {searchLoading ? (
                <div className="px-4 py-4 text-xs text-[var(--color-text-muted)] animate-pulse">
                  {t("searchingStocks")}
                </div>
              ) : searchResults.length > 0 ? (
                searchResults.map((stock) => (
                  <button
                    key={stock.ticker}
                    className="w-full text-left px-4 py-3 hover:bg-white/5 transition-colors border-b border-white/5 last:border-b-0"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => openStock(stock)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                          {stock.name}
                        </p>
                        <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                          {stock.ticker} · {stock.sector_name ?? stock.sectorName ?? t("realtimeAnalysis")}
                        </p>
                      </div>
                      <span
                        className="text-[10px] px-2 py-1 rounded-full font-bold shrink-0"
                        style={{
                          background: stock.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                          color: stock.flag === "US" ? "#60a5fa" : "#f87171",
                        }}
                      >
                        {stock.flag}
                      </span>
                    </div>
                  </button>
                ))
              ) : (
                <div className="px-4 py-4 text-xs text-[var(--color-text-muted)]">
                  {t("noStockResults")}
                </div>
              )}
            </div>
          )}
          {/* ─── Top 10 Ranking ─── */}
          {!searchOpen && !normalizedQuery && (
            <div
              className="mt-3 glass rounded-2xl border border-white/10 overflow-hidden"
              style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.3)", maxHeight: 420, overflowY: "auto" }}
            >
              <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                <Trophy size={14} className="text-[#f59e0b]" />
                <span className="text-xs font-bold text-[var(--color-text-primary)]">{t("overallScoreTop10")}</span>
                <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">{t("realtime")}</span>
              </div>
              {topRankedLoading ? (
                <div className="px-4 py-6 text-xs text-[var(--color-text-muted)] animate-pulse text-center">{t("calculatingRanking")}</div>
              ) : topRanked.length === 0 ? (
                <div className="px-4 py-4 text-xs text-[var(--color-text-muted)] text-center">{t("loadingData")}</div>
              ) : (
                topRanked.map((stock, i) => (
                  <button
                    key={stock.ticker}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors border-b border-white/3 last:border-b-0"
                    onClick={() => {
                      const sector = SECTORS.find(s => s.picks.some(p => p.ticker === stock.ticker));
                      if (sector) {
                        navigate(`/sector/${sector.id}?stock=${encodeURIComponent(stock.ticker)}`);
                      } else {
                        openStock({ ticker: stock.ticker, name: stock.name, sectorName: stock.sector_name || "", sectorId: stock.sector_id, flag: stock.flag });
                      }
                    }}
                  >
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-black shrink-0"
                      style={{
                        background: i < 3 ? "linear-gradient(135deg, #f59e0b, #d97706)" : "rgba(255,255,255,0.06)",
                        color: i < 3 ? "#fff" : "var(--color-text-muted)",
                        boxShadow: i < 3 ? "0 2px 8px rgba(245,158,11,0.3)" : "none",
                      }}
                    >
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{stock.name}</span>
                        <span
                          className="text-[8px] px-1 py-0.5 rounded font-bold shrink-0"
                          style={{
                            background: stock.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                            color: stock.flag === "US" ? "#60a5fa" : "#f87171",
                          }}
                        >
                          {stock.flag}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--color-text-muted)] truncate">{stock.ticker} · {stock.sector_name}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-black" style={{
                        color: stock.score >= 65 ? "#22c55e" : stock.score >= 45 ? "#eab308" : "#ef4444"
                      }}>{stock.score}</p>
                      {stock.change_1m != null && (
                        <div className="flex items-center gap-0.5 justify-end">
                          {stock.change_1m >= 0 ? <TrendingUp size={10} className="text-[#22c55e]" /> : <TrendingDown size={10} className="text-[#ef4444]" />}
                          <span className={`text-[10px] font-mono ${stock.change_1m >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
                            {stock.change_1m >= 0 ? "+" : ""}{stock.change_1m}%
                          </span>
                        </div>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Ambient glow blobs */}
        <div className="absolute pointer-events-none" style={{ left: cx - 250, top: cy - 250, width: 500, height: 500, background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%)", animation: "breathe 8s ease-in-out infinite" }} />
        <div className="absolute pointer-events-none" style={{ left: cx + 100, top: cy - 200, width: 400, height: 400, background: "radial-gradient(circle, rgba(168,85,247,0.04) 0%, transparent 70%)", animation: "breathe 10s ease-in-out infinite 2s" }} />

        {/* ─── Year Slider (fixed right) ─── */}
        <div className="fixed top-14 right-5 z-40 flex flex-col items-end gap-2">
          <div className="glass rounded-2xl px-5 py-3 flex flex-col gap-2" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)", width: 260 }}>
            <div className="flex items-center justify-between w-full">
              <span className="text-[11px] text-[var(--color-text-muted)] font-medium">{t("investmentTiming")}</span>
              <span className="text-sm font-bold text-gradient">{2025 + year}{t("yearUnit")}</span>
            </div>
            <div className="w-full relative">
              <input
                type="range"
                min={1}
                max={30}
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(90deg, #3b82f6 ${((year - 1) / 29) * 100}%, rgba(255,255,255,0.08) ${((year - 1) / 29) * 100}%)`,
                  WebkitAppearance: "none",
                }}
              />
              <div className="flex justify-between mt-1.5 px-0.5">
                {[1, 5, 10, 15, 20, 25, 30].map((y) => (
                  <button
                    key={y}
                    onClick={() => setYear(y)}
                    className={`text-[9px] font-mono transition-all ${
                      y === year ? "text-white font-bold" : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                    }`}
                  >
                    {y}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="text-[9px] text-[var(--color-text-muted)] tracking-wide pr-1">
            {2025 + year}{t("yearUnit")} {t("investmentAllocation")}
          </p>
        </div>

        {/* SVG Lines & Effects */}
        <svg width={dims.w} height={dims.h} className="absolute inset-0 pointer-events-none">
          <defs>
            {SECTORS.map((s) => (
              <linearGradient key={`grad-${s.id}`} id={`grad-${s.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={s.color} stopOpacity="0" />
                <stop offset="50%" stopColor={s.color} stopOpacity="0.5" />
                <stop offset="100%" stopColor={s.color} stopOpacity="0.1" />
              </linearGradient>
            ))}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Orbit rings */}
          {[0.96, 1, 1.04].map((scale, i) => (
            <circle key={i} cx={cx} cy={cy} r={orbitR * scale} fill="none" stroke="var(--color-border)" strokeWidth={i === 1 ? 0.8 : 0.3} strokeDasharray={i === 1 ? "6 12" : "2 16"} opacity={i === 1 ? 0.3 : 0.12} />
          ))}

          {/* Connection lines */}
          {SECTORS.map((s) => {
            const rad = (s.angle * Math.PI) / 180;
            const sx = cx + Math.cos(rad) * orbitR;
            const sy = cy + Math.sin(rad) * orbitR;
            const w = weights.get(s.id) ?? 0;
            const isActive = selected?.id === s.id;
            const isHov = hovered === s.id;

            return (
              <g key={s.id}>
                <line x1={cx} y1={cy} x2={sx} y2={sy} stroke={`url(#grad-${s.id})`} strokeWidth={isActive || isHov ? lerp(2, 4, w) : lerp(1, 2.5, w)} opacity={isActive ? 0.8 : isHov ? 0.6 : lerp(0.15, 0.35, w)} style={{ transition: "all 0.4s ease" }} />
                <circle r={isActive ? 3 : 2} fill={s.color} opacity={isActive ? 0.9 : 0.4} filter={isActive ? "url(#glow)" : ""}>
                  <animateMotion dur={`${3 - w * 1.5}s`} repeatCount="indefinite" path={`M${cx},${cy} L${sx},${sy}`} />
                </circle>
                {isActive && (
                  <>
                    <circle cx={sx} cy={sy} r={lerp(55, 100, w)} fill="none" stroke={s.color} strokeWidth={1} opacity={0.15}>
                      <animate attributeName="r" values={`${lerp(55, 100, w)};${lerp(70, 120, w)};${lerp(55, 100, w)}`} dur="3s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.15;0.05;0.15" dur="3s" repeatCount="indefinite" />
                    </circle>
                    <circle cx={sx} cy={sy} r={lerp(45, 85, w)} fill={s.color} opacity={0.06}>
                      <animate attributeName="r" values={`${lerp(45, 85, w)};${lerp(55, 95, w)};${lerp(45, 85, w)}`} dur="2s" repeatCount="indefinite" />
                    </circle>
                  </>
                )}
              </g>
            );
          })}
        </svg>

        {/* Central Node */}
        <div
          className="absolute z-20 rounded-full flex flex-col items-center justify-center cursor-default select-none"
          style={{
            left: cx - 55, top: cy - 55, width: 110, height: 110,
            background: "radial-gradient(circle at 30% 30%, #1e3a5f 0%, #0c1220 80%)",
            border: "1.5px solid rgba(59,130,246,0.3)",
            boxShadow: "0 0 80px rgba(59,130,246,0.12), 0 0 30px rgba(59,130,246,0.06), inset 0 1px 0 rgba(255,255,255,0.05)",
            animation: "breathe 6s ease-in-out infinite",
          }}
          onClick={() => setSelected(null)}
        >
          <div className="absolute inset-2 rounded-full" style={{ border: "1px solid rgba(59,130,246,0.1)" }} />
          <Factory size={32} className="mb-1" style={{ color: "#60a5fa", filter: "drop-shadow(0 0 10px rgba(59,130,246,0.4))" }} strokeWidth={1.5} />
          <span className="text-[13px] font-bold text-center leading-tight text-gradient">
            {t("futureGrowth")}
            <br />
            {t("industry")}
          </span>
        </div>

        {/* Sector Nodes */}
        {SECTORS.map((s, idx) => {
          const w = weights.get(s.id) ?? 0;
          const rad = (s.angle * Math.PI) / 180;
          const sx = cx + Math.cos(rad) * orbitR;
          const sy = cy + Math.sin(rad) * orbitR;
          const size = lerp(75, 155, w * 8);
          const clampedSize = Math.max(75, Math.min(155, size));
          const isActive = selected?.id === s.id;
          const isHov = hovered === s.id;
          const pct = Math.round(w * 100);

          return (
            <div
              key={s.id}
              className="absolute z-20 rounded-full flex flex-col items-center justify-center cursor-pointer select-none node-hover"
              style={{
                left: sx - clampedSize / 2,
                top: sy - clampedSize / 2,
                width: clampedSize,
                height: clampedSize,
                background: isActive
                  ? `radial-gradient(circle at 30% 30%, ${s.color}dd, ${s.color}88)`
                  : `radial-gradient(circle at 30% 30%, ${s.color}22, ${s.color}08)`,
                border: `1.5px solid ${isActive ? s.color : `${s.color}${isHov ? "80" : "40"}`}`,
                boxShadow: isActive
                  ? `0 0 50px ${s.color}35, 0 0 100px ${s.color}15, inset 0 1px 0 rgba(255,255,255,0.1)`
                  : isHov
                  ? `0 0 40px ${s.color}25, inset 0 1px 0 rgba(255,255,255,0.05)`
                  : `0 0 20px ${s.color}08, inset 0 1px 0 rgba(255,255,255,0.03)`,
                transform: isActive ? "scale(1.06)" : "scale(1)",
                animation: `fadeInUp 0.5s ease-out ${idx * 0.06}s both`,
                transition: "width 0.5s ease, height 0.5s ease, left 0.5s ease, top 0.5s ease, background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease",
              }}
              onClick={() => setSelected(isActive ? null : s)}
              onMouseEnter={() => setHovered(s.id)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="absolute inset-1.5 rounded-full pointer-events-none" style={{ border: `1px solid ${s.color}${isActive ? "30" : "10"}` }} />
              <s.icon
                size={lerp(22, 38, w * 8)}
                strokeWidth={1.5}
                style={{
                  color: isActive ? "#fff" : s.color,
                  filter: `drop-shadow(0 0 ${isActive ? 12 : 6}px ${s.color}${isActive ? "aa" : "60"})`,
                  transition: "all 0.5s ease",
                }}
              />
              <span
                className="text-center font-bold leading-tight mt-1"
                style={{
                  fontSize: Math.max(11, lerp(11, 17, w * 8)),
                  color: isActive ? "#fff" : "var(--color-text-primary)",
                  whiteSpace: "pre-line",
                  textShadow: isActive ? `0 0 20px ${s.color}60` : "none",
                  transition: "all 0.3s ease",
                }}
              >
                {s.name}
              </span>
              <span
                className="text-[11px] font-mono mt-1 px-2.5 py-0.5 rounded-full font-bold"
                style={{
                  background: isActive ? "rgba(255,255,255,0.15)" : `linear-gradient(135deg, ${s.color}20, ${s.color}10)`,
                  color: isActive ? "#fff" : s.color,
                  border: `1px solid ${isActive ? "rgba(255,255,255,0.2)" : `${s.color}20`}`,
                  backdropFilter: "blur(4px)",
                  transition: "all 0.3s ease",
                }}
              >
                {pct}%
              </span>
            </div>
          );
        })}

        {/* Legend bottom-right */}
        <div className="absolute bottom-5 right-5 z-30 flex items-center gap-4 text-[10px] text-[var(--color-text-muted)] glass rounded-xl px-4 py-2.5">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: "rgba(59,130,246,0.2)", border: "1px solid rgba(59,130,246,0.3)" }} />
            {t("lowAllocation")}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-5 h-5 rounded-full" style={{ background: "rgba(59,130,246,0.2)", border: "1px solid rgba(59,130,246,0.3)" }} />
            {t("medium")}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-7 h-7 rounded-full" style={{ background: "rgba(59,130,246,0.2)", border: "1px solid rgba(59,130,246,0.3)" }} />
            {t("highAllocation")}
          </span>
        </div>

        {/* Sector count */}
        <div className="absolute bottom-5 left-5 z-30 text-[11px] text-[var(--color-text-muted)] glass rounded-xl px-4 py-2.5 font-medium">
          {SECTORS.length} {t("sectors")} · {SECTORS.reduce((a, s) => a + s.picks.length, 0)} {t("stocks")}
        </div>
          </>
        )}

        {/* ─── Evaluating stock overlay (shared mobile/desktop) ─── */}
        {evaluatingStock && (
          <div className={`absolute inset-0 z-50 flex items-center justify-center bg-black/55 backdrop-blur-md ${isMobile ? "px-4" : "px-4"}`}>
            <div
              className={`w-full max-w-lg rounded-3xl border border-white/10 glass ${isMobile ? "mx-4 px-5 py-6" : "px-8 py-8"} relative`}
              style={{ boxShadow: "0 24px 80px rgba(0,0,0,0.55)" }}
            >
              {/* Close button */}
              <button
                onClick={() => { analysisAbortRef.current = true; setEvaluatingStock(null); }}
                className="absolute top-4 right-4 w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={16} />
              </button>

              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-accent-blue)]">
                AI Deep Analysis
              </p>
              <h3 className={`${isMobile ? "text-xl" : "text-2xl"} font-black text-[var(--color-text-primary)] mt-2`}>
                {evaluatingStock.name}
              </h3>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">
                {evaluatingStock.ticker} · {evaluatingStock.sectorName}
              </p>

              {/* Progress bar */}
              <div className="mt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[var(--color-text-secondary)] font-medium">{analysisStage}</span>
                  <span className="text-sm font-black text-[var(--color-accent-blue)]">{analysisProgress}%</span>
                </div>
                <div className="h-2.5 rounded-full bg-white/8 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${analysisProgress}%`,
                      background: analysisProgress >= 100
                        ? "linear-gradient(90deg, #22c55e, #16a34a)"
                        : "linear-gradient(90deg, #3b82f6, #8b5cf6)",
                    }}
                  />
                </div>
              </div>

              {/* Analysis steps */}
              <div className="mt-5 space-y-2">
                {[
                  { label: t("chartCollection"), threshold: 25 },
                  { label: t("technicalAnalysis"), threshold: 45 },
                  { label: t("financialAnalysis"), threshold: 65 },
                  { label: t("newsAnalysis"), threshold: 80 },
                  { label: t("checklistCreation"), threshold: 100 },
                ].map((step) => {
                  const done = analysisProgress >= step.threshold;
                  const active = !done && analysisProgress >= step.threshold - 25;
                  return (
                    <div
                      key={step.label}
                      className={`flex items-center gap-3 rounded-xl ${isMobile ? "px-3 py-2" : "px-4 py-2.5"} transition-all duration-300`}
                      style={{
                        background: done ? "rgba(34,197,94,0.08)" : active ? "rgba(59,130,246,0.08)" : "rgba(255,255,255,0.02)",
                        border: `1px solid ${done ? "rgba(34,197,94,0.2)" : active ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.05)"}`,
                      }}
                    >
                      <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{
                        background: done ? "#22c55e" : active ? "#3b82f6" : "rgba(255,255,255,0.1)",
                      }}>
                        {done ? (
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2.5 6L5 8.5L9.5 3.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                        ) : active ? (
                          <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-white/30" />
                        )}
                      </div>
                      <span className={`text-sm ${done ? "text-[#22c55e] font-semibold" : active ? "text-[var(--color-text-primary)] font-medium" : "text-[var(--color-text-muted)]"}`}>
                        {step.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ─── Mobile sector overlay (bottom sheet) ─── */}
      {isMobile && selected && (
        <div
          className="fixed inset-0 z-50 flex flex-col justify-end"
          onClick={() => setSelected(null)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

          {/* Bottom sheet */}
          <div
            className="relative z-10 rounded-t-3xl overflow-y-auto"
            style={{
              maxHeight: "85vh",
              background: "var(--color-bg-primary)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderBottom: "none",
              boxShadow: "0 -12px 60px rgba(0,0,0,0.5)",
              animation: "fadeInUp 0.3s ease-out",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 rounded-full bg-white/20" />
            </div>

            <div className="px-5 pb-8 space-y-5">
              {/* Header */}
              <div className="flex items-center gap-3">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center"
                  style={{
                    background: `linear-gradient(135deg, ${selected.color}30, ${selected.color}10)`,
                    border: `1.5px solid ${selected.color}50`,
                    boxShadow: `0 8px 32px ${selected.color}20`,
                  }}
                >
                  <selected.icon size={26} strokeWidth={1.5} style={{ color: selected.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold" style={{ color: selected.color }}>
                    {selected.name}
                  </h3>
                  <p className="text-[11px] text-[var(--color-text-muted)]">
                    {2025 + year}{t("investmentWeightFor")}{" "}
                    <span style={{ color: selected.color, fontWeight: 700 }}>
                      {Math.round((weights.get(selected.id) ?? 0) * 100)}%
                    </span>
                  </p>
                </div>
                <button
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-[var(--color-text-muted)] hover:text-white bg-white/5 active:bg-white/10 transition-all"
                  onClick={() => setSelected(null)}
                >
                  <X size={18} />
                </button>
              </div>

              {/* Description */}
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                {selected.desc}
              </p>

              {/* Material tags */}
              {selected.materials.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selected.materials.map((m) => (
                    <span
                      key={m}
                      className="px-2.5 py-1 rounded-full text-[10px] font-medium"
                      style={{
                        background: `linear-gradient(135deg, ${selected.color}15, ${selected.color}08)`,
                        color: selected.color,
                        border: `1px solid ${selected.color}25`,
                      }}
                    >
                      {m}
                    </span>
                  ))}
                </div>
              )}

              {/* Divider */}
              <div className="h-px w-full" style={{ background: `linear-gradient(90deg, transparent, ${selected.color}30, transparent)` }} />

              {/* Top 5 Picks */}
              <div>
                <p className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-widest mb-3">
                  Top 5 Picks
                </p>
                <div className="space-y-2">
                  {selected.picks.map((pick, i) => (
                    <div
                      key={pick.ticker}
                      className="flex items-center gap-3 px-3.5 py-3 rounded-xl active:bg-white/5 transition-all duration-200"
                      style={{
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid rgba(255,255,255,0.04)",
                      }}
                      onClick={() => navigate(`/sector/${selected.id}?stock=${encodeURIComponent(pick.ticker)}`)}
                    >
                      <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-bold shrink-0"
                        style={{
                          background: `linear-gradient(135deg, ${selected.color}, ${selected.color}bb)`,
                          color: "#fff",
                          boxShadow: `0 4px 12px ${selected.color}30`,
                        }}
                      >
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                            {pick.name}
                          </span>
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded font-bold"
                            style={{
                              background: pick.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                              color: pick.flag === "US" ? "#60a5fa" : "#f87171",
                            }}
                          >
                            {pick.flag}
                          </span>
                        </div>
                        <p className="text-[10px] text-[var(--color-text-muted)] truncate mt-0.5">
                          {pick.desc}
                        </p>
                      </div>
                      <svg className="w-4 h-4 text-[var(--color-text-muted)] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sector detail button */}
              <button
                className="w-full py-3.5 rounded-xl text-sm font-bold transition-all duration-300"
                style={{
                  background: `linear-gradient(135deg, ${selected.color}, ${selected.color}bb)`,
                  color: "#fff",
                  boxShadow: `0 4px 20px ${selected.color}40`,
                  border: "1px solid rgba(255,255,255,0.1)",
                }}
                onClick={() => navigate(`/sector/${selected.id}`)}
              >
                {t("sectorDetailAnalysis")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
