import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, ExternalLink, Filter, X } from "lucide-react";
import MacroLayout from "./MacroLayout";
import ChartView from "@/components/ChartView";
import { fetchCommodities } from "@/api/macro";
import type { CommoditiesResponse, CommodityFeedItem } from "@/types/macro";
import Sparkline from "./Sparkline";

type PeriodKey = "1d" | "5d" | "10d" | "1m" | "3m" | "6m";

const PERIODS: { key: PeriodKey; label: string; field: keyof CommodityFeedItem; spark: string }[] = [
  { key: "1d", label: "1일", field: "change_pct_1d", spark: "1mo" },
  { key: "5d", label: "5일", field: "change_pct_5d", spark: "1mo" },
  { key: "10d", label: "10일", field: "change_pct_10d", spark: "1mo" },
  { key: "1m", label: "1개월", field: "change_pct_20d", spark: "3mo" },
  { key: "3m", label: "3개월", field: "change_pct_60d", spark: "6mo" },
  { key: "6m", label: "6개월", field: "change_pct_120d", spark: "1y" },
];

const CATEGORY_TO_USE: Record<string, string> = {
  "에너지": "발전, 운송, 정유, LNG, 전력가격",
  "산업금속": "전력망, 건설, 조선, 데이터센터, 전기차",
  "귀금속": "안전자산, 촉매, 전장, 태양광, 반도체 소재",
  "희소금속": "배터리, 전력반도체, 영구자석, 방산 공급망",
  "반도체 가스": "EUV/DUV 노광, 식각, 반도체 특수가스",
  "양자/방산 특수재": "우주항공, 방산, 양자/극저온 장비",
  "농산물": "식품 원가, 사료, 바이오연료, 작황/날씨",
  "화학원료": "비료, 배터리 가공, 산업화학, downstream 원가",
  "바이오 원료": "CDMO, 의약품 원료, 의료 소모품",
};

export default function Commodities() {
  const [data, setData] = useState<CommoditiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<CommodityFeedItem | null>(null);
  const [period, setPeriod] = useState<PeriodKey>("3m");
  const [category, setCategory] = useState("전체");
  const [direction, setDirection] = useState<"all" | "up" | "down">("all");

  useEffect(() => {
    fetchCommodities()
      .then(setData)
      .catch((e) => console.error("commodities", e))
      .finally(() => setLoading(false));
  }, []);

  const selectedPeriod = PERIODS.find((p) => p.key === period) ?? PERIODS[4];
  const categories = useMemo(() => ["전체", ...Array.from(new Set((data?.feed ?? []).map((x) => x.category || "기타")))], [data]);

  const visible = useMemo(() => {
    const field = selectedPeriod.field;
    return [...(data?.feed ?? [])]
      .filter((item) => category === "전체" || item.category === category)
      .filter((item) => {
        const value = Number(item[field] ?? 0);
        if (direction === "up") return value > 0;
        if (direction === "down") return value < 0;
        return true;
      })
      .sort((a, b) => Number(b[field] ?? -9999) - Number(a[field] ?? -9999));
  }, [data, category, direction, selectedPeriod.field]);

  if (loading) return <MacroLayout title="원자재 모니터링" subtitle="실시간 가격 업데이트 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="원자재 모니터링" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  const liveCount = data.feed.filter((f) => f.coverage_status === "live").length;
  const proxyCount = data.feed.filter((f) => f.coverage_status === "proxy" || f.coverage_status === "computed_proxy").length;
  const delayedCount = data.feed.filter((f) => ["delayed", "monthly", "stale_fallback"].includes(f.coverage_status ?? "")).length;

  return (
    <MacroLayout
      title="원자재 모니터링"
      subtitle={`${data.feed.length}개 추적 · live ${liveCount} · proxy/계산 ${proxyCount} · 지연/월간 ${delayedCount}`}
    >
      <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <header className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-sky-300" />
            <h3 className="text-sm font-semibold text-slate-200">전체 원자재</h3>
            <span className="text-xs text-slate-500">기간별 상승률 정렬 · 클릭 시 차트/용도/원인</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Filter size={14} className="text-slate-500" />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-200"
            >
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as "all" | "up" | "down")}
              className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-200"
            >
              <option value="all">전체 방향</option>
              <option value="up">상승만</option>
              <option value="down">하락만</option>
            </select>
          </div>
        </header>

        <div className="flex flex-wrap gap-1.5 mb-4">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${
                period === p.key
                  ? "border-[#3b82f6] bg-[#3b82f6]/20 text-[#93c5fd]"
                  : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-600"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] border-separate border-spacing-y-1">
            <thead>
              <tr className="text-[10px] uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2 text-left font-semibold">원자재</th>
                <th className="px-3 py-2 text-left font-semibold">용도</th>
                <th className="px-3 py-2 text-right font-semibold">가격</th>
                <th className="px-3 py-2 text-right font-semibold">{selectedPeriod.label}</th>
                <th className="px-3 py-2 text-left font-semibold">방향성 이유</th>
                <th className="px-3 py-2 text-left font-semibold">차트</th>
                <th className="px-3 py-2 text-left font-semibold">신뢰도</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <CommodityTableRow
                  key={item.id}
                  item={item}
                  period={selectedPeriod}
                  onClick={() => setSelected(item)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {selected && <CommodityModal item={selected} period={selectedPeriod} onClose={() => setSelected(null)} />}
    </MacroLayout>
  );
}

function CommodityTableRow({
  item,
  period,
  onClick,
}: {
  item: CommodityFeedItem;
  period: (typeof PERIODS)[number];
  onClick: () => void;
}) {
  const value = Number(item[period.field] ?? 0);
  const use = CATEGORY_TO_USE[item.category] ?? item.note ?? "공급망/수요 proxy";
  return (
    <tr>
      <td colSpan={7} className="p-0">
        <button
          onClick={onClick}
          className="grid w-full grid-cols-[220px_210px_110px_110px_1fr_120px_110px] items-center rounded-lg border border-slate-800 bg-slate-950/55 px-3 py-2.5 text-left hover:border-slate-600 hover:bg-slate-900/70"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-[13px] font-semibold text-slate-200">{item.name}</span>
              {item.is_hidden_bottleneck && <span className="text-amber-400">★</span>}
            </div>
            <div className="mt-0.5 flex flex-wrap gap-1.5 text-[10px] text-slate-500">
              <span>{item.category}</span>
              {item.ticker && <span className="font-mono">{item.ticker}</span>}
              {item.is_proxy && <span>proxy</span>}
            </div>
          </div>
          <div className="truncate pr-3 text-[11px] text-slate-400">{use}</div>
          <div className="text-right text-[12px] font-mono text-slate-300">
            {item.price != null ? item.price.toLocaleString(undefined, { maximumFractionDigits: 4 }) : "—"}
          </div>
          <div className={`text-right text-sm font-bold ${pctColor(value)}`}>{fmtPct(value)}</div>
          <div className="truncate px-3 text-[11px] text-slate-400">{item.driver_label ?? shortReason(item)}</div>
          <div><Sparkline ticker={item.ticker} dataOverride={item.chart_series} width={96} height={26} period={period.spark} /></div>
          <div className="flex items-center justify-end gap-1.5">
            <CoverageBadge item={item} />
            <span className="text-[10px] text-slate-500">{item.confidence ?? "—"}%</span>
          </div>
        </button>
      </td>
    </tr>
  );
}

function CommodityModal({
  item,
  period,
  onClose,
}: {
  item: CommodityFeedItem;
  period: (typeof PERIODS)[number];
  onClose: () => void;
}) {
  const reasons = [
    ...(item.cause_reasons ?? []),
    ...(item.timing_reasons ?? []),
    ...(item.trend_reasons ?? []),
    ...(item.surge_reasons ?? []),
    ...(item.risk_notes ?? []),
  ];
  const periodValue = Number(item[period.field] ?? 0);
  const use = CATEGORY_TO_USE[item.category] ?? item.note ?? "공급망/수요 proxy";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-primary)] shadow-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">{item.name}</h2>
              <CoverageBadge item={item} />
              <span className={`rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold ${pctColor(periodValue)}`}>
                {period.label} {fmtPct(periodValue)}
              </span>
            </div>
            <div className="mt-1 text-xs text-[var(--color-text-muted)]">
              {item.category} · {item.ticker ?? item.source} · 신뢰도 {item.confidence ?? "—"}% · 기준일 {item.data_as_of?.slice(0, 10) ?? "—"}
            </div>
          </div>
          <button onClick={onClose} className="rounded-md p-2 text-[var(--color-text-muted)] hover:bg-white/10 hover:text-white">
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 p-4 xl:grid-cols-[1fr_380px]">
          <div>
            {item.chart_series?.length ? (
              <div className="rounded-xl border border-[var(--color-border)] bg-black/20 p-4">
                <div className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">계산 시계열</div>
                <Sparkline ticker={item.ticker} dataOverride={item.chart_series} width={720} height={260} period={period.spark} />
              </div>
            ) : item.chartable && item.ticker ? (
              <ChartView ticker={item.ticker} />
            ) : (
              <div className="rounded-xl border border-[var(--color-border)] bg-black/20 p-8 text-center">
                <BarChart3 size={28} className="mx-auto mb-2 text-[var(--color-text-muted)]" />
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">차트용 공개 가격 제한</div>
                <div className="mt-1 text-xs text-[var(--color-text-muted)]">{item.note}</div>
              </div>
            )}
          </div>

          <aside className="space-y-3">
            <InfoBox title="어디에 쓰이나" tone="blue">
              <p>{use}</p>
              {item.proxy_for && <p className="mt-1 text-[10px] text-slate-500">직접 가격 대신 {item.proxy_for} proxy 사용</p>}
            </InfoBox>

            {item.related_stocks_kr?.length ? (
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
                <div className="mb-2 text-xs font-semibold text-[var(--color-text-primary)]">국내 관련주</div>
                <div className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
                  {item.related_stocks_kr.map((stock) => (
                    <a
                      key={`${stock.ticker}-${stock.sector}`}
                      href={`/sector/ai_semi?stock=${encodeURIComponent(`${stock.ticker}.KS`)}`}
                      className="block rounded-md border border-slate-800 bg-black/20 px-2.5 py-2 hover:border-slate-600"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[12px] font-semibold text-slate-200">{stock.name}</span>
                        <span className="font-mono text-[10px] text-slate-500">{stock.ticker}</span>
                      </div>
                      <div className="mt-1 text-[10px] text-slate-500">{stock.sector} · {stock.direction}</div>
                      {stock.mechanism && <div className="mt-1 text-[10px] leading-relaxed text-slate-400">{stock.mechanism}</div>}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-[var(--color-text-primary)]">
                <Activity size={13} /> 기간별 움직임
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Metric label="1일" value={item.change_pct_1d} />
                <Metric label="5일" value={item.change_pct_5d} />
                <Metric label="10일" value={item.change_pct_10d} />
                <Metric label="1개월" value={item.change_pct_20d} />
                <Metric label="3개월" value={item.change_pct_60d} />
                <Metric label="6개월" value={item.change_pct_120d} />
              </div>
            </div>

            <InfoBox title="방향성이 왜 이런가" tone="amber">
              <div className="mb-1 font-semibold text-slate-200">{item.driver_label ?? "원인 분석"}</div>
              <div className="space-y-1">
                {reasons.length ? reasons.slice(0, 8).map((r, i) => <p key={i}>· {r}</p>) : <p>뚜렷한 정량 신호 없음</p>}
              </div>
            </InfoBox>

            <InfoBox title="상승 지속 조건" tone="green">
              <p>{item.bullish_thesis ?? "수요 증가와 공급 병목이 동시에 확인될 때만 지속성이 높다."}</p>
            </InfoBox>

            <InfoBox title="주의/깨지는 조건" tone="red">
              <p>{item.caution ?? "proxy 기반 신호는 실제 원자재 가격과 괴리가 날 수 있다."}</p>
            </InfoBox>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <div className="mb-2 text-xs font-semibold text-[var(--color-text-primary)]">데이터 소스</div>
              <div className="text-[11px] leading-relaxed text-[var(--color-text-secondary)]">
                {item.source ?? "—"} · {item.frequency ?? "—"} · {item.coverage_status ?? "—"}
              </div>
              {item.source_url && (
                <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-[11px] text-[#93c5fd] hover:underline">
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

function InfoBox({ title, tone, children }: { title: string; tone: "blue" | "amber" | "green" | "red"; children: React.ReactNode }) {
  const cls = {
    blue: "border-[#3b82f6]/25 bg-[#3b82f6]/5 text-[#93c5fd]",
    amber: "border-[#fbbf24]/30 bg-[#fbbf24]/5 text-[#fbbf24]",
    green: "border-[#10b981]/25 bg-[#10b981]/5 text-[#10b981]",
    red: "border-[#ef4444]/25 bg-[#ef4444]/5 text-[#ef4444]",
  }[tone];
  return (
    <div className={`rounded-lg border p-3 ${cls}`}>
      <div className="mb-1.5 text-xs font-semibold">{title}</div>
      <div className="text-[11px] leading-relaxed text-[var(--color-text-secondary)]">{children}</div>
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
