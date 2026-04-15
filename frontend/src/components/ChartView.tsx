import { useEffect, useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  ReferenceLine,
} from "recharts";
import { fetchChartData } from "@/api/client";
import type { ChartDataPoint } from "@/types";

const periods = ["1M", "3M", "6M", "1Y"] as const;

interface ChartViewProps {
  ticker: string;
}

export default function ChartView({ ticker }: ChartViewProps) {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [period, setPeriod] = useState<string>("6M");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchChartData(ticker, period)
      .then((d) => {
        setData(d);
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
      {/* Period selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-[var(--color-text-secondary)]">기간:</span>
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              period === p
                ? "bg-[var(--color-accent-blue)] text-white"
                : "bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Main price chart with Bollinger Bands and SMAs */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3">
          주가 차트
        </h3>
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
                  sma20: "SMA 20",
                  sma50: "SMA 50",
                  sma200: "SMA 200",
                  bollingerUpper: "볼린저 상단",
                  bollingerLower: "볼린저 하단",
                };
                return [value.toFixed(2), labels[name] ?? name];
              }}
            />
            {/* Bollinger Bands */}
            <Area
              type="monotone"
              dataKey="bollingerUpper"
              stroke="none"
              fill="var(--color-accent-blue)"
              fillOpacity={0.05}
            />
            <Area
              type="monotone"
              dataKey="bollingerLower"
              stroke="none"
              fill="var(--color-bg-primary)"
              fillOpacity={1}
            />
            {/* Candlestick approximation: bar from low to high */}
            <Bar
              dataKey="low"
              fill="transparent"
              stackId="candle"
            />
            <Bar
              dataKey={(d: ChartDataPoint) => d.high - d.low}
              stackId="candle"
              fill="var(--color-text-muted)"
              fillOpacity={0.3}
              barSize={2}
            />
            {/* Close price line */}
            <Line
              type="monotone"
              dataKey="close"
              stroke="var(--color-text-primary)"
              strokeWidth={2}
              dot={false}
            />
            {/* SMA lines */}
            <Line
              type="monotone"
              dataKey="sma20"
              stroke="#f59e0b"
              strokeWidth={1}
              dot={false}
              strokeDasharray="2 2"
            />
            <Line
              type="monotone"
              dataKey="sma50"
              stroke="#8b5cf6"
              strokeWidth={1}
              dot={false}
              strokeDasharray="4 2"
            />
            <Line
              type="monotone"
              dataKey="sma200"
              stroke="#ec4899"
              strokeWidth={1}
              dot={false}
              strokeDasharray="6 2"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI Chart */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3">
          RSI
        </h3>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
              tickFormatter={(v: string) => v.slice(5)}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[30, 50, 70]}
              tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                color: "var(--color-text-primary)",
              }}
              formatter={(value: number) => [value.toFixed(1), "RSI"]}
            />
            <ReferenceLine y={70} stroke="var(--color-accent-red)" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="var(--color-accent-green)" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="rsi"
              stroke="var(--color-accent-blue)"
              strokeWidth={1.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* MACD Chart */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3">
          MACD
        </h3>
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
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                color: "var(--color-text-primary)",
              }}
            />
            <ReferenceLine y={0} stroke="var(--color-text-muted)" />
            <Bar
              dataKey="macdHistogram"
              fill="var(--color-accent-blue)"
              fillOpacity={0.5}
              barSize={3}
            />
            <Line
              type="monotone"
              dataKey="macdLine"
              stroke="var(--color-accent-blue)"
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="macdSignal"
              stroke="var(--color-accent-red)"
              strokeWidth={1.5}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
