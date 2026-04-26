// 거시 전망 페이지 — 라이브 매크로 + 시나리오 자동 감지 + 27섹터 종합 추천
import { useEffect, useMemo, useState } from "react";
import { Telescope, AlertCircle, ArrowUp, ArrowDown, Zap, Trophy, ShieldAlert, Radio } from "lucide-react";
import MacroLayout from "./MacroLayout";
import WikiMarkdown from "./WikiMarkdown";
import { fetchOutlook, fetchWikiPage, fetchIndicators } from "@/api/macro";
import type { OutlookResponse, WikiPageResponse, LiveMacroIndicator, ActiveScenario, SynthesizedSector, SectorMeta, CurrentMacroEvent } from "@/types/macro";

export default function Outlook() {
  const [data, setData] = useState<OutlookResponse | null>(null);
  const [wiki, setWiki] = useState<WikiPageResponse | null>(null);
  const [sectorMap, setSectorMap] = useState<Record<string, SectorMeta>>({});
  const [loading, setLoading] = useState(true);
  const [showFullSpec, setShowFullSpec] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchOutlook(), fetchWikiPage("outlook"), fetchIndicators()])
      .then(([d, w, ind]) => {
        setData(d);
        setWiki(w);
        const map: Record<string, SectorMeta> = {};
        ind.sectors.forEach((s) => { map[s.id] = s; });
        setSectorMap(map);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const liveByCategory = useMemo(() => {
    if (!data?.live_indicators) return {};
    const map: Record<string, LiveMacroIndicator[]> = {};
    data.live_indicators.forEach((i) => {
      (map[i.category] ||= []).push(i);
    });
    return map;
  }, [data]);

  if (loading) return <MacroLayout title="거시 전망" subtitle="라이브 매크로 fetch 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="거시 전망" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  const top = data.synthesis?.top_sectors ?? [];
  const bottom = data.synthesis?.bottom_sectors ?? [];
  const active = data.active_scenarios ?? [];
  const events = data.current_events ?? [];
  const selected = selectedScenario ? data.scenarios.find((s) => s.id === selectedScenario) : null;

  return (
    <MacroLayout
      title="거시 전망 (Macro Outlook)"
      subtitle={`라이브 매크로 + 시나리오 자동 감지 + 27섹터 종합 추천 · ${data.current_regime.as_of} 기준`}
    >
      {events.length > 0 && (
        <section className="mb-6">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
            <Radio size={14} className="text-[#fbbf24]" />
            현재 핵심 이슈
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {events.map((event) => <CurrentEventCard key={event.id} event={event} sectorMap={sectorMap} />)}
          </div>
        </section>
      )}

      {/* 🏆 종합 추천 TOP/BOTTOM — 가장 위 */}
      <section className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="rounded-xl border border-[#10b981]/40 bg-gradient-to-br from-[#10b981]/15 to-transparent p-4">
          <div className="flex items-center gap-2 mb-3 text-[#10b981]">
            <Trophy size={18} />
            <h3 className="text-sm font-semibold">🏆 종합 유망 섹터 TOP {top.length}</h3>
            <span className="ml-auto text-[10px] text-[var(--color-text-muted)]">현재 이슈 + 원자재 + 시나리오</span>
          </div>
          <div className="space-y-2.5">
            {top.map((s) => <SynthesisRow key={s.sector_id} item={s} sectorMap={sectorMap} kind="top" />)}
          </div>
        </div>
        <div className="rounded-xl border border-[#ef4444]/40 bg-gradient-to-br from-[#ef4444]/15 to-transparent p-4">
          <div className="flex items-center gap-2 mb-3 text-[#ef4444]">
            <ShieldAlert size={18} />
            <h3 className="text-sm font-semibold">⚠️ 종합 우려 섹터 BOTTOM {bottom.length}</h3>
          </div>
          <div className="space-y-2.5">
            {bottom.length > 0 ? (
              bottom.map((s) => <SynthesisRow key={s.sector_id} item={s} sectorMap={sectorMap} kind="bottom" />)
            ) : (
              <div className="text-[11px] text-[var(--color-text-muted)] italic">현재 명확한 우려 섹터 없음</div>
            )}
          </div>
        </div>
      </section>

      {/* 🎯 활성 시나리오 (지금 어디 있나) */}
      {active.length > 0 && (
        <section className="mb-6">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
            <Zap size={14} className="text-[#fbbf24]" />
            지금 활성 시나리오 ({active.length}개 감지)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {active.map((s) => <ActiveScenarioCard key={s.id} scenario={s} sectorMap={sectorMap} />)}
          </div>
        </section>
      )}

      {/* 📊 라이브 거시 지표 */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
          <Telescope size={14} /> 📊 라이브 거시 지표 (yfinance · 30분 캐시)
        </h2>
        <div className="space-y-2">
          {Object.entries(liveByCategory).map(([cat, items]) => (
            <div key={cat}>
              <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">{cat}</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
                {items.map((i) => <LiveCell key={i.id} ind={i} />)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 정책 알림 */}
      {data.policy_alerts.length > 0 && (
        <section className="mb-6">
          <div className="rounded-lg border border-[#fbbf24]/30 bg-[#fbbf24]/5 p-3.5">
            <div className="flex items-center gap-2 mb-2 text-[#fbbf24]">
              <AlertCircle size={14} />
              <h3 className="text-xs font-semibold">정책 알림</h3>
            </div>
            <ul className="space-y-1 text-xs text-[var(--color-text-secondary)]">
              {data.policy_alerts.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
        </section>
      )}

      {/* 🔮 시나리오 시뮬레이터 — 9개 시나리오 클릭 → 영향 시뮬 */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">
          🔮 시나리오 시뮬레이터 — "이 상황이 오면?" 클릭해서 영향 보기
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mb-3">
          {data.scenarios.map((s) => {
            const isActive = active.some((a) => a.id === s.id);
            const isSelected = selectedScenario === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setSelectedScenario(isSelected ? null : s.id)}
                className={`text-left rounded-md border p-2.5 transition-all ${
                  isSelected
                    ? "border-[#3b82f6] bg-[#3b82f6]/15 ring-2 ring-[#3b82f6]/40"
                    : isActive
                    ? "border-[#fbbf24]/50 bg-[#fbbf24]/10 hover:border-[#fbbf24]"
                    : "border-[var(--color-border)] bg-[var(--color-bg-secondary)] hover:border-[#3b82f6]/40"
                }`}
              >
                <div className="text-[11px] font-semibold text-[var(--color-text-primary)] mb-1 flex items-center gap-1">
                  {isActive && <span className="text-[#fbbf24]">🔥</span>}
                  {s.name}
                </div>
                <div className="text-[9px] text-[var(--color-text-muted)] line-clamp-2">{s.triggers.join(" · ")}</div>
              </button>
            );
          })}
        </div>
        {selected && (
          <div className="rounded-xl border border-[#3b82f6]/40 bg-[#3b82f6]/5 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                💡 시뮬레이션: {selected.name}
              </h3>
              <button onClick={() => setSelectedScenario(null)} className="text-xs text-[var(--color-text-muted)] hover:text-white">×</button>
            </div>
            <div className="text-[11px] text-[var(--color-text-muted)] mb-3">트리거 신호: {selected.triggers.join(" / ")}</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <div className="text-[11px] font-semibold text-[#10b981] mb-1.5 flex items-center gap-1"><ArrowUp size={11} /> 호재 섹터</div>
                <div className="space-y-1">
                  {selected.favorable.map((sec) => (
                    <div key={sec} className="text-[11px] px-2 py-1 rounded bg-[#10b981]/15 text-[#6ee7b7]">{sec}</div>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-[#ef4444] mb-1.5 flex items-center gap-1"><ArrowDown size={11} /> 악재 섹터</div>
                <div className="space-y-1">
                  {selected.unfavorable.length > 0 ? selected.unfavorable.map((sec) => (
                    <div key={sec} className="text-[11px] px-2 py-1 rounded bg-[#ef4444]/15 text-[#fca5a5]">{sec}</div>
                  )) : <div className="text-[11px] italic text-[var(--color-text-muted)]">명확한 악재 섹터 없음</div>}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 8개 거시 차원 */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">8개 거시 차원 (참고)</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {data.dimensions.map((d) => (
            <div key={d.id} className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-2.5">
              <div className="text-[11px] font-semibold text-[var(--color-text-primary)] mb-1">{d.name}</div>
              <div className="text-[10px] text-[var(--color-text-muted)] leading-relaxed">
                {d.key_indicators.slice(0, 3).join(" · ")}
                {d.key_indicators.length > 3 && ` 외 ${d.key_indicators.length - 3}`}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <button onClick={() => setShowFullSpec((v) => !v)}
          className="text-xs px-3 py-1.5 rounded-md border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-white/5">
          {showFullSpec ? "▼ 전체 명세 닫기" : "▶ 전체 명세 보기 (33개 거시 지표 — wiki/macro/03-outlook.md)"}
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

function SynthesisRow({ item, sectorMap, kind }: { item: SynthesizedSector; sectorMap: Record<string, SectorMeta>; kind: "top" | "bottom" }) {
  const sec = sectorMap[item.sector_id];
  const color = kind === "top" ? "#10b981" : "#ef4444";
  return (
    <div className="rounded bg-black/20 p-2.5">
      <div className="flex items-center justify-between mb-1">
        <div className="text-sm font-semibold text-[var(--color-text-primary)]">{sec?.name ?? item.sector_id}</div>
        <div className="flex items-center gap-1.5 text-[10px]">
          <span style={{ color }} className="font-bold">
            {item.synthesis_score > 0 ? `+${item.synthesis_score}` : item.synthesis_score}
          </span>
          {sec && <><span className="text-[var(--color-text-muted)]">·</span><span className="text-[var(--color-text-muted)]">{sec.indicator_count}지표</span></>}
        </div>
      </div>
      <div className="space-y-0.5">
        {item.drivers.slice(0, 4).map((d, i) => (
          <div key={i} className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{d}</div>
        ))}
      </div>
    </div>
  );
}

function ActiveScenarioCard({ scenario, sectorMap }: { scenario: ActiveScenario; sectorMap: Record<string, SectorMeta> }) {
  const pct = Math.round(scenario.strength * 100);
  return (
    <div className="rounded-xl border border-[#fbbf24]/40 bg-[#fbbf24]/5 p-3.5">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-semibold text-[var(--color-text-primary)]">🔥 {scenario.name}</div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-[#fbbf24]/25 text-[#fbbf24] font-semibold">{pct}%</span>
      </div>
      <div className="w-full h-1 rounded bg-white/5 mb-2">
        <div className="h-full rounded bg-[#fbbf24]" style={{ width: `${pct}%` }} />
      </div>
      <div className="space-y-0.5 mb-2">
        {scenario.evidence.map((e, i) => (
          <div key={i} className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">· {e}</div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <div className="text-[#10b981] mb-0.5">↑ 호재</div>
          <div className="flex flex-wrap gap-1">
            {scenario.favorable_sectors.slice(0, 4).map((sid) => (
              <span key={sid} className="px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#6ee7b7]">{sectorMap[sid]?.name ?? sid}</span>
            ))}
          </div>
        </div>
        <div>
          <div className="text-[#ef4444] mb-0.5">↓ 악재</div>
          <div className="flex flex-wrap gap-1">
            {scenario.unfavorable_sectors.length > 0 ? scenario.unfavorable_sectors.slice(0, 4).map((sid) => (
              <span key={sid} className="px-1.5 py-0.5 rounded bg-[#ef4444]/15 text-[#fca5a5]">{sectorMap[sid]?.name ?? sid}</span>
            )) : <span className="text-[var(--color-text-muted)] italic">없음</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function CurrentEventCard({ event, sectorMap }: { event: CurrentMacroEvent; sectorMap: Record<string, SectorMeta> }) {
  const pct = Math.round(event.severity * 100);
  return (
    <div className="rounded-xl border border-[#fbbf24]/40 bg-[#fbbf24]/5 p-3.5">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <div className="text-sm font-semibold text-[var(--color-text-primary)]">{event.title}</div>
          <div className="text-[10px] text-[#fbbf24] mt-0.5">{event.status}</div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-[#fbbf24]/25 text-[#fbbf24] font-semibold">{pct}%</span>
      </div>
      <div className="w-full h-1 rounded bg-white/5 mb-2">
        <div className="h-full rounded bg-[#fbbf24]" style={{ width: `${pct}%` }} />
      </div>
      <div className="space-y-0.5 mb-3">
        {event.evidence.slice(0, 3).map((e, i) => (
          <div key={i} className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">· {e}</div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <div className="text-[#10b981] mb-1">↑ 우호</div>
          <div className="flex flex-wrap gap-1">
            {event.favorable_sectors.slice(0, 6).map((sid) => (
              <span key={sid} className="px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#6ee7b7]">{sectorMap[sid]?.name ?? sid}</span>
            ))}
          </div>
        </div>
        <div>
          <div className="text-[#ef4444] mb-1">↓ 부담</div>
          <div className="flex flex-wrap gap-1">
            {event.unfavorable_sectors.slice(0, 6).map((sid) => (
              <span key={sid} className="px-1.5 py-0.5 rounded bg-[#ef4444]/15 text-[#fca5a5]">{sectorMap[sid]?.name ?? sid}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function LiveCell({ ind }: { ind: LiveMacroIndicator }) {
  const c1 = ind.change_pct_1d;
  const z = ind.zscore_60d;
  const colorByDir = (val: number | null) =>
    val == null ? "text-[var(--color-text-muted)]" : val > 0 ? "text-[#10b981]" : val < 0 ? "text-[#ef4444]" : "text-[var(--color-text-muted)]";
  const isAnomalous = z != null && Math.abs(z) > 1.5;
  return (
    <div className={`rounded-md border p-2 ${isAnomalous ? "border-[#fbbf24]/50 bg-[#fbbf24]/5" : "border-[var(--color-border)] bg-[var(--color-bg-secondary)]"}`}>
      <div className="text-[10px] text-[var(--color-text-muted)] truncate">{ind.name}</div>
      <div className="text-base font-bold text-[var(--color-text-primary)]">
        {ind.price != null ? ind.price.toLocaleString(undefined, { maximumFractionDigits: 4 }) : "—"}
      </div>
      <div className="flex items-center justify-between text-[10px]">
        <span className={colorByDir(c1)}>{c1 != null ? `${c1 > 0 ? "+" : ""}${c1}%` : "—"}</span>
        {z != null && Math.abs(z) > 0.5 && (
          <span className={colorByDir(z)}>Z {z > 0 ? "+" : ""}{z}</span>
        )}
      </div>
    </div>
  );
}
