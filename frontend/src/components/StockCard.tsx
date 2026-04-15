import { Link } from "react-router-dom";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import type { Stock } from "@/types";

function generateSparkline(price: number, changePct: number) {
  const points = 20;
  const data = [];
  const change = price * (changePct / 100);
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
  const pct = stock.change_percent ?? 0;
  const isPositive = pct >= 0;
  const sparkData = generateSparkline(stock.price, pct);
  const isKRX = stock.ticker.endsWith(".KS") || stock.ticker.endsWith(".KQ");
  const currency = isKRX ? "₩" : "$";

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
          {currency}{stock.price.toLocaleString(undefined, { minimumFractionDigits: isKRX ? 0 : 2, maximumFractionDigits: isKRX ? 0 : 2 })}
        </p>
        <p
          className={`text-sm font-semibold ${
            isPositive ? "text-[var(--color-accent-green)]" : "text-[var(--color-accent-red)]"
          }`}
        >
          {isPositive ? "+" : ""}
          {pct.toFixed(2)}%
        </p>
      </div>
    </Link>
  );
}
