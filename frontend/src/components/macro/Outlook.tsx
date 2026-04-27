import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ExternalLink, Radio, Zap } from "lucide-react";
import MacroLayout from "./MacroLayout";
import { fetchIndicators, fetchOutlook } from "@/api/macro";
import type { BreakingMacroIssue, OutlookResponse, SectorMeta } from "@/types/macro";

export default function Outlook() {
  const [data, setData] = useState<OutlookResponse | null>(null);
  const [sectorMap, setSectorMap] = useState<Record<string, SectorMeta>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchOutlook(), fetchIndicators()])
      .then(([outlook, indicators]) => {
        setData(outlook);
        const map: Record<string, SectorMeta> = {};
        indicators.sectors.forEach((s) => { map[s.id] = s; });
        setSectorMap(map);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const issues = useMemo(() => data?.breaking_issues ?? [], [data]);

  if (loading) return <MacroLayout title="거시 속보 스캐너" subtitle="뉴스/RSS 수집 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="거시 속보 스캐너" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  return (
    <MacroLayout
      title="거시 속보 스캐너"
      subtitle="최신 뉴스/RSS 기반 · 이슈별 국내외 섹터 영향 자동 분류 · 10분 캐시"
    >
      <section className="mb-5 rounded-xl border border-amber-500/25 bg-amber-500/5 p-4">
        <div className="mb-3 flex items-center gap-2 text-amber-300">
          <Radio size={16} />
          <h2 className="text-sm font-semibold">지금 당장 봐야 할 이슈</h2>
        </div>
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          {issues.map((issue) => (
            <IssueCard key={issue.id} issue={issue} sectorMap={sectorMap} />
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <div className="mb-3 flex items-center gap-2 text-slate-200">
          <Zap size={15} />
          <h2 className="text-sm font-semibold">속보 종합 섹터 영향</h2>
        </div>
        <ImpactSummary issues={issues} sectorMap={sectorMap} />
      </section>
    </MacroLayout>
  );
}

function IssueCard({ issue, sectorMap }: { issue: BreakingMacroIssue; sectorMap: Record<string, SectorMeta> }) {
  const pct = Math.round((issue.urgency ?? 0) * 100);
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950/70 p-3">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-slate-100">🔥 {issue.title}</div>
          <div className="mt-1 text-[11px] leading-relaxed text-slate-400">{issue.impact}</div>
        </div>
        <span className="shrink-0 rounded bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-300">긴급 {pct}</span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-[11px]">
        <SectorChips title="우호" tone="good" ids={issue.favorable_sectors} sectorMap={sectorMap} />
        <SectorChips title="부담" tone="bad" ids={issue.unfavorable_sectors} sectorMap={sectorMap} />
      </div>

      <div className="space-y-1.5">
        {issue.articles.length ? issue.articles.slice(0, 4).map((a) => (
          <a key={`${a.title}-${a.published_at}`} href={a.url} target="_blank" rel="noopener noreferrer"
             className="block rounded border border-slate-800 bg-black/20 px-2.5 py-2 hover:border-slate-600">
            <div className="line-clamp-2 text-[12px] font-medium text-slate-200">{a.title}</div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] text-slate-500">
              <span>{a.source}</span>
              <span>·</span>
              <span>{a.published_at?.slice(0, 16).replace("T", " ")}</span>
              <ExternalLink size={10} />
            </div>
          </a>
        )) : (
          <div className="rounded border border-rose-500/20 bg-rose-500/5 p-2 text-[11px] text-rose-300">
            <AlertTriangle size={12} className="mr-1 inline" /> 뉴스 수집 실패: {issue.error ?? "RSS 응답 없음"}
          </div>
        )}
      </div>
    </div>
  );
}

function SectorChips({ title, tone, ids, sectorMap }: { title: string; tone: "good" | "bad"; ids: string[]; sectorMap: Record<string, SectorMeta> }) {
  return (
    <div>
      <div className={`mb-1 font-semibold ${tone === "good" ? "text-emerald-300" : "text-rose-300"}`}>{title}</div>
      <div className="flex flex-wrap gap-1">
        {ids.map((id) => (
          <span key={id} className={`rounded px-1.5 py-0.5 ${tone === "good" ? "bg-emerald-500/15 text-emerald-200" : "bg-rose-500/15 text-rose-200"}`}>
            {sectorMap[id]?.name ?? id}
          </span>
        ))}
      </div>
    </div>
  );
}

function ImpactSummary({ issues, sectorMap }: { issues: BreakingMacroIssue[]; sectorMap: Record<string, SectorMeta> }) {
  const scores: Record<string, { score: number; reasons: string[] }> = {};
  for (const issue of issues) {
    const weight = Math.max(0.5, issue.urgency || 0.5);
    for (const sid of issue.favorable_sectors) {
      const row = scores[sid] ?? { score: 0, reasons: [] };
      row.score += weight;
      row.reasons.push(`+ ${issue.title}`);
      scores[sid] = row;
    }
    for (const sid of issue.unfavorable_sectors) {
      const row = scores[sid] ?? { score: 0, reasons: [] };
      row.score -= weight;
      row.reasons.push(`- ${issue.title}`);
      scores[sid] = row;
    }
  }
  const rows = Object.entries(scores).sort((a, b) => Math.abs(b[1].score) - Math.abs(a[1].score)).slice(0, 16);
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
      {rows.map(([sid, row]) => (
        <div key={sid} className={`rounded-lg border p-3 ${row.score >= 0 ? "border-emerald-500/25 bg-emerald-500/8" : "border-rose-500/25 bg-rose-500/8"}`}>
          <div className="mb-1 flex items-center justify-between gap-2">
            <div className="font-semibold text-slate-100">{sectorMap[sid]?.name ?? sid}</div>
            <div className={`font-mono text-sm font-bold ${row.score >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{row.score > 0 ? "+" : ""}{row.score.toFixed(1)}</div>
          </div>
          {row.reasons.slice(0, 3).map((r) => <div key={r} className="text-[10px] text-slate-400">{r}</div>)}
        </div>
      ))}
    </div>
  );
}
