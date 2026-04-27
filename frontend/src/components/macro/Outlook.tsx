import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, RotateCcw, SlidersHorizontal } from "lucide-react";
import MacroLayout from "./MacroLayout";
import { fetchIndicators, fetchOutlook } from "@/api/macro";
import type { CurrentMacroEvent, OutlookResponse, SectorMeta } from "@/types/macro";

type Vote = -1 | 0 | 1;
type ScenarioInput =
  | { id: string; name: string; triggers: string[]; kind: "scenario"; favorable: string[]; unfavorable: string[] }
  | { id: string; name: string; triggers: string[]; kind: "event"; favorable: string[]; unfavorable: string[]; event: CurrentMacroEvent };

export default function Outlook() {
  const [data, setData] = useState<OutlookResponse | null>(null);
  const [sectorMap, setSectorMap] = useState<Record<string, SectorMeta>>({});
  const [loading, setLoading] = useState(true);
  const [votes, setVotes] = useState<Record<string, Vote>>({});

  useEffect(() => {
    Promise.all([fetchOutlook(), fetchIndicators()])
      .then(([d, ind]) => {
        setData(d);
        const map: Record<string, SectorMeta> = {};
        ind.sectors.forEach((s) => { map[s.id] = s; });
        setSectorMap(map);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const inputs = useMemo(() => {
    if (!data) return [];
    const scenarios: ScenarioInput[] = data.scenarios.map((s) => ({
      id: s.id,
      name: s.name,
      triggers: s.triggers,
      kind: "scenario",
      favorable: s.favorable,
      unfavorable: s.unfavorable,
    }));
    const events: ScenarioInput[] = (data.current_events ?? []).map((e) => ({
      id: `event:${e.id}`,
      name: e.title,
      triggers: e.evidence.slice(0, 2),
      kind: "event",
      favorable: e.favorable_sectors,
      unfavorable: e.unfavorable_sectors,
      event: e,
    }));
    return [...events, ...scenarios];
  }, [data]);

  const simulation = useMemo(() => simulate(inputs, votes, sectorMap), [inputs, votes, sectorMap]);

  if (loading) return <MacroLayout title="거시전망 시뮬레이터" subtitle="시나리오 불러오는 중..."><div /></MacroLayout>;
  if (!data) return <MacroLayout title="거시전망 시뮬레이터" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  const applyCurrent = () => {
    const next: Record<string, Vote> = {};
    for (const s of data.active_scenarios ?? []) next[s.id] = 1;
    for (const e of data.current_events ?? []) next[`event:${e.id}`] = 1;
    setVotes(next);
  };

  return (
    <MacroLayout
      title="거시전망 시뮬레이터"
      subtitle="경제·정치·전쟁·금리 시나리오를 발생/완화로 체크해서 우호 섹터를 종합"
    >
      <section className="mb-5 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <SlidersHorizontal size={16} /> 시나리오 체크
            </h2>
            <p className="mt-1 text-xs text-slate-500">발생은 해당 시나리오가 현실화, 완화·실패는 반대 방향으로 계산합니다.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={applyCurrent} className="rounded-md border border-amber-500/35 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/15">
              현재 감지 적용
            </button>
            <button onClick={() => setVotes({})} className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">
              <RotateCcw size={13} /> 초기화
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
          {inputs.map((input) => (
            <ScenarioCard
              key={input.id}
              input={input}
              vote={votes[input.id] ?? 0}
              sectorMap={sectorMap}
              onVote={(vote) => setVotes((prev) => ({ ...prev, [input.id]: vote }))}
            />
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <ResultPanel title="우호 섹터" tone="good" items={simulation.good} />
        <ResultPanel title="부담 섹터" tone="bad" items={simulation.bad} />
      </section>
    </MacroLayout>
  );
}

function ScenarioCard({
  input,
  vote,
  sectorMap,
  onVote,
}: {
  input: ScenarioInput;
  vote: Vote;
  sectorMap: Record<string, SectorMeta>;
  onVote: (vote: Vote) => void;
}) {
  const isEvent = input.kind === "event";
  return (
    <div className={`rounded-lg border p-3 ${vote === 1 ? "border-emerald-500/35 bg-emerald-500/8" : vote === -1 ? "border-rose-500/35 bg-rose-500/8" : isEvent ? "border-amber-500/25 bg-amber-500/5" : "border-slate-800 bg-slate-900/45"}`}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-100">{isEvent ? "🔥 " : ""}{input.name}</div>
          <div className="mt-1 line-clamp-2 text-[10px] leading-relaxed text-slate-500">{input.triggers.join(" · ")}</div>
        </div>
        <span className="shrink-0 rounded bg-white/5 px-1.5 py-0.5 text-[9px] font-semibold text-slate-400">{isEvent ? "현재 이슈" : "거시"}</span>
      </div>

      <div className="mb-2 grid grid-cols-3 gap-1">
        <VoteButton active={vote === 1} tone="good" label="발생" onClick={() => onVote(vote === 1 ? 0 : 1)} />
        <VoteButton active={vote === 0} tone="neutral" label="중립" onClick={() => onVote(0)} />
        <VoteButton active={vote === -1} tone="bad" label="완화/실패" onClick={() => onVote(vote === -1 ? 0 : -1)} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <MiniSectorList title="우호" tone="good" items={input.favorable} sectorMap={sectorMap} />
        <MiniSectorList title="부담" tone="bad" items={input.unfavorable} sectorMap={sectorMap} />
      </div>
    </div>
  );
}

function VoteButton({ active, tone, label, onClick }: { active: boolean; tone: "good" | "bad" | "neutral"; label: string; onClick: () => void }) {
  const cls = active
    ? tone === "good" ? "border-emerald-500 bg-emerald-500/20 text-emerald-200"
    : tone === "bad" ? "border-rose-500 bg-rose-500/20 text-rose-200"
    : "border-blue-500 bg-blue-500/20 text-blue-200"
    : "border-slate-800 bg-black/20 text-slate-500 hover:border-slate-600";
  return <button onClick={onClick} className={`rounded border px-2 py-1.5 text-[10px] font-semibold ${cls}`}>{label}</button>;
}

function MiniSectorList({ title, tone, items, sectorMap }: { title: string; tone: "good" | "bad"; items: string[]; sectorMap: Record<string, SectorMeta> }) {
  const color = tone === "good" ? "text-emerald-300" : "text-rose-300";
  return (
    <div>
      <div className={`mb-1 font-semibold ${color}`}>{title}</div>
      <div className="flex flex-wrap gap-1">
        {items.slice(0, 5).map((x) => (
          <span key={x} className={`rounded px-1.5 py-0.5 ${tone === "good" ? "bg-emerald-500/12 text-emerald-200" : "bg-rose-500/12 text-rose-200"}`}>
            {sectorMap[x]?.name ?? x}
          </span>
        ))}
        {items.length === 0 && <span className="text-slate-600">없음</span>}
      </div>
    </div>
  );
}

function ResultPanel({ title, tone, items }: { title: string; tone: "good" | "bad"; items: SimResult[] }) {
  const Icon = tone === "good" ? ArrowUp : ArrowDown;
  const color = tone === "good" ? "text-emerald-300" : "text-rose-300";
  const border = tone === "good" ? "border-emerald-500/35 bg-emerald-500/8" : "border-rose-500/35 bg-rose-500/8";
  return (
    <div className={`rounded-xl border p-4 ${border}`}>
      <div className={`mb-3 flex items-center gap-2 text-sm font-semibold ${color}`}><Icon size={16} /> {title}</div>
      <div className="space-y-2">
        {items.length ? items.map((item) => (
          <div key={item.name} className="rounded-lg bg-black/25 p-3">
            <div className="mb-1 flex items-center justify-between gap-3">
              <div className="font-semibold text-slate-100">{item.name}</div>
              <div className={`font-mono text-sm font-bold ${color}`}>{item.score > 0 ? "+" : ""}{item.score.toFixed(1)}</div>
            </div>
            <div className="space-y-0.5">
              {item.reasons.slice(0, 5).map((reason) => (
                <div key={reason} className="text-[11px] leading-relaxed text-slate-400">· {reason}</div>
              ))}
            </div>
          </div>
        )) : (
          <div className="rounded-lg bg-black/20 p-4 text-center text-xs text-slate-500">선택된 시나리오가 없습니다.</div>
        )}
      </div>
    </div>
  );
}

type SimResult = { name: string; score: number; reasons: string[] };

function simulate(inputs: ScenarioInput[], votes: Record<string, Vote>, sectorMap: Record<string, SectorMeta>) {
  const scores: Record<string, SimResult> = {};
  const add = (key: string, delta: number, reason: string) => {
    const name = sectorMap[key]?.name ?? key;
    const item = scores[name] ?? { name, score: 0, reasons: [] };
    item.score += delta;
    item.reasons.push(reason);
    scores[name] = item;
  };

  for (const input of inputs) {
    const vote = votes[input.id] ?? 0;
    if (vote === 0) continue;
    const base = input.kind === "event" ? Math.max(1.2, input.event.severity * 3) : 2;
    const success = vote === 1;

    if (input.kind === "event" && input.event.sector_impacts?.length) {
      for (const impact of input.event.sector_impacts) {
        const delta = impact.score * base * (success ? 1 : -1);
        add(impact.sector_id, delta, `${input.name} ${success ? "발생" : "완화"}: ${impact.reason}`);
      }
      continue;
    }

    for (const sec of input.favorable) add(sec, success ? base : -base * 0.8, `${input.name} ${success ? "발생 시 우호" : "실패/완화 시 우호 약화"}`);
    for (const sec of input.unfavorable) add(sec, success ? -base : base * 0.8, `${input.name} ${success ? "발생 시 부담" : "실패/완화 시 부담 완화"}`);
  }

  const all = Object.values(scores).filter((x) => Math.abs(x.score) >= 0.1);
  return {
    good: all.filter((x) => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 12),
    bad: all.filter((x) => x.score < 0).sort((a, b) => a.score - b.score).slice(0, 12),
  };
}
