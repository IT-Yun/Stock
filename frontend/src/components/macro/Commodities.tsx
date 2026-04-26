import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BarChart3, Clock, ExternalLink, Flame, History, Snowflake, Target, TrendingDown, TrendingUp, X } from "lucide-react";
import MacroLayout from "./MacroLayout";
import ChartView from "@/components/ChartView";
import { fetchCommodities, fetchRegime } from "@/api/macro";
import type { CommoditiesResponse, CommodityFeedItem, RegimeItem, RegimeLabel, RegimeResponse } from "@/types/macro";
import Sparkline from "./Sparkline";

// 카테고리 → 가장 영향을 받는 섹터 매핑 (wiki/macro/01-commodities.md 기반)
const CATEGORY_TO_SECTORS: Record<string, { sector: string; effect: string }[]> = {
  "에너지": [
    { sector: "수소/에너지", effect: "정유·LNG 마진" },
    { sector: "우주항공/방산", effect: "지정학 동반 발주" },
    { sector: "조선", effect: "LNG선·VLCC 발주" },
  ],
  "산업금속": [
    { sector: "AI/반도체", effect: "구리·은 = 데이터센터 인프라" },
    { sector: "이차전지", effect: "구리·니켈·알루미늄" },
    { sector: "전기차 완성차", effect: "구리·알루미늄 차체" },
    { sector: "조선", effect: "철강 후판" },
    { sector: "건설/건자재", effect: "철근·구리" },
  ],
  "귀금속": [
    { sector: "AI/반도체", effect: "은 = 본딩와이어, 백금/팔라듐 = 촉매" },
    { sector: "전기차 완성차", effect: "팔라듐·백금 = 자동차 촉매" },
    { sector: "수소/에너지", effect: "백금·이리듐 = 전해조 촉매" },
  ],
  "희소금속": [
    { sector: "이차전지", effect: "리튬·코발트·망간 = 양극재" },
    { sector: "EV 소재/부품", effect: "리튬·흑연·니켈" },
    { sector: "AI/반도체", effect: "갈륨·게르마늄 = 화합물반도체" },
    { sector: "수소/에너지", effect: "이리듐 = PEM 전해조" },
    { sector: "양자컴퓨팅", effect: "헬륨-3 = dilution refrigerator" },
  ],
  "반도체 가스": [
    { sector: "AI/반도체", effect: "네온·크립톤·크세논 = EUV/DUV 노광" },
    { sector: "디스플레이", effect: "특수가스 = OLED 증착" },
  ],
  "양자/방산 특수재": [
    { sector: "양자컴퓨팅", effect: "헬륨-3·이리듐 = 핵심 병목" },
    { sector: "우주항공/방산", effect: "티타늄 = 항공기 동체" },
  ],
  "농산물": [
    { sector: "음식료", effect: "곡물·설탕·코코아 원가" },
    { sector: "화장품", effect: "면화·코코아 = 일부 ODM" },
  ],
  "화학원료": [
    { sector: "이차전지", effect: "황산·NaOH = 전해질 가공" },
    { sector: "AI/반도체", effect: "고순도 인산 = HBM 식각" },
  ],
  "바이오 원료": [
    { sector: "생명공학", effect: "GLP-1 펩타이드 등 CDMO 원료" },
    { sector: "의료기기/미용", effect: "필러·톡신 원료" },
  ],
  "매크로신호": [
    { sector: "전체 섹터", effect: "위험선호도 측정 (구리/금, 금/은 비율)" },
  ],
};

const BUY_ACTIONS = new Set(["분할 매수 관심", "눌림 매수 후보"]);
const SELL_ACTIONS = new Set(["매도·회피", "추격 금지"]);

const REGIME_ORDER: RegimeLabel[] = ["Breakout", "Rebound", "Topping", "Crash", "Sleeper", "Steady"];

const REGIME_STYLE: Record<RegimeLabel, { label: string; bg: string; text: string; ring: string; icon: any }> = {
  Breakout: { label: "Breakout", bg: "bg-emerald-500/15", text: "text-emerald-300", ring: "ring-emerald-500/40", icon: TrendingUp },
  Rebound:  { label: "Rebound",  bg: "bg-teal-500/15",    text: "text-teal-300",    ring: "ring-teal-500/40",    icon: TrendingUp },
  Steady:   { label: "Steady",   bg: "bg-slate-500/15",   text: "text-slate-300",   ring: "ring-slate-500/40",   icon: Activity },
  Topping:  { label: "Topping",  bg: "bg-amber-500/15",   text: "text-amber-300",   ring: "ring-amber-500/40",   icon: TrendingDown },
  Crash:    { label: "Crash",    bg: "bg-rose-500/15",    text: "text-rose-300",    ring: "ring-rose-500/40",    icon: TrendingDown },
  Sleeper:  { label: "Sleeper",  bg: "bg-indigo-500/15",  text: "text-indigo-300",  ring: "ring-indigo-500/40",  icon: Clock },
};

export default function Commodities() {
  const [data, setData] = useState<CommoditiesResponse | null>(null);
  const [regime, setRegime] = useState<RegimeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<CommodityFeedItem | null>(null);
  const [regimeFilter, setRegimeFilter] = useState<RegimeLabel | null>(null);

  useEffect(() => {
    Promise.all([
      fetchCommodities().then(setData).catch((e) => console.error("commodities", e)),
      fetchRegime().then(setRegime).catch((e) => console.error("regime", e)),
    ]).finally(() => setLoading(false));
  }, []);

  const regimeMap = useMemo(() => {
    const map = new Map<string, RegimeItem>();
    regime?.items.forEach((it) => map.set(it.id, it));
    return map;
  }, [regime]);

  const matrix = useMemo(() => {
    const feed = data?.feed ?? [];
    const ranked = [...feed].sort((a, b) => Math.abs(b.trend_score ?? 0) - Math.abs(a.trend_score ?? 0));
    const buy = ranked
      .filter((x) => BUY_ACTIONS.has(x.timing_action ?? "") && (x.confidence ?? 0) >= 45)
      .sort((a, b) => (b.timing_score ?? 0) - (a.timing_score ?? 0))
      .slice(0, 6);
    const surge = ranked
      .filter((x) => x.is_surge || ((x.change_pct_60d ?? 0) >= 18 && (x.confidence ?? 0) >= 45))
      .sort((a, b) => {
        const ap = xPriority(a);
        const bp = xPriority(b);
        if (bp !== ap) return bp - ap;
        return Math.abs(b.change_pct_5d ?? b.change_pct_60d ?? 0) - Math.abs(a.change_pct_5d ?? a.change_pct_60d ?? 0);
      })
      .slice(0, 6);
    const sell = ranked
      .filter((x) => SELL_ACTIONS.has(x.timing_action ?? "") || x.is_plunge || x.is_multi_month_downtrend)
      .sort((a, b) => {
        const ta = Math.abs(a.timing_score ?? 0);
        const tb = Math.abs(b.timing_score ?? 0);
        return tb - ta;
      })
      .slice(0, 6);
    return { buy, surge, sell };
  }, [data]);

  if (loading) return <MacroLayout title="원자재 매매 시그널" subtitle="실시간 가격 업데이트 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="원자재 매매 시그널" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  const liveCount = data.feed.filter((f) => f.coverage_status === "live").length;
  const proxyCount = data.feed.filter((f) => f.coverage_status === "proxy" || f.coverage_status === "computed_proxy").length;
  const delayedCount = data.feed.filter((f) => ["delayed", "monthly", "stale_fallback"].includes(f.coverage_status ?? "")).length;

  return (
    <MacroLayout
      title="원자재 매매 시그널"
      subtitle={`매일 업데이트 · ${data.feed.length}개 추적 · live ${liveCount} · proxy/계산 ${proxyCount} · 지연/월간 ${delayedCount}`}
    >
      {regime && regime.total_items > 0 && (
        <RegimePanel
          regime={regime}
          activeFilter={regimeFilter}
          onFilter={setRegimeFilter}
        />
      )}

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-3">
        <SignalPanel
          title="매수 타이밍"
          icon={<Target size={18} />}
          tone="green"
          items={matrix.buy}
          empty="현재 분할/눌림 매수 후보 없음"
          onSelect={setSelected}
        />
        <SignalPanel
          title="급등·상승 원인"
          icon={<Flame size={18} />}
          tone="red"
          items={matrix.surge}
          empty="현재 신뢰도 있는 급등/중기 상승 신호 없음"
          onSelect={setSelected}
        />
        <SignalPanel
          title="매도·회피"
          icon={<Snowflake size={18} />}
          tone="blue"
          items={matrix.sell}
          empty="현재 매도/회피 후보 없음"
          onSelect={setSelected}
        />
      </section>

      <AllCommoditiesSection
        feed={data.feed}
        regimeMap={regimeMap}
        onSelect={setSelected}
      />

      <SectorImpactSection
        feed={data.feed}
        onSelect={setSelected}
      />

      {selected && <CommodityModal item={selected} onClose={() => setSelected(null)} />}
    </MacroLayout>
  );
}

function RegimePanel({
  regime,
  activeFilter,
  onFilter,
}: {
  regime: RegimeResponse;
  activeFilter: RegimeLabel | null;
  onFilter: (label: RegimeLabel | null) => void;
}) {
  const items = activeFilter
    ? regime.distribution[activeFilter] ?? []
    : [...regime.changed_today].length > 0
      ? regime.changed_today
      : regime.items.filter((it) => ["Breakout", "Crash", "Topping", "Rebound"].includes(it.current_regime));

  return (
    <section className="mb-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <History size={18} className="text-violet-300" />
          <h3 className="text-sm font-semibold text-slate-200">5년 Regime 분석</h3>
          <span className="text-xs text-slate-400">
            {regime.total_items}개 추적 · 오늘 변화 {regime.regime_changes_today}건
            {regime.updated && ` · ${regime.updated.slice(0, 16).replace("T", " ")}`}
          </span>
        </div>
        <div className="text-xs text-slate-500">명세 wiki/macro/05-regime-scoring.md</div>
      </header>

      <div className="flex flex-wrap gap-2 mb-3">
        <FilterChip
          active={activeFilter === null}
          onClick={() => onFilter(null)}
          label={`오늘 변화 (${regime.regime_changes_today})`}
        />
        {REGIME_ORDER.map((r) => {
          const count = regime.distribution[r]?.length ?? 0;
          const style = REGIME_STYLE[r];
          return (
            <button
              key={r}
              onClick={() => onFilter(activeFilter === r ? null : r)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium ring-1 transition ${
                activeFilter === r
                  ? `${style.bg} ${style.text} ${style.ring}`
                  : "bg-slate-800/40 text-slate-400 ring-slate-700 hover:bg-slate-800"
              }`}
            >
              {style.label} <span className="ml-1 opacity-70">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        {items.length === 0 ? (
          <div className="text-xs text-slate-500 col-span-full py-2">표시할 항목 없음</div>
        ) : (
          items.map((it) => <RegimeCard key={it.id} item={it} />)
        )}
      </div>
    </section>
  );
}

function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 rounded-md text-xs font-medium ring-1 transition ${
        active
          ? "bg-violet-500/15 text-violet-300 ring-violet-500/40"
          : "bg-slate-800/40 text-slate-400 ring-slate-700 hover:bg-slate-800"
      }`}
    >
      {label}
    </button>
  );
}

function RegimeCard({ item }: { item: RegimeItem }) {
  const style = REGIME_STYLE[item.current_regime] ?? REGIME_STYLE.Steady;
  const Icon = style.icon;
  const m = item.metrics ?? {};
  const pct5y = ((m.pct_5y ?? 0) * 100).toFixed(0);
  const ret60 = ((m.ret_60d ?? 0) * 100).toFixed(1);
  const trend = ((m.trend_12m ?? 0) * 100).toFixed(1);
  const ret60Num = m.ret_60d ?? 0;
  const trendNum = m.trend_12m ?? 0;
  const isProxy = item.is_proxy;

  return (
    <div className={`rounded-lg border border-slate-800 bg-slate-950/40 p-3 ring-1 ${style.ring}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold ${style.bg} ${style.text}`}>
              <Icon size={10} />
              {style.label}
            </span>
            {item.regime_change && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/15 text-yellow-300 ring-1 ring-yellow-500/30">NEW</span>
            )}
            {isProxy && (
              <span className="text-[10px] text-slate-500" title="ETF 프록시 — equity beta 영향">proxy</span>
            )}
          </div>
          <div className="text-sm font-medium text-slate-200 truncate">{item.name}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {item.previous_regime
              ? `${item.previous_regime} (${item.previous_regime_days ?? 0}일) → 오늘`
              : `${item.days_in_zone ?? 0}일 유지`}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs text-slate-400">5y {pct5y}%</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-1 mt-2 text-[11px]">
        <div className="text-slate-500">
          60d
          <div className={ret60Num >= 0 ? "text-emerald-300" : "text-rose-300"}>
            {ret60Num >= 0 ? "+" : ""}{ret60}%
          </div>
        </div>
        <div className="text-slate-500">
          trend 12m
          <div className={trendNum >= 0 ? "text-emerald-300" : "text-rose-300"}>
            {trendNum >= 0 ? "+" : ""}{trend}%
          </div>
        </div>
        <div className="text-slate-500">
          vol z
          <div className="text-slate-300">{(m.vol_z ?? 0).toFixed(1)}</div>
        </div>
      </div>

      {item.recommendation && (
        <div className="mt-2 pt-2 border-t border-slate-800 text-[11px]">
          <span className={`font-semibold ${style.text}`}>{item.recommendation}</span>
          <span className="text-slate-500"> — {item.recommendation_note}</span>
        </div>
      )}
    </div>
  );
}

function xPriority(item: CommodityFeedItem) {
  if (item.is_surge) return 4;
  if (item.is_multi_month_uptrend) return 3;
  if (item.is_plunge) return 2;
  return 1;
}

// ─────────────────────────────────────────────
// 전체 원자재 섹션 (53개 모두 + 카테고리별 그룹 + 인라인 차트)
// ─────────────────────────────────────────────
function AllCommoditiesSection({
  feed,
  regimeMap,
  onSelect,
}: {
  feed: CommodityFeedItem[];
  regimeMap: Map<string, RegimeItem>;
  onSelect: (item: CommodityFeedItem) => void;
}) {
  const grouped = useMemo(() => {
    const map = new Map<string, CommodityFeedItem[]>();
    feed.forEach((item) => {
      const key = item.category || "기타";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(item);
    });
    return Array.from(map.entries());
  }, [feed]);

  return (
    <section className="mt-6">
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BarChart3 size={18} className="text-sky-300" />
          <h3 className="text-sm font-semibold text-slate-200">전체 원자재 ({feed.length}개)</h3>
          <span className="text-xs text-slate-400">카테고리별 그룹 · 클릭 시 상세 모달</span>
        </div>
      </header>

      <div className="space-y-4">
        {grouped.map(([category, items]) => (
          <div key={category}>
            <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <span className="text-slate-100">{category}</span>
              <span className="text-slate-500">({items.length})</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
              {items.map((item) => (
                <CommodityRowCard
                  key={item.id}
                  item={item}
                  regime={regimeMap.get(item.id)}
                  onClick={() => onSelect(item)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CommodityRowCard({
  item,
  regime,
  onClick,
}: {
  item: CommodityFeedItem;
  regime?: RegimeItem;
  onClick: () => void;
}) {
  const change = item.change_pct_60d ?? item.change_pct_20d ?? item.change_pct_5d ?? 0;
  const changeColor = change >= 0 ? "text-emerald-400" : "text-rose-400";
  const isHidden = item.is_hidden_bottleneck;
  const regimeStyle = regime ? REGIME_STYLE[regime.current_regime] : null;

  return (
    <button
      onClick={onClick}
      className="text-left rounded-lg border border-slate-800 bg-slate-950/40 p-2.5 hover:border-slate-600 hover:bg-slate-900/50 transition group"
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-slate-200 truncate">{item.name}</div>
          <div className="text-[10px] text-slate-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
            <span>{item.unit}</span>
            {item.ticker && <span className="font-mono text-slate-600">{item.ticker}</span>}
            {isHidden && <span className="text-amber-500" title="시장 저평가 hidden bottleneck">★</span>}
            {item.is_proxy && <span className="text-slate-600" title="ETF/proxy 데이터">proxy</span>}
            {regimeStyle && (
              <span className={`px-1 rounded text-[9px] font-semibold ${regimeStyle.bg} ${regimeStyle.text}`}>
                {regimeStyle.label}
              </span>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className={`text-xs font-semibold ${changeColor}`}>
            {change >= 0 ? "+" : ""}{change.toFixed(1)}%
          </div>
          <div className="text-[9px] text-slate-500">60d</div>
        </div>
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="text-[10px] text-slate-500">
          {item.price ? (
            <>가격 <span className="text-slate-300 font-mono">{item.price.toLocaleString(undefined, { maximumFractionDigits: 4 })}</span></>
          ) : (
            <span className="text-slate-600">가격 미수집</span>
          )}
        </div>
        <Sparkline ticker={item.ticker} width={100} height={28} period="3mo" />
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────
// 섹터별 영향 섹션 (원자재 → 어떤 섹터에 영향)
// ─────────────────────────────────────────────
function SectorImpactSection({
  feed,
  onSelect,
}: {
  feed: CommodityFeedItem[];
  onSelect: (item: CommodityFeedItem) => void;
}) {
  // 섹터 → 그 섹터에 영향 주는 원자재들 매핑
  const sectorMap = useMemo(() => {
    const map = new Map<string, { effect: string; commodities: CommodityFeedItem[] }>();
    feed.forEach((item) => {
      const cat = item.category || "기타";
      const sectors = CATEGORY_TO_SECTORS[cat] ?? [];
      sectors.forEach(({ sector, effect }) => {
        if (!map.has(sector)) {
          map.set(sector, { effect, commodities: [] });
        }
        map.get(sector)!.commodities.push(item);
      });
    });
    return Array.from(map.entries()).sort((a, b) => b[1].commodities.length - a[1].commodities.length);
  }, [feed]);

  return (
    <section className="mt-6 mb-4">
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target size={18} className="text-amber-300" />
          <h3 className="text-sm font-semibold text-slate-200">섹터별 영향 매핑</h3>
          <span className="text-xs text-slate-400">원자재 → 가장 영향받는 산업 (wiki/macro/01-commodities.md 기반)</span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {sectorMap.map(([sector, { effect, commodities }]) => (
          <div key={sector} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-slate-200">{sector}</h4>
              <span className="text-[10px] text-slate-500">{commodities.length}개 원자재</span>
            </div>
            <p className="text-[11px] text-slate-400 mb-2 leading-snug">{effect}</p>
            <div className="space-y-1">
              {commodities
                .sort((a, b) => Math.abs(b.change_pct_60d ?? 0) - Math.abs(a.change_pct_60d ?? 0))
                .slice(0, 8)
                .map((item) => {
                  const change = item.change_pct_60d ?? 0;
                  const changeColor = change >= 0 ? "text-emerald-400" : "text-rose-400";
                  return (
                    <button
                      key={item.id}
                      onClick={() => onSelect(item)}
                      className="w-full flex items-center justify-between gap-2 px-2 py-1 rounded hover:bg-slate-900/50 transition text-left"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs text-slate-300 truncate">{item.name}</span>
                        {item.is_hidden_bottleneck && <span className="text-[9px] text-amber-500">★</span>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Sparkline ticker={item.ticker} width={50} height={16} period="3mo" />
                        <span className={`text-[11px] font-semibold tabular-nums ${changeColor} w-12 text-right`}>
                          {change >= 0 ? "+" : ""}{change.toFixed(1)}%
                        </span>
                      </div>
                    </button>
                  );
                })}
              {commodities.length > 8 && (
                <div className="text-[10px] text-slate-600 text-center pt-1">+{commodities.length - 8}개 더</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function SignalPanel({
  title,
  icon,
  tone,
  items,
  empty,
  onSelect,
}: {
  title: string;
  icon: React.ReactNode;
  tone: "green" | "red" | "blue";
  items: CommodityFeedItem[];
  empty: string;
  onSelect: (item: CommodityFeedItem) => void;
}) {
  const styles = {
    green: "border-[#10b981]/40 bg-gradient-to-br from-[#10b981]/15 to-transparent text-[#10b981]",
    red: "border-[#ef4444]/40 bg-gradient-to-br from-[#ef4444]/15 to-transparent text-[#ef4444]",
    blue: "border-[#3b82f6]/40 bg-gradient-to-br from-[#3b82f6]/15 to-transparent text-[#3b82f6]",
  }[tone];

  return (
    <div className={`rounded-xl border p-4 min-h-[520px] ${styles}`}>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      <div className="space-y-2">
        {items.length ? items.map((item) => (
          <button
            key={item.id}
            onClick={() => onSelect(item)}
            className="w-full text-left flex items-center justify-between gap-3 py-2.5 px-3 rounded bg-black/20 hover:bg-black/30 transition-colors"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{item.name}</span>
                <span className="text-[10px] text-[var(--color-text-muted)]">{item.category}</span>
              </div>
              <div className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 truncate">
                {item.driver_label ?? shortReason(item)}
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className={`text-sm font-bold ${pctColor(item.change_pct_1d)}`}>
                {fmtPct(item.change_pct_1d)}
              </div>
              <div className="text-[10px] text-[var(--color-text-muted)]">
                {item.change_pct_60d != null ? `3개월 ${fmtPct(item.change_pct_60d)}` : item.coverage_status}
              </div>
            </div>
          </button>
        )) : (
          <div className="text-xs text-[var(--color-text-muted)] italic">{empty}</div>
        )}
      </div>
    </div>
  );
}

function CommodityModal({ item, onClose }: { item: CommodityFeedItem; onClose: () => void }) {
  const reasons = [
    ...(item.timing_reasons ?? []),
    ...(item.trend_reasons ?? []),
    ...(item.surge_reasons ?? []),
    ...(item.risk_notes ?? []),
  ];
  const causeList = item.cause_reasons ?? [causeText(item)];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-6xl max-h-[92vh] overflow-y-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-primary)] shadow-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">{item.name}</h2>
              <TimingBadge action={item.timing_action} />
              <CoverageBadge item={item} />
            </div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">
              {item.category} · {item.ticker ?? item.source} · 신뢰도 {item.confidence ?? "—"}% · 기준일 {item.data_as_of?.slice(0, 10) ?? "—"}
            </div>
          </div>
          <button onClick={onClose} className="rounded-md p-2 text-[var(--color-text-muted)] hover:bg-white/10 hover:text-white">
            <X size={18} />
          </button>
        </div>

        <div className="p-4 grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
          <div>
            {item.chartable && item.ticker ? (
              <ChartView ticker={item.ticker} />
            ) : (
              <div className="rounded-xl border border-[var(--color-border)] bg-black/20 p-8 text-center">
                <BarChart3 size={28} className="mx-auto mb-2 text-[var(--color-text-muted)]" />
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">차트용 공개 가격 제한</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">{item.note}</div>
              </div>
            )}
          </div>

          <aside className="space-y-3">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <div className="text-xs font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-1.5">
                <Activity size={13} /> 매매 판정
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <Metric label="1일" value={item.change_pct_1d} />
                <Metric label="5일" value={item.change_pct_5d} />
                <Metric label="1개월" value={item.change_pct_20d} />
                <Metric label="3개월" value={item.change_pct_60d} />
                <Metric label="6개월" value={item.change_pct_120d} />
                <Metric label="Z" value={item.zscore_60d} suffix="" />
              </div>
              <div className="space-y-1">
                {reasons.length ? reasons.slice(0, 7).map((r, i) => (
                  <div key={i} className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">· {r}</div>
                )) : (
                  <div className="text-[11px] text-[var(--color-text-muted)]">뚜렷한 정량 신호 없음</div>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-[#fbbf24]/30 bg-[#fbbf24]/5 p-3">
              <div className="text-xs font-semibold text-[#fbbf24] mb-2 flex items-center gap-1.5">
                <AlertTriangle size={13} /> 왜 움직이나
              </div>
              <div className="text-[11px] font-semibold text-[var(--color-text-primary)] mb-1">{item.driver_label ?? "원인 분석"}</div>
              <div className="space-y-1">
                {causeList.slice(0, 6).map((cause, i) => (
                  <p key={i} className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">· {cause}</p>
                ))}
              </div>
              {item.proxy_for && (
                <p className="text-[10px] text-[var(--color-text-muted)] mt-2">직접 가격 대신 {item.proxy_for} proxy 사용</p>
              )}
            </div>

            <div className="rounded-lg border border-[#10b981]/25 bg-[#10b981]/5 p-3">
              <div className="text-xs font-semibold text-[#10b981] mb-1">상승 지속 조건</div>
              <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{item.bullish_thesis ?? "수요 증가와 공급 병목이 동시에 확인될 때만 지속성이 높다."}</p>
            </div>

            <div className="rounded-lg border border-[#ef4444]/25 bg-[#ef4444]/5 p-3">
              <div className="text-xs font-semibold text-[#ef4444] mb-1">주의/깨지는 조건</div>
              <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{item.caution ?? "proxy 기반 신호는 실제 원자재 가격과 괴리가 날 수 있다."}</p>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <div className="text-xs font-semibold text-[var(--color-text-primary)] mb-2">데이터 소스</div>
              <div className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
                {item.source ?? "—"} · {item.frequency ?? "—"} · {item.coverage_status ?? "—"}
              </div>
              {item.source_url && (
                <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-2 text-[11px] text-[#93c5fd] hover:underline">
                  원본 확인 <ExternalLink size={11} />
                </a>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function shortReason(item: CommodityFeedItem) {
  return item.driver_label
    ?? item.timing_reasons?.[0]
    ?? item.trend_reasons?.[0]
    ?? item.surge_reasons?.[0]
    ?? item.risk_notes?.[0]
    ?? item.note
    ?? item.timing_action
    ?? "신호 확인";
}

function causeText(item: CommodityFeedItem) {
  if (item.note && item.coverage_status !== "live") return item.note;
  if (item.id.includes("crude") || item.id.includes("natgas") || item.id.includes("coal")) {
    return "에너지 원자재는 지정학, 재고, 운송 병목, 날씨, 달러와 금리 기대가 같이 움직입니다. 최근 급등은 공급 차질/전쟁 리스크 또는 수요 회복 기대를 먼저 의심해야 합니다.";
  }
  if (["gold", "silver", "platinum", "palladium", "rhodium"].includes(item.id)) {
    return "귀금속은 달러, 실질금리, 안전자산 수요, 산업 수요가 핵심입니다. 금은 위험회피와 금리 기대, 백금/팔라듐/로듐은 자동차 촉매와 공급 차질 영향이 큽니다.";
  }
  if (item.category.includes("산업금속") || item.category.includes("희소금속")) {
    return "산업금속과 희소금속은 중국 수요, 재고, 광산 공급, 수출통제, AI 전력망/EV/방산 수요가 핵심 원인입니다. 중기 상승이면 공급망 병목 또는 capex 사이클을 같이 봐야 합니다.";
  }
  if (item.category.includes("농산물")) {
    return "농산물은 날씨, 작황, USDA 수급 전망, 운송, 달러가 핵심입니다. 단기 급등은 기상 리스크나 수출 제한 뉴스와 교차 확인해야 합니다.";
  }
  if (item.category.includes("화학")) {
    return "화학원료는 천연가스/석탄 같은 원료비, 중국 가동률, 비료·배터리·산업 수요가 원인입니다. proxy 종목으로 볼 때는 실제 spot과 괴리가 날 수 있습니다.";
  }
  return "가격 공개가 제한된 원자재는 spot 가격보다 공급 이벤트, 수출통제, 재고, 관련 기업 proxy를 같이 봐야 합니다.";
}

function TimingBadge({ action }: { action?: string }) {
  const cls =
    action === "분할 매수 관심" ? "bg-[#10b981]/15 text-[#6ee7b7] border-[#10b981]/30" :
    action === "눌림 매수 후보" ? "bg-[#22c55e]/10 text-[#86efac] border-[#22c55e]/25" :
    action === "추격 금지" ? "bg-[#f59e0b]/15 text-[#fcd34d] border-[#f59e0b]/30" :
    action === "매도·회피" ? "bg-[#ef4444]/15 text-[#fca5a5] border-[#ef4444]/30" :
    "bg-white/5 text-[var(--color-text-muted)] border-white/10";
  return <span className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-semibold ${cls}`}>{action ?? "관망"}</span>;
}

function CoverageBadge({ item }: { item: CommodityFeedItem }) {
  const status = item.coverage_status ?? "live";
  const label =
    status === "live" ? "live" :
    status === "proxy" ? "proxy" :
    status === "computed_proxy" ? "계산" :
    status === "monthly" ? "월간" :
    status === "delayed" ? "지연" :
    status === "unavailable" ? "제한" : status;
  const cls =
    status === "live" ? "bg-[#10b981]/15 text-[#6ee7b7] border-[#10b981]/30" :
    status === "proxy" || status === "computed_proxy" ? "bg-[#3b82f6]/15 text-[#93c5fd] border-[#3b82f6]/30" :
    status === "monthly" || status === "delayed" ? "bg-[#f59e0b]/15 text-[#fcd34d] border-[#f59e0b]/30" :
    "bg-[#ef4444]/15 text-[#fca5a5] border-[#ef4444]/30";
  return <span className={`inline-flex rounded border px-1.5 py-0.5 text-[9px] font-semibold ${cls}`}>{label}</span>;
}

function Metric({ label, value, suffix = "%" }: { label: string; value: number | null | undefined; suffix?: string }) {
  return (
    <div className="rounded-md border border-[var(--color-border)] bg-black/20 p-2">
      <div className="text-[10px] text-[var(--color-text-muted)]">{label}</div>
      <div className={`text-sm font-bold ${pctColor(value)}`}>{fmtPct(value, suffix)}</div>
    </div>
  );
}

function fmtPct(value: number | null | undefined, suffix = "%") {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value}${suffix}`;
}

function pctColor(value: number | null | undefined) {
  if (value == null) return "text-[var(--color-text-muted)]";
  if (value > 0) return "text-[#ef4444]";
  if (value < 0) return "text-[#3b82f6]";
  return "text-[var(--color-text-muted)]";
}
