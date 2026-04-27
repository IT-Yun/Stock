import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3, Boxes, ChevronRight, ExternalLink, GitBranch, Star } from "lucide-react";
import MacroLayout from "./MacroLayout";
import WikiMarkdown from "./WikiMarkdown";
import ChartView from "@/components/ChartView";
import { fetchValueChain, fetchWikiPage } from "@/api/macro";
import type { ValueChainResponse, ValueChainTier, WikiPageResponse } from "@/types/macro";

const TIER_THEMES: Record<number, { border: string; bg: string; tint: string }> = {
  0: { border: "border-[#94a3b8]/40", bg: "bg-[#94a3b8]/5", tint: "text-[#94a3b8]" },
  1: { border: "border-[#a78bfa]/40", bg: "bg-[#a78bfa]/5", tint: "text-[#a78bfa]" },
  2: { border: "border-[#60a5fa]/40", bg: "bg-[#60a5fa]/5", tint: "text-[#60a5fa]" },
  3: { border: "border-[#34d399]/40", bg: "bg-[#34d399]/5", tint: "text-[#34d399]" },
  4: { border: "border-[#fbbf24]/60", bg: "bg-[#fbbf24]/10", tint: "text-[#fbbf24]" },
  5: { border: "border-[#f87171]/40", bg: "bg-[#f87171]/5", tint: "text-[#f87171]" },
};

const TIER_LABELS: Record<number, string> = {
  0: "최종 수요",
  1: "핵심 칩/원청",
  2: "서버·네트워크",
  3: "데이터센터",
  4: "전력·냉각 장비",
  5: "에너지·원재료",
};

function extractTicker(name: string): string | null {
  const kr = name.match(/\((\d{6})\)/);
  if (kr) return `${kr[1]}.KS`;
  const us = name.match(/\(\s*([A-Z]{1,6})\s*\)/);
  if (us) return us[1];
  return null;
}

function cleanName(name: string): string {
  return name.replace(/\(\s*[A-Z]{1,6}\s*\)/g, "").replace(/\(\d{6}\)/g, "").trim();
}

function groupName(tier: ValueChainTier): string {
  return tier.name.split("·")[0].trim();
}

export default function ValueChain() {
  const [data, setData] = useState<ValueChainResponse | null>(null);
  const [wiki, setWiki] = useState<WikiPageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFullSpec, setShowFullSpec] = useState(false);
  const [selectedSectorId, setSelectedSectorId] = useState<string | null>(null);
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [selectedStock, setSelectedStock] = useState<{ ticker: string; name: string } | null>(null);

  useEffect(() => {
    Promise.all([fetchValueChain(), fetchWikiPage("value-chain")])
      .then(([d, w]) => {
        setData(d);
        setWiki(w);
        setSelectedSectorId(d.sectors[0]?.sector_id ?? null);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const selectedSector = useMemo(() => {
    if (!data) return null;
    return data.sectors.find((s) => s.sector_id === selectedSectorId) ?? data.sectors[0] ?? null;
  }, [data, selectedSectorId]);

  const stages = useMemo(() => {
    if (!selectedSector) return [];
    return Array.from(new Set(selectedSector.tiers.map(groupName)));
  }, [selectedSector]);

  const visibleTiers = useMemo(() => {
    if (!selectedSector) return [];
    if (selectedStage === "all") return selectedSector.tiers;
    return selectedSector.tiers.filter((t) => groupName(t) === selectedStage);
  }, [selectedSector, selectedStage]);

  if (loading) return <MacroLayout title="Value Chain" subtitle="로딩 중..."><div /></MacroLayout>;
  if (!data || !selectedSector) return <MacroLayout title="Value Chain" subtitle="데이터 로드 실패"><div /></MacroLayout>;

  return (
    <MacroLayout
      title="Value Chain"
      subtitle={`${data.total_kr_stocks} KR + ${data.total_us_stocks} US · 섹터별 세부 단계 선택 후 종목/차트 확인`}
    >
      <section className="mb-5">
        <div className="flex flex-wrap gap-2">
          {data.sectors.map((sec) => (
            <button
              key={sec.sector_id}
              onClick={() => {
                setSelectedSectorId(sec.sector_id);
                setSelectedStage("all");
                setSelectedStock(null);
              }}
              className={`rounded-md border px-3 py-2 text-xs font-semibold transition-colors ${
                selectedSector.sector_id === sec.sector_id
                  ? "border-[#3b82f6] bg-[#3b82f6]/15 text-[#93c5fd]"
                  : "border-[var(--color-border)] bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:border-[#3b82f6]/50"
              }`}
            >
              {sec.sector_name}
            </button>
          ))}
        </div>
      </section>

      <section className="mb-5">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
            <div>
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                <GitBranch size={18} /> {selectedSector.sector_name}
              </h2>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1">{selectedSector.hidden_alpha}</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <StageButton label="전체" active={selectedStage === "all"} onClick={() => setSelectedStage("all")} />
              {stages.map((stage) => (
                <StageButton key={stage} label={stage} active={selectedStage === stage} onClick={() => setSelectedStage(stage)} />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-4">
            <div className="min-w-0">
              {selectedStage === "all" ? (
                <FlowDiagram tiers={visibleTiers} onSelectStock={(stock) => setSelectedStock(stock)} />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {visibleTiers.map((tier) => (
                    <TierPanel
                      key={`${tier.level}-${tier.name}`}
                      tier={tier}
                      onSelectStock={(stock) => setSelectedStock(stock)}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-black/20 p-3 min-h-[360px]">
              {selectedStock ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="text-sm font-semibold text-[var(--color-text-primary)]">{selectedStock.name}</div>
                      <div className="text-[10px] text-[var(--color-text-muted)]">{selectedStock.ticker}</div>
                    </div>
                    <a
                      href={`/sector/ai_semi?stock=${encodeURIComponent(selectedStock.ticker)}`}
                      className="inline-flex items-center gap-1 text-[10px] text-[#93c5fd] hover:underline"
                    >
                      상세 분석 <ExternalLink size={11} />
                    </a>
                  </div>
                  <ChartView ticker={selectedStock.ticker} />
                </div>
              ) : (
                <div className="h-full min-h-[320px] flex flex-col items-center justify-center text-center">
                  <BarChart3 size={28} className="text-[var(--color-text-muted)] mb-2" />
                  <div className="text-sm font-semibold text-[var(--color-text-primary)]">종목을 누르면 차트가 열립니다</div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-1">티커가 있는 칩만 클릭 가능합니다.</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
          <Star size={14} className="text-[#fbbf24]" /> Hidden Alpha
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          {data.hidden_alpha_top.map((a) => (
            <div key={a.company} className="rounded-lg border border-[#fbbf24]/30 bg-[#fbbf24]/5 p-3">
              <div className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">{a.company}</div>
              <div className="flex flex-wrap gap-1 mb-2">
                {a.tickers.map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedStock({ ticker: `${t}.KS`, name: a.company })}
                    className="text-[9px] px-1.5 py-0.5 rounded bg-[#fbbf24]/20 text-[#fbbf24] font-mono"
                  >
                    {t}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{a.thesis}</p>
            </div>
          ))}
        </div>
      </section>

      {data.warnings.length > 0 && (
        <section className="mb-6">
          <div className="rounded-lg border border-[#ef4444]/30 bg-[#ef4444]/5 p-3">
            <div className="flex items-center gap-2 mb-2 text-[#ef4444]">
              <AlertTriangle size={14} />
              <h3 className="text-xs font-semibold">억지 매핑 회피</h3>
            </div>
            <ul className="space-y-1 text-[11px] text-[var(--color-text-secondary)]">
              {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        </section>
      )}

      <section>
        <button
          onClick={() => setShowFullSpec((v) => !v)}
          className="text-xs px-3 py-1.5 rounded-md border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-white/5"
        >
          {showFullSpec ? "전체 명세 닫기" : "전체 명세 보기"}
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

function FlowDiagram({ tiers, onSelectStock }: { tiers: ValueChainTier[]; onSelectStock: (stock: { ticker: string; name: string }) => void }) {
  const sorted = [...tiers].sort((a, b) => a.level - b.level);
  return (
    <div className="overflow-x-auto pb-2">
      <div className="min-w-[980px] flex items-stretch gap-3">
        {sorted.map((tier, idx) => (
          <div key={`${tier.level}-${tier.name}`} className="flex items-stretch gap-3">
            <div className="w-[230px] shrink-0">
              <TierPanel tier={tier} compact onSelectStock={onSelectStock} />
            </div>
            {idx < sorted.length - 1 && (
              <div className="flex items-center">
                <div className="h-px w-9 bg-slate-600" />
                <ChevronRight size={18} className="text-slate-500 -ml-1" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function StageButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md border px-2.5 py-1.5 text-[10px] font-semibold transition-colors ${
        active
          ? "border-[#fbbf24] bg-[#fbbf24]/15 text-[#fbbf24]"
          : "border-[var(--color-border)] bg-black/20 text-[var(--color-text-secondary)] hover:border-[#fbbf24]/50"
      }`}
    >
      {label}
    </button>
  );
}

function TierPanel({ tier, compact = false, onSelectStock }: { tier: ValueChainTier; compact?: boolean; onSelectStock: (stock: { ticker: string; name: string }) => void }) {
  const theme = TIER_THEMES[tier.level] ?? TIER_THEMES[0];
  const stage = groupName(tier);
  const detail = tier.name.includes("·") ? tier.name.split("·").slice(1).join("·").trim() : TIER_LABELS[tier.level];

  return (
    <div className={`rounded-lg border ${theme.border} ${theme.bg} p-3 ${compact ? "min-h-[360px]" : ""}`}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className={`text-[10px] font-bold ${theme.tint}`}>T{tier.level} · {stage}</div>
          <div className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">{detail}</div>
        </div>
        {tier.is_korean_alpha && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#fbbf24]/25 text-[#fbbf24] font-bold">KR alpha</span>
        )}
      </div>
      <div className={`flex flex-wrap gap-1.5 ${compact ? "content-start" : ""}`}>
        {tier.players.map((p) => {
          const ticker = extractTicker(p);
          const name = cleanName(p);
          return (
            <button
              key={p}
              disabled={!ticker}
              onClick={() => ticker && onSelectStock({ ticker, name })}
              className={`inline-flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium ${
                ticker
                  ? tier.is_korean_alpha
                    ? "border border-[#fbbf24]/40 bg-[#fbbf24]/20 text-[#fbbf24] hover:bg-[#fbbf24]/30"
                    : "bg-[#3b82f6]/15 text-[#93c5fd] hover:bg-[#3b82f6]/25"
                  : "bg-white/5 text-[var(--color-text-muted)] cursor-default"
              }`}
            >
              <Boxes size={10} />
              <span className="truncate max-w-[150px]">{name}</span>
              {ticker && <ChevronRight size={10} />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
