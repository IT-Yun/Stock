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
  const confidence = analysis.confidence ?? analysis.confidence_score ?? 0;
  const macdSignal = ind.macd_signal ?? ind.macdSignal ?? null;
  const bollingerLower = ind.bollinger_lower ?? ind.bollingerLower ?? null;
  const bollingerUpper = ind.bollinger_upper ?? ind.bollingerUpper ?? null;
  const bollingerMiddle = ind.bollinger_middle ?? ind.bollingerMiddle ?? null;
  const sma20 = ind.sma_20 ?? ind.sma20 ?? null;
  const sma50 = ind.sma_50 ?? ind.sma50 ?? null;

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5 space-y-5">
      <h3 className="text-lg font-bold">매매 분석</h3>

      <div className="flex items-center gap-4">
        <span
          className="px-4 py-2 rounded-lg text-lg font-bold"
          style={{ backgroundColor: recColor, color: "#fff" }}
        >
          {recLabel}
        </span>
        <div className="flex-1">
          <p className="text-xs text-[var(--color-text-muted)] mb-1">신뢰도 {confidence.toFixed(0)}%</p>
          <div className="w-full bg-[var(--color-bg-hover)] rounded-full h-2.5">
            <div
              className="h-2.5 rounded-full transition-all"
              style={{ width: `${confidence}%`, backgroundColor: recColor }}
            />
          </div>
        </div>
      </div>

      {ind.buy_sell_signal && (
        <p className="text-sm text-[var(--color-text-secondary)]">시그널: {ind.buy_sell_signal}</p>
      )}

      <div className="space-y-3">
        {ind.rsi != null && (
          <IndicatorRow
            label="RSI"
            value={ind.rsi.toFixed(1)}
            interpretation={ind.rsi > 70 ? "과매수" : ind.rsi < 30 ? "과매도" : "중립"}
          />
        )}
        {ind.macd != null && macdSignal != null && (
          <IndicatorRow
            label="MACD"
            value={`${ind.macd.toFixed(2)} / ${macdSignal.toFixed(2)}`}
            interpretation={ind.macd > macdSignal ? "상승 모멘텀" : "하락 모멘텀"}
          />
        )}
        {bollingerLower != null && bollingerUpper != null && (
          <IndicatorRow
            label="볼린저 밴드"
            value={`${bollingerLower.toFixed(1)} - ${bollingerUpper.toFixed(1)}`}
            interpretation={`중심: ${bollingerMiddle?.toFixed(1) ?? "N/A"}`}
          />
        )}
        {sma20 != null && (
          <IndicatorRow
            label="이동평균"
            value={`SMA20: ${sma20.toFixed(1)}`}
            interpretation={`SMA50: ${sma50?.toFixed(1) ?? "N/A"}`}
          />
        )}
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
