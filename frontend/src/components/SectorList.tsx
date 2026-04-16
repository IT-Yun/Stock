import { useEffect, useState } from "react";
import { fetchSectors } from "@/api/client";
import { useLanguage } from "@/i18n";
import StockCard from "./StockCard";
import type { Sector } from "@/types";

export default function SectorList() {
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();

  useEffect(() => {
    setLoading(true);
    fetchSectors()
      .then((data) => {
        setSectors(data);
        setError(null);
      })
      .catch(() => setError(t("sectorLoadFailed")))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-6 animate-pulse"
          >
            <div className="h-6 bg-[var(--color-bg-hover)] rounded w-32 mb-2" />
            <div className="h-4 bg-[var(--color-bg-hover)] rounded w-64 mb-4" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {[1, 2, 3].map((j) => (
                <div key={j} className="h-24 bg-[var(--color-bg-hover)] rounded-xl" />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-[var(--color-accent-red)] text-lg mb-2">{t("error")}</p>
          <p className="text-[var(--color-text-secondary)]">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">{t("futureGrowthSectors")}</h2>
      {sectors.map((sector) => (
        <div
          key={sector.name}
          className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5"
        >
          <h3 className="text-lg font-bold text-[var(--color-accent-blue)] mb-1">
            {sector.name}
          </h3>
          <p className="text-sm text-[var(--color-text-secondary)] mb-4">
            {sector.description}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {sector.stocks.slice(0, 3).map((stock) => (
              <StockCard key={stock.ticker} stock={stock} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
