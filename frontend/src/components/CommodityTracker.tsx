import { useEffect, useState } from "react";
import { fetchCommodities } from "@/api/client";
import type { CommodityPrice } from "@/types";

interface CommodityTrackerProps {
  relatedCommodities?: string[];
}

export default function CommodityTracker({ relatedCommodities }: CommodityTrackerProps) {
  const [commodities, setCommodities] = useState<CommodityPrice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchCommodities()
      .then((data) => {
        setCommodities(data);
        setError(null);
      })
      .catch(() => setError("원자재 데이터를 불러오는 데 실패했습니다."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5">
        <h3 className="text-lg font-bold mb-4">원자재 시세</h3>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-[var(--color-bg-hover)] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5">
        <h3 className="text-lg font-bold mb-4">원자재 시세</h3>
        <p className="text-[var(--color-accent-red)] text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5">
      <h3 className="text-lg font-bold mb-4">원자재 시세</h3>
      <div className="space-y-1">
        {commodities.map((c: any) => {
          const pct = c.change_percent ?? c.changePercent ?? 0;
          const isPositive = pct >= 0;
          const displayName = c.nameKo ?? c.name;
          const isRelated = relatedCommodities?.includes(c.name) || relatedCommodities?.includes(displayName);
          return (
            <div
              key={c.name}
              className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                isRelated
                  ? "bg-[var(--color-accent-blue)]/10 border border-[var(--color-accent-blue)]/20"
                  : "hover:bg-[var(--color-bg-hover)]"
              }`}
            >
              <div className="flex items-center gap-2">
                {isRelated && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-blue)]" />
                )}
                <span className="text-sm font-medium text-[var(--color-text-primary)]">
                  {displayName}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-mono text-[var(--color-text-secondary)]">
                  {c.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {c.unit ?? ""}
                </span>
                <span
                  className={`text-xs font-semibold min-w-[60px] text-right ${
                    isPositive
                      ? "text-[var(--color-accent-green)]"
                      : "text-[var(--color-accent-red)]"
                  }`}
                >
                  {isPositive ? "+" : ""}
                  {pct.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
