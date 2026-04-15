import { useEffect, useState } from "react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchChartData } from "@/api/client";
import type { ChartDataPoint } from "@/types";

const periods = [
  { label: "1개월", value: "1mo" },
  { label: "3개월", value: "3mo" },
  { label: "6개월", value: "6mo" },
  { label: "1년", value: "1y" },
] as const;

interface ChartViewProps {
  ticker: string;
}

export default function ChartView({ ticker }: ChartViewProps) {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [period, setPeriod] = useState<string>("3mo");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchChartData(ticker, period)
      .then((chartData) => {
        setData(chartData);
        setError(null);
      })
      .catch(() => setError("차트 데이터를 불러오는 데 실패했습니다."))
      .finally(() => setLoading(false));
  }, [ticker, period]);

  if (loading) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-6">
        <div className="h-80 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[var(--color-accent-blue)]" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-6">
        <p className="text-[var(--color-accent-red)] text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-[var(--color-text-secondary)]">기간:</span>
        {periods.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              period === p.value
                ? "bg-[var(--color-accent-blue)] text-white"
                : "bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3">주가 차트</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
              tickFormatter={(v: string) => v.slice(5)}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                color: "var(--color-text-primary)",
              }}
              formatter={(value: number, name: string) => {
                const labels: Record<string, string> = {
                  close: "종가",
                  open: "시가",
                  high: "고가",
                  low: "저가",
                  sma_20: "SMA 20",
                  sma_50: "SMA 50",
                  bollinger_upper: "볼린저 상단",
                  bollinger_lower: "볼린저 하단",
                };

                return [typeof value === "number" ? value.toFixed(2) : value, labels[name] ?? name];
              }}
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke="var(--color-accent-blue)"
              fill="var(--color-accent-blue)"
              fillOpacity={0.08}
              strokeWidth={2}
            />
            <Line type="monotone" dataKey="close" stroke="var(--color-accent-blue)" strokeWidth={2} dot={false} />
            <Line
              type="monotone"
              dataKey="sma_20"
              stroke="#f59e0b"
              strokeWidth={1}
              dot={false}
              strokeDasharray="3 3"
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="sma_50"
              stroke="#8b5cf6"
              strokeWidth={1}
              dot={false}
              strokeDasharray="4 2"
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3">거래량</h3>
        <ResponsiveContainer width="100%" height={120}>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
              tickFormatter={(v: string) => v.slice(5)}
            />
            <YAxis
              tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
              tickFormatter={(v: number) => `${(v / 1e6).toFixed(0)}M`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                color: "var(--color-text-primary)",
              }}
              formatter={(value: number) => [value.toLocaleString(), "거래량"]}
            />
            <Bar dataKey="volume" fill="var(--color-accent-blue)" fillOpacity={0.4} barSize={3} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
