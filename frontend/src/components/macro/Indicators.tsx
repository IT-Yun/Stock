import { useEffect, useMemo, useState } from "react";
import { Filter, Minus, TrendingDown, TrendingUp, X } from "lucide-react";
import MacroLayout from "./MacroLayout";
import { fetchIndicators } from "@/api/macro";
import type { IndicatorsResponse, SectorMeta } from "@/types/macro";

function scoreColor(score: number) {
  if (score >= 6) return { bg: "bg-emerald-500/30", ring: "ring-emerald-400/60", text: "text-emerald-200", label: "매우 우호" };
  if (score >= 3) return { bg: "bg-emerald-500/18", ring: "ring-emerald-500/40", text: "text-emerald-300", label: "우호" };
  if (score >= 1) return { bg: "bg-emerald-500/8", ring: "ring-emerald-500/25", text: "text-emerald-400", label: "약우호" };
  if (score <= -6) return { bg: "bg-rose-500/30", ring: "ring-rose-400/60", text: "text-rose-200", label: "매우 부담" };
  if (score <= -3) return { bg: "bg-rose-500/18", ring: "ring-rose-500/40", text: "text-rose-300", label: "부담" };
  if (score <= -1) return { bg: "bg-rose-500/8", ring: "ring-rose-500/25", text: "text-rose-400", label: "약부담" };
  return { bg: "bg-slate-800/40", ring: "ring-slate-700", text: "text-slate-400", label: "중립" };
}

export default function Indicators() {
  const [data, setData] = useState<IndicatorsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [phaseFilter, setPhaseFilter] = useState<"all" | 1 | 2>("all");
  const [sentimentFilter, setSentimentFilter] = useState<"all" | "bullish" | "bearish" | "neutral">("all");
  const [selectedSector, setSelectedSector] = useState<SectorMeta | null>(null);

  useEffect(() => {
    fetchIndicators()
      .then(setData)
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
    return data.sectors.reduce((acc, s) => {
      const t = s.live_sentiment?.sentiment ?? "neutral";
      acc[t] += 1;
      return acc;
    }, { bullish: 0, neutral: 0, bearish: 0 });
  }, [data]);

  if (loading) return <MacroLayout title="선행 지표" subtitle="섹터별 sentiment 계산 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="선행 지표" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  return (
    <MacroLayout
      title="선행 지표 매트릭스"
      subtitle={`${data.total_sectors}개 섹터 × ${data.total_indicators}개 지표 · 각 지표 호재/악재 평가`}
    >
      <section className="mb-6">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
            <Filter size={14} /> 27개 섹터
          </h2>
          <div className="flex flex-wrap gap-1">
            <span className="mr-2 self-center text-[10px] text-[var(--color-text-muted)]">Phase</span>
            {(["all", 1, 2] as const).map((p) => (
              <button key={p} onClick={() => setPhaseFilter(p)}
                className={`rounded px-2 py-1 text-[10px] ${phaseFilter === p ? "bg-[#3b82f6] text-white" : "bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10"}`}>
                {p === "all" ? "전체" : `${p}`}
              </button>
            ))}
            <span className="mx-2 self-center text-[10px] text-[var(--color-text-muted)]">·</span>
            {(["all", "bullish", "neutral", "bearish"] as const).map((s) => (
              <button key={s} onClick={() => setSentimentFilter(s)}
                className={`rounded px-2 py-1 text-[10px] ${
                  sentimentFilter === s
                    ? s === "bullish" ? "bg-[#10b981] text-white"
                    : s === "bearish" ? "bg-[#ef4444] text-white"
                    : s === "neutral" ? "bg-slate-600 text-white"
                    : "bg-[#3b82f6] text-white"
                    : "bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10"
                }`}>
                {s === "all" ? `전체 ${data.total_sectors}` : s === "bullish" ? `호재 ${counts.bullish}` : s === "bearish" ? `악재 ${counts.bearish}` : `중립 ${counts.neutral}`}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {visibleSectors.map((s) => <SectorCard key={s.id} sector={s} onClick={() => setSelectedSector(s)} />)}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
          <span>강도 범례:</span>
          <span className="rounded bg-emerald-500/30 px-2 py-0.5 text-emerald-200">매우 우호 ≥+6</span>
          <span className="rounded bg-emerald-500/18 px-2 py-0.5 text-emerald-300">우호 +3</span>
          <span className="rounded bg-slate-800/40 px-2 py-0.5 text-slate-400">중립 0</span>
          <span className="rounded bg-rose-500/18 px-2 py-0.5 text-rose-300">부담 -3</span>
          <span className="rounded bg-rose-500/30 px-2 py-0.5 text-rose-200">매우 부담 ≤-6</span>
        </div>
      </section>

      {selectedSector && <SectorDetailModal sector={selectedSector} onClose={() => setSelectedSector(null)} />}
    </MacroLayout>
  );
}

function SectorCard({ sector, onClick }: { sector: SectorMeta; onClick: () => void }) {
  const sent = sector.live_sentiment;
  const score = sent?.score ?? 0;
  const bullish = sent?.bullish_count ?? 0;
  const bearish = sent?.bearish_count ?? 0;
  const total = Math.max(bullish + bearish, 1);
  const c = scoreColor(score);
  const Icon = score > 0 ? TrendingUp : score < 0 ? TrendingDown : Minus;
  const assessments = sent?.indicator_assessments ?? [];

  return (
    <button onClick={onClick} className={`w-full rounded-md p-2.5 text-left ring-1 transition ${c.bg} ${c.ring} hover:ring-2`}>
      <div className="mb-1 flex items-start justify-between gap-1.5">
        <div className="flex-1 truncate text-[12px] font-semibold text-[var(--color-text-primary)]">{sector.name}</div>
        <div className="flex shrink-0 items-center gap-1">
          <Icon size={11} className={c.text} />
          <span className={`text-[11px] font-bold tabular-nums ${c.text}`}>{score > 0 ? `+${score}` : score}</span>
        </div>
      </div>

      <div className="mb-1.5 flex h-1.5 overflow-hidden rounded-full bg-slate-900/60">
        {bullish > 0 && <div className="h-full bg-emerald-500/80" style={{ width: `${(bullish / total) * 100}%` }} />}
        {bearish > 0 && <div className="h-full bg-rose-500/80" style={{ width: `${(bearish / total) * 100}%` }} />}
      </div>

      <div className="mb-1.5 flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
        <span>P{sector.phase}</span>
        <span>·</span>
        <span className="text-[#fbbf24]">{sector.indicator_count}지표</span>
        <span>·</span>
        <span className={c.text}>{sent?.verdict ?? c.label}</span>
      </div>

      <div className="space-y-0.5">
        {assessments.slice(0, 3).map((a, i) => (
          <div key={i} className={`flex items-center gap-1 truncate text-[10px] leading-tight ${a.direction === "bullish" ? "text-emerald-300" : a.direction === "bearish" ? "text-rose-300" : "text-[var(--color-text-secondary)]"}`}>
            <span>{a.direction === "bullish" ? "+" : a.direction === "bearish" ? "-" : "·"}</span>
            <span className="truncate">{a.name}</span>
            <SourceBadge status={a.source_status} compact />
          </div>
        ))}
      </div>
    </button>
  );
}

function SectorDetailModal({ sector, onClose }: { sector: SectorMeta; onClose: () => void }) {
  const sent = sector.live_sentiment;
  const score = sent?.score ?? 0;
  const c = scoreColor(score);
  const Icon = score > 0 ? TrendingUp : score < 0 ? TrendingDown : Minus;
  const assessments = sent?.indicator_assessments ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="my-8 w-full max-w-3xl rounded-xl border border-slate-700 bg-slate-950 p-5" onClick={(e) => e.stopPropagation()}>
        <header className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{sector.name}</h2>
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${c.bg} ${c.text}`}>{sent?.verdict ?? c.label}</span>
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">Phase {sector.phase} · {sector.indicator_count}개 지표</div>
          </div>
          <button onClick={onClose} className="shrink-0 text-slate-400 hover:text-slate-200"><X size={18} /></button>
        </header>

        <div className={`mb-4 rounded-lg p-4 ring-1 ${c.bg} ${c.ring}`}>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon size={20} className={c.text} />
              <span className={`text-2xl font-bold tabular-nums ${c.text}`}>{score > 0 ? `+${score}` : score}</span>
              <span className="text-xs text-[var(--color-text-muted)]">종합 score</span>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-emerald-300">+ {sent?.bullish_count ?? 0}개 호재</span>
              <span className="text-rose-300">- {sent?.bearish_count ?? 0}개 악재</span>
            </div>
          </div>
          {sent?.key_takeaway && <p className="text-[12px] leading-relaxed text-[var(--color-text-secondary)]">{sent.key_takeaway}</p>}
        </div>

        <div className="mb-4">
          <h3 className="mb-2 text-xs font-semibold text-slate-300">지표별 평가</h3>
          <div className="space-y-1.5">
            {assessments.map((a, i) => (
              <div key={i} className={`rounded border px-2 py-1.5 text-[11px] leading-relaxed ${
                a.direction === "bullish"
                  ? "border-emerald-500/25 bg-emerald-500/8 text-emerald-200"
                  : a.direction === "bearish"
                  ? "border-rose-500/25 bg-rose-500/8 text-rose-200"
                  : "border-slate-700 bg-slate-900/60 text-slate-400"
              }`}>
                <span className="font-semibold">{a.direction === "bullish" ? "호재" : a.direction === "bearish" ? "악재" : "확인필요"}</span>
                <SourceBadge status={a.source_status} />
                <span className="mx-1">·</span>
                <span>{a.reason}</span>
                {a.source_name && (
                  <div className="mt-1 text-[10px] text-slate-500">
                    소스: {a.source_name}{a.updated_at ? ` · ${a.updated_at}` : ""}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-slate-800 pt-3 text-[10px] text-slate-500">
          live/proxy로 연결된 지표만 점수에 반영하고, 외부 원자료 지표는 보조 확인 항목으로 표시합니다.
        </div>
      </div>
    </div>
  );
}

function SourceBadge({ status, compact = false }: { status?: string; compact?: boolean }) {
  const label =
    status === "live" ? "live" :
    status === "proxy" || status === "computed_proxy" ? "proxy" :
    status === "delayed" ? "지연" :
    status === "monthly" ? "월간" :
    status === "missing" ? "미수집" :
    status === "manual" ? "외부" :
    status === "not_connected" ? "미수집" :
    status ?? "미수집";
  const cls =
    status === "live" ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-300" :
    status === "proxy" || status === "computed_proxy" ? "border-blue-500/30 bg-blue-500/15 text-blue-300" :
    status === "delayed" || status === "monthly" ? "border-amber-500/30 bg-amber-500/15 text-amber-300" :
    status === "manual" || status === "not_connected" ? "border-slate-600 bg-slate-700/50 text-slate-300" :
    "border-slate-700 bg-slate-800/60 text-slate-500";
  return <span className={`ml-1 inline-flex shrink-0 rounded border ${compact ? "px-1 py-0 text-[8px]" : "px-1.5 py-0.5 text-[9px]"} font-semibold ${cls}`}>{label}</span>;
}
