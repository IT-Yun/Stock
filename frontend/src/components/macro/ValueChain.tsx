import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3, Boxes, ChevronDown, ChevronRight, ExternalLink, GitBranch, Star, X } from "lucide-react";
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
  1: "원청/핵심 제품",
  2: "제조/플랫폼",
  3: "장비/인프라",
  4: "소재/부품",
  5: "원재료/정책/에너지",
};

function extractTicker(name: string): string | null {
  const kr = name.match(/\((\d{6})\)/);
  if (kr) return `${kr[1]}.KS`;
  const us = name.match(/\(\s*([A-Z]{1,6})\s*\)/);
  if (us) return us[1];
  if (/^[A-Z]{2,6}$/.test(name.trim())) return name.trim();
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
      subtitle={`${data.total_kr_stocks} KR + ${data.total_us_stocks} US · 세로 공정 흐름 · 종목 클릭 시 차트`}
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

      <section className="mb-5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-[var(--color-text-primary)]">
              <GitBranch size={18} /> {selectedSector.sector_name}
            </h2>
            <p className="mt-1 text-xs text-[var(--color-text-secondary)]">{selectedSector.hidden_alpha}</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <StageButton label="전체" active={selectedStage === "all"} onClick={() => setSelectedStage("all")} />
            {stages.map((stage) => (
              <StageButton key={stage} label={stage} active={selectedStage === stage} onClick={() => setSelectedStage(stage)} />
            ))}
          </div>
        </div>

        <VerticalFlow
          tiers={visibleTiers}
          sectorName={selectedSector.sector_name}
          onSelectStock={(stock) => setSelectedStock(stock)}
        />
      </section>

      <section className="mb-6">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
          <Star size={14} className="text-[#fbbf24]" /> Hidden Alpha
        </h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {data.hidden_alpha_top.map((a) => (
            <div key={a.company} className="rounded-lg border border-[#fbbf24]/30 bg-[#fbbf24]/5 p-3">
              <div className="mb-1 text-sm font-semibold text-[var(--color-text-primary)]">{a.company}</div>
              <div className="mb-2 flex flex-wrap gap-1">
                {a.tickers.map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedStock({ ticker: `${t}.KS`, name: a.company })}
                    className="rounded bg-[#fbbf24]/20 px-1.5 py-0.5 font-mono text-[9px] text-[#fbbf24]"
                  >
                    {t}
                  </button>
                ))}
              </div>
              <p className="text-[11px] leading-relaxed text-[var(--color-text-secondary)]">{a.thesis}</p>
            </div>
          ))}
        </div>
      </section>

      {data.warnings.length > 0 && (
        <section className="mb-6">
          <div className="rounded-lg border border-[#ef4444]/30 bg-[#ef4444]/5 p-3">
            <div className="mb-2 flex items-center gap-2 text-[#ef4444]">
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
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-white/5"
        >
          {showFullSpec ? "전체 명세 닫기" : "전체 명세 보기"}
        </button>
        {showFullSpec && wiki && (
          <div className="mt-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4">
            <WikiMarkdown content={wiki.content} />
          </div>
        )}
      </section>

      {selectedStock && (
        <StockChartModal
          stock={selectedStock}
          sectorId={selectedSector.sector_id}
          onClose={() => setSelectedStock(null)}
        />
      )}
    </MacroLayout>
  );
}

function VerticalFlow({
  tiers,
  sectorName,
  onSelectStock,
}: {
  tiers: ValueChainTier[];
  sectorName: string;
  onSelectStock: (stock: { ticker: string; name: string }) => void;
}) {
  const sorted = [...tiers].sort((a, b) => a.level - b.level);
  if (sorted.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-black/20 p-8 text-center">
        <BarChart3 size={28} className="mx-auto mb-2 text-[var(--color-text-muted)]" />
        <div className="text-sm font-semibold text-[var(--color-text-primary)]">밸류체인 데이터 없음</div>
      </div>
    );
  }

  return (
    <div>
      {sorted.map((tier, idx) => (
        <div key={`${tier.node_id ?? tier.level}-${tier.name}`}>
          <TierPanel tier={tier} sectorName={sectorName} onSelectStock={onSelectStock} />
          {idx < sorted.length - 1 && (
            <div className="flex items-center justify-center py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-700 bg-slate-950">
                <ChevronDown size={18} className="text-slate-500" />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function StockChartModal({
  stock,
  sectorId,
  onClose,
}: {
  stock: { ticker: string; name: string };
  sectorId: string;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 p-4" onClick={(e) => e.stopPropagation()}>
        <header className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="text-base font-semibold text-[var(--color-text-primary)]">{stock.name}</div>
            <div className="text-[10px] text-[var(--color-text-muted)]">{stock.ticker}</div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`/sector/${sectorId}?stock=${encodeURIComponent(stock.ticker)}`}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-[10px] text-[#93c5fd] hover:bg-slate-900"
            >
              상세 분석 <ExternalLink size={11} />
            </a>
            <button onClick={onClose} className="rounded-md p-2 text-slate-400 hover:bg-white/10 hover:text-slate-200">
              <X size={18} />
            </button>
          </div>
        </header>
        <ChartView ticker={stock.ticker} />
      </div>
    </div>
  );
}

function TierPanel({
  tier,
  sectorName,
  onSelectStock,
}: {
  tier: ValueChainTier;
  sectorName: string;
  onSelectStock: (stock: { ticker: string; name: string }) => void;
}) {
  const theme = TIER_THEMES[tier.level] ?? TIER_THEMES[0];
  const stage = groupName(tier);
  const detail = tier.name.includes("·") ? tier.name.split("·").slice(1).join("·").trim() : tier.name || TIER_LABELS[tier.level];
  const krPlayers = tier.players.filter((p) => /\(\d{6}\)/.test(p));
  const usPlayers = tier.players.filter((p) => /\(\s*[A-Z]{1,6}\s*\)/.test(p) || /^[A-Z]{2,6}$/.test(p));
  const otherPlayers = tier.players.filter((p) => !krPlayers.includes(p) && !usPlayers.includes(p));

  return (
    <div className={`rounded-xl border ${theme.border} ${theme.bg} p-4`}>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr]">
        <div>
          <div className={`text-[11px] font-bold ${theme.tint}`}>T{tier.level} · {stage}</div>
          <div className="mt-1 text-base font-semibold text-[var(--color-text-primary)]">{detail}</div>
          <div className="mt-2 text-[11px] leading-relaxed text-[var(--color-text-muted)]">
            {tierDescription(sectorName, tier.level, stage, detail)}
          </div>
          <TierFacts tier={tier} />
          {tier.is_korean_alpha && (
            <span className="mt-3 inline-flex rounded bg-[#fbbf24]/25 px-2 py-0.5 text-[10px] font-bold text-[#fbbf24]">KR alpha</span>
          )}
        </div>

        <div className="space-y-3">
          {krPlayers.length > 0 && <PlayerGroup title="KR 종목" players={krPlayers} tone="kr" onSelectStock={onSelectStock} />}
          {usPlayers.length > 0 && <PlayerGroup title="US/글로벌" players={usPlayers} tone="us" onSelectStock={onSelectStock} />}
          {otherPlayers.length > 0 && <PlayerGroup title="비상장/원료/시장" players={otherPlayers} tone="other" onSelectStock={onSelectStock} />}
        </div>
      </div>
    </div>
  );
}

function TierFacts({ tier }: { tier: ValueChainTier }) {
  const role = tier.roles?.[0];
  const signal = tier.signals?.[0];
  const signalMap = tier.signal_map ?? [];
  const costs = tier.cost_drivers ?? [];
  const materials = tier.materials ?? [];

  if (!role && !signal && signalMap.length === 0 && costs.length === 0 && materials.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      {role && (
        <div className="rounded-md border border-slate-800 bg-black/20 px-2.5 py-2">
          <div className="text-[10px] font-semibold text-slate-500">역할</div>
          <div className="mt-0.5 text-[11px] leading-relaxed text-slate-300">{role}</div>
        </div>
      )}
      {signal && (
        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-2">
          <div className="text-[10px] font-semibold text-emerald-400">먼저 볼 신호</div>
          <div className="mt-0.5 text-[11px] leading-relaxed text-emerald-100/80">{signal}</div>
        </div>
      )}
      {signalMap.length > 0 && (
        <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-2.5 py-2">
          <div className="text-[10px] font-semibold text-blue-300">신호 전이</div>
          <ul className="mt-1 space-y-1">
            {signalMap.slice(0, 3).map((s) => (
              <li key={s} className="text-[11px] leading-relaxed text-blue-100/80">+ {s}</li>
            ))}
          </ul>
        </div>
      )}
      {costs.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-semibold text-slate-500">원가/병목 변수</div>
          <div className="flex flex-wrap gap-1">
            {costs.map((c) => (
              <span key={c} className="rounded border border-rose-500/25 bg-rose-500/10 px-1.5 py-0.5 text-[10px] text-rose-200">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
      {materials.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-semibold text-slate-500">원재료/용도</div>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {materials.slice(0, 6).map((m) => (
              <div key={m} className="rounded border border-slate-800 bg-white/5 px-2 py-1 text-[10px] leading-relaxed text-slate-300">
                {m}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PlayerGroup({
  title,
  players,
  tone,
  onSelectStock,
}: {
  title: string;
  players: string[];
  tone: "kr" | "us" | "other";
  onSelectStock: (stock: { ticker: string; name: string }) => void;
}) {
  const toneClass = {
    kr: "border-[#fbbf24]/35 bg-[#fbbf24]/12 text-[#fbbf24] hover:bg-[#fbbf24]/20",
    us: "border-[#3b82f6]/30 bg-[#3b82f6]/12 text-[#93c5fd] hover:bg-[#3b82f6]/20",
    other: "border-slate-700 bg-white/5 text-slate-400",
  }[tone];

  return (
    <div>
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {players.map((p) => {
          const ticker = extractTicker(p);
          const name = cleanName(p);
          return (
            <button
              key={p}
              disabled={!ticker}
              onClick={() => ticker && onSelectStock({ ticker, name })}
              className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-[10px] font-medium ${ticker ? toneClass : "cursor-default border-slate-800 bg-white/5 text-slate-500"}`}
            >
              <Boxes size={10} />
              <span>{name}</span>
              {ticker && <ChevronRight size={10} />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function tierDescription(sectorName: string, level: number, stage: string, detail: string) {
  if (sectorName.includes("AI") || sectorName.includes("반도체")) {
    const semi: Record<number, string> = {
      0: "수요가 먼저 움직입니다. 빅테크 capex, 클라우드/AI 추론 수요가 하위 칩·장비·소재로 내려갑니다.",
      1: "설계/Fabless 단계입니다. GPU, ASIC, 네트워크 칩 원청의 수주와 제품 사이클이 핵심입니다.",
      2: "파운드리·메모리 단계입니다. HBM, DRAM, 선단공정 가동률과 패키징 병목을 봅니다.",
      3: "장비 단계입니다. 노광, 증착, 식각, 세정, CMP 같은 공정 장비가 fab 투자와 연결됩니다.",
      4: "소재·부품 단계입니다. PR, 특수가스, 슬러리, 쿼츠/SiC 링, 세정 소재처럼 공정별 소모품이 반복 매출을 만듭니다.",
      5: "원재료·에너지 단계입니다. 전력, 구리, 알루미늄, 희귀가스 병목이 capex 지속성을 좌우합니다.",
    };
    return semi[level] ?? `${stage} 단계의 ${detail} 역할을 확인합니다.`;
  }
  const generic: Record<number, string> = {
    0: "최종 수요입니다. 판매량, 발주, 정책, 소비 흐름이 밸류체인 전체의 출발점입니다.",
    1: "원청/핵심 제품 단계입니다. 가격 결정력과 수주 가시성을 확인합니다.",
    2: "핵심 제조/플랫폼 단계입니다. 가동률, 점유율, 생산능력이 중요합니다.",
    3: "장비/인프라 단계입니다. capex 사이클과 설치 기반을 봅니다.",
    4: "소재/부품 단계입니다. 원가 전가력, 공급 병목, 국산화 프리미엄이 핵심입니다.",
    5: "원재료/정책/에너지 단계입니다. 투입비와 공급망 리스크가 상위 단계 마진을 흔듭니다.",
  };
  return generic[level] ?? `${stage} 단계의 ${detail} 역할을 확인합니다.`;
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
