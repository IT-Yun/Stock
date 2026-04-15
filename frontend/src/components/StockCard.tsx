import { Link } from "react-router-dom";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import type { Stock } from "@/types";

// Generate simple sparkline mock data based on current price/change
function generateSparkline(price: number, change: number) {
  const points = 20;
  const data = [];
  const startPrice = price - change;
  for (let i = 0; i < points; i++) {
    const progress = i / (points - 1);
    const noise = (Math.random() - 0.5) * Math.abs(change) * 0.5;
    data.push({ v: startPrice + change * progress + noise });
  }
  return data;
}

interface StockCardProps {
  stock: Stock;
}

export default function StockCard({ stock }: StockCardProps) {
  const isPositive = stock.changePercent >= 0;
  const sparkData = generateSparkline(stock.price, stock.change);

  return (
    <Link
      to={`/stock/${encodeURIComponent(stock.ticker)}`}
      className="block bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4 hover:bg-[var(--color-bg-hover)] transition-colors"
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-xs text-[var(--color-text-muted)] font-mono">
            {stock.ticker}
          </p>
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {stock.name}
          </p>
        </div>
        <div className="w-16 h-8">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke={isPositive ? "var(--color-accent-green)" : "var(--color-accent-red)"}
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="flex items-end justify-between">
        <p className="text-lg font-bold text-[var(--color-text-primary)]">
          ${stock.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
        <p
          className={`text-sm font-semibold ${
            isPositive ? "text-[var(--color-accent-green)]" : "text-[var(--color-accent-red)]"
          }`}
        >
          {isPositive ? "+" : ""}
          {stock.changePercent.toFixed(2)}%
        </p>
      </div>
    </Link>
  );
}
