import { useEffect, useState } from "react";
import { fetchAnalysis } from "@/api/client";
import type { AnalysisResult } from "@/types";

interface AnalysisDashboardProps {
  ticker: string;
}

const recommendationLabels: Record<string, string> = {
  strong_buy: "강력 매수",
  buy: "매수",
  hold: "보유",
  sell: "매도",
  strong_sell: "강력 매도",
};

const recommendationColors: Record<string, string> = {
  strong_buy: "var(--color-strong-buy)",
  buy: "var(--color-buy)",
  hold: "var(--color-hold)",
  sell: "var(--color-sell)",
  strong_sell: "var(--color-strong-sell)",
};

export default function AnalysisDashboard({ ticker }: AnalysisDashboardProps) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchAnalysis(ticker)
      .then((d) => {
        setAnalysis(d);
        setError(null);
      })
      .catch(() => setError("분석 데이터를 불러오는 데 실패했습니다."))
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-[var(--color-bg-hover)] rounded w-40 mb-4" />
        <div className="h-24 bg-[var(--color-bg-hover)] rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-[var(--color-bg-hover)] rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-6">
        <p className="text-[var(--color-accent-red)] text-center">
          {error ?? "데이터를 불러올 수 없습니다."}
        </p>
      </div>
    );
  }

  const recColor = recommendationColors[analysis.recommendation] ?? "var(--color-text-primary)";
  const recLabel = recommendationLabels[analysis.recommendation] ?? analysis.recommendation;
  const ind = analysis.indicators;

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5 space-y-5">
      <h3 className="text-lg font-bold">매매 분석</h3>

      {/* Recommendation badge + confidence */}
      <div className="flex items-center gap-4">
        <span
          className="px-4 py-2 rounded-lg text-lg font-bold"
          style={{ backgroundColor: recColor, color: "#fff" }}
        >
          {recLabel}
        </span>
        <div className="flex-1">
          <p className="text-xs text-[var(--color-text-muted)] mb-1">
            신뢰도 {(analysis.confidence * 100).toFixed(0)}%
          </p>
          <div className="w-full bg-[var(--color-bg-hover)] rounded-full h-2.5">
            <div
              className="h-2.5 rounded-full transition-all"
              style={{
                width: `${analysis.confidence * 100}%`,
                backgroundColor: recColor,
              }}
            />
          </div>
        </div>
      </div>

      {/* Summary */}
      <p className="text-sm text-[var(--color-text-secondary)]">
        {analysis.summary}
      </p>

      {/* Indicators breakdown */}
      <div className="space-y-3">
        <IndicatorRow
          label="RSI"
          value={ind.rsi.toFixed(1)}
          interpretation={ind.rsiSignal}
        />
        <IndicatorRow
          label="MACD"
          value={`${ind.macdLine.toFixed(2)} / ${ind.macdSignal.toFixed(2)}`}
          interpretation={ind.macdInterpretation}
        />
        <IndicatorRow
          label="볼린저 밴드"
          value={`${ind.bollingerLower.toFixed(1)} - ${ind.bollingerUpper.toFixed(1)}`}
          interpretation={ind.bollingerPosition}
        />
        <IndicatorRow
          label="이동평균 추세"
          value={`SMA20: ${ind.sma20.toFixed(1)}`}
          interpretation={ind.smaTrend}
        />
      </div>
    </div>
  );
}

function IndicatorRow({
  label,
  value,
  interpretation,
}: {
  label: string;
  value: string;
  interpretation: string;
}) {
  return (
    <div className="flex items-center justify-between bg-[var(--color-bg-primary)] rounded-lg px-4 py-3">
      <div>
        <p className="text-sm font-medium text-[var(--color-text-primary)]">
          {label}
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">{interpretation}</p>
      </div>
      <p className="text-sm font-mono text-[var(--color-text-secondary)]">
        {value}
      </p>
    </div>
  );
}
