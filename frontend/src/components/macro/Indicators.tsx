// 선행 지표 페이지 — 섹터별 라이브 sentiment + 명세 기반 카드
import { useEffect, useMemo, useState } from "react";
import { Activity, Filter, TrendingUp, TrendingDown, Minus } from "lucide-react";
import MacroLayout from "./MacroLayout";
import WikiMarkdown from "./WikiMarkdown";
import { fetchIndicators, fetchWikiPage } from "@/api/macro";
import type { IndicatorsResponse, WikiPageResponse, SectorMeta, SectorSentiment } from "@/types/macro";

export default function Indicators() {
  const [data, setData] = useState<IndicatorsResponse | null>(null);
  const [wiki, setWiki] = useState<WikiPageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [phaseFilter, setPhaseFilter] = useState<"all" | 1 | 2>("all");
  const [sentimentFilter, setSentimentFilter] = useState<"all" | "bullish" | "bearish">("all");
  const [showFullSpec, setShowFullSpec] = useState(false);

  useEffect(() => {
    Promise.all([fetchIndicators(), fetchWikiPage("indicators")])
      .then(([d, w]) => { setData(d); setWiki(w); })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const visibleSectors = useMemo(() => {
    if (!data) return [];
    return data.sectors.filter((s) => {
      if (phaseFilter !== "all" && s.phase !== phaseFilter) return false;
      const sent = s.live_sentiment?.sentiment ?? "neutral";
      if (sentimentFilter !== "all" && sent !== sentimentFilter) return false;
      return true;
    });
  }, [data, phaseFilter, sentimentFilter]);

  const counts = useMemo(() => {
    if (!data) return { bullish: 0, neutral: 0, bearish: 0 };
    let b = 0, n = 0, r = 0;
    for (const s of data.sectors) {
      const t = s.live_sentiment?.sentiment ?? "neutral";
      if (t === "bullish") b++;
      else if (t === "bearish") r++;
      else n++;
    }
    return { bullish: b, neutral: n, bearish: r };
  }, [data]);

  if (loading) return <MacroLayout title="선행 지표" subtitle="섹터별 sentiment 계산 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="선행 지표" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  const top = data.top_sectors;

  return (
    <MacroLayout
      title="선행 지표 매트릭스"
      subtitle={`${data.total_sectors}개 섹터 × ${data.total_indicators}개 지표 · 라이브 sentiment ${counts.bullish + counts.bearish}/${data.total_sectors}`}
    >
      {/* 직접 원가/수요 신호 */}
      {top && (top.bullish_sectors.length > 0 || top.bearish_sectors.length > 0) && (
        <section className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-3">
          {top.bullish_sectors.length > 0 && (
            <div className="rounded-xl border border-[#10b981]/40 bg-gradient-to-br from-[#10b981]/15 to-transparent p-4">
              <div className="flex items-center gap-2 mb-3 text-[#10b981]">
                <TrendingUp size={18} />
                <h3 className="text-sm font-semibold">직접 호재 신호 TOP {top.bullish_sectors.length}</h3>
              </div>
              <div className="space-y-2.5">
                {top.bullish_sectors.map((s) => (
                  <TopSectorRow key={s.sector_id} sentiment={s} sectors={data.sectors} kind="bullish" />
                ))}
              </div>
            </div>
          )}
          {top.bearish_sectors.length > 0 && (
            <div className="rounded-xl border border-[#ef4444]/40 bg-gradient-to-br from-[#ef4444]/15 to-transparent p-4">
              <div className="flex items-center gap-2 mb-3 text-[#ef4444]">
                <TrendingDown size={18} />
                <h3 className="text-sm font-semibold">직접 부담 신호 TOP {top.bearish_sectors.length}</h3>
              </div>
              <div className="space-y-2.5">
                {top.bearish_sectors.map((s) => (
                  <TopSectorRow key={s.sector_id} sentiment={s} sectors={data.sectors} kind="bearish" />
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
          <Activity size={14} /> 섹터별 핵심 체크 지표
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {data.sectors.slice(0, 12).map((s) => (
            <div key={s.id} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">{s.name}</div>
                <span className="text-[10px] text-[#fbbf24]">{s.indicator_count}개 지표</span>
              </div>
              <div className="space-y-1">
                {(s.live_sentiment?.watch_signals ?? []).slice(0, 3).map((w, i) => (
                  <div key={i} className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">· {w}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 핵심 선행 지표 */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
          <Activity size={14} /> 핵심 선행 지표 (즉시 활용)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.featured.filter((i) => i.is_top_signal).map((ind) => (
            <div key={ind.id} className="rounded-lg border border-[#3b82f6]/30 bg-[#3b82f6]/5 p-3.5">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] uppercase tracking-wider text-[#93c5fd] font-semibold">{ind.sector_name}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#3b82f6]/20 text-[#93c5fd] font-semibold">TOP</span>
              </div>
              <div className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">{ind.name}</div>
              <p className="text-[11px] text-[var(--color-text-secondary)] mb-1.5 leading-relaxed">{ind.what}</p>
              <p className="text-[11px] text-[#fbbf24] mb-2">⏱ {ind.lead_time}</p>
              <div className="flex flex-wrap gap-1 mb-1.5">
                {ind.tickers_kr.slice(0, 3).map((t) => <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-[#3b82f6]/15 text-[#93c5fd]">{t}</span>)}
                {ind.tickers_us.slice(0, 3).map((t) => <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#6ee7b7]">{t}</span>)}
              </div>
              {ind.source.url && (
                <a href={ind.source.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#3b82f6] hover:underline">
                  → {ind.source.name}
                </a>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 27개 섹터 그리드 + 필터 */}
      <section className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <Filter size={14} /> 27개 섹터 (라이브 sentiment)
          </h2>
          <div className="flex flex-wrap gap-1">
            <span className="text-[10px] text-[var(--color-text-muted)] mr-2 self-center">Phase</span>
            {(["all", 1, 2] as const).map((p) => (
              <button key={p} onClick={() => setPhaseFilter(p)}
                className={`text-[10px] px-2 py-1 rounded ${phaseFilter === p ? "bg-[#3b82f6] text-white" : "bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10"}`}>
                {p === "all" ? "전체" : `${p}`}
              </button>
            ))}
            <span className="text-[10px] text-[var(--color-text-muted)] mx-2 self-center">·</span>
            {(["all", "bullish", "bearish"] as const).map((s) => (
              <button key={s} onClick={() => setSentimentFilter(s)}
                className={`text-[10px] px-2 py-1 rounded ${
                  sentimentFilter === s
                    ? s === "bullish" ? "bg-[#10b981] text-white"
                    : s === "bearish" ? "bg-[#ef4444] text-white"
                    : "bg-[#3b82f6] text-white"
                    : "bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10"
                }`}>
                {s === "all" ? `전체 ${counts.bullish + counts.neutral + counts.bearish}` : s === "bullish" ? `🚀 ${counts.bullish}` : `⚠️ ${counts.bearish}`}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {visibleSectors.map((s) => <SectorCard key={s.id} sector={s} />)}
        </div>
      </section>

      <section>
        <button
          onClick={() => setShowFullSpec((v) => !v)}
          className="text-xs px-3 py-1.5 rounded-md border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-white/5"
        >
          {showFullSpec ? "▼ 전체 명세 닫기" : "▶ 전체 명세 보기 (178개 지표 상세)"}
        </button>
        {showFullSpec && wiki && (
          <div className="mt-4 p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
            <WikiMarkdown content={wiki.content} />
          </div>
        )}
      </section>
    </MacroLayout>
  );
}

function SectorCard({ sector }: { sector: SectorMeta }) {
  const sent = sector.live_sentiment;
  const t = sent?.sentiment ?? "neutral";
  const score = sent?.score ?? 0;

  const styles =
    t === "bullish"
      ? "border-[#10b981]/50 bg-[#10b981]/10 hover:border-[#10b981]"
      : t === "bearish"
      ? "border-[#ef4444]/50 bg-[#ef4444]/10 hover:border-[#ef4444]"
      : "border-[var(--color-border)] bg-[var(--color-bg-secondary)] hover:border-[#3b82f6]/40";

  const Icon = t === "bullish" ? TrendingUp : t === "bearish" ? TrendingDown : Minus;
  const iconColor = t === "bullish" ? "text-[#10b981]" : t === "bearish" ? "text-[#ef4444]" : "text-[var(--color-text-muted)]";

  const allSignals = [
    ...(sent?.bullish_signals ?? []).map((s) => ({ kind: "+", text: s })),
    ...(sent?.bearish_signals ?? []).map((s) => ({ kind: "-", text: s })),
  ];
  const watchSignals = sent?.watch_signals ?? [];

  return (
    <div className={`rounded-md border p-2.5 transition-colors ${styles}`}>
      <div className="flex items-start justify-between mb-1">
        <div className="text-[12px] font-semibold text-[var(--color-text-primary)] truncate flex-1">{sector.name}</div>
        <Icon size={12} className={`${iconColor} shrink-0 ml-1`} />
      </div>
      <div className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)] mb-1.5">
        <span>P{sector.phase}</span>
        <span>·</span>
        <span className="text-[#fbbf24]">{sector.indicator_count}개</span>
        {score !== 0 && (
          <>
            <span>·</span>
            <span className={iconColor}>{score > 0 ? `+${score}` : score}</span>
          </>
        )}
      </div>
      {allSignals.length > 0 ? (
        <div className="space-y-0.5">
          {allSignals.slice(0, 2).map((s, i) => (
            <div key={i} className={`text-[10px] leading-tight truncate ${s.kind === "+" ? "text-[#6ee7b7]" : "text-[#fca5a5]"}`}>
              {s.kind} {s.text}
            </div>
          ))}
          {allSignals.length > 2 && (
            <div className="text-[9px] text-[var(--color-text-muted)]">+{allSignals.length - 2}개</div>
          )}
        </div>
      ) : (
        <div className="space-y-0.5">
          {watchSignals.slice(0, 2).map((w, i) => (
            <div key={i} className="text-[10px] leading-tight truncate text-[var(--color-text-secondary)]">· {w}</div>
          ))}
          {watchSignals.length === 0 && (
            <div className="text-[10px] text-[var(--color-text-muted)] italic">신호 없음 (중립)</div>
          )}
        </div>
      )}
    </div>
  );
}

function TopSectorRow({ sentiment, sectors, kind }: {
  sentiment: SectorSentiment;
  sectors: SectorMeta[];
  kind: "bullish" | "bearish";
}) {
  const sec = sectors.find((s) => s.id === sentiment.sector_id);
  const color = kind === "bullish" ? "#10b981" : "#ef4444";
  const signals = kind === "bullish" ? sentiment.bullish_signals : sentiment.bearish_signals;

  return (
    <div className="rounded bg-black/20 p-2.5">
      <div className="flex items-center justify-between mb-1">
        <div className="text-sm font-semibold text-[var(--color-text-primary)]">{sec?.name ?? sentiment.sector_id}</div>
        <div className="flex items-center gap-1.5 text-[10px]">
          <span style={{ color }} className="font-bold">
            {sentiment.score > 0 ? `+${sentiment.score}` : sentiment.score}
          </span>
          <span className="text-[var(--color-text-muted)]">·</span>
          <span className="text-[var(--color-text-muted)]">{sec?.indicator_count}지표</span>
        </div>
      </div>
      <div className="space-y-0.5">
        {signals.map((s, i) => (
          <div key={i} className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
            {kind === "bullish" ? "+" : "−"} {s}
          </div>
        ))}
      </div>
    </div>
  );
}
