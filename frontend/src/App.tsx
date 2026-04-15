import { Routes, Route, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import SectorList from "./components/SectorList";
import ChartView from "./components/ChartView";
import AnalysisDashboard from "./components/AnalysisDashboard";
import NewsPanel from "./components/NewsPanel";
import CommodityTracker from "./components/CommodityTracker";
import StockCard from "./components/StockCard";
import { fetchSectorStocks, fetchSectors } from "./api/client";
import type { Stock, Sector } from "./types";

function SectorDetailPage() {
  const { name } = useParams<{ name: string }>();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [sector, setSector] = useState<Sector | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sectorName = name ?? "";

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchSectorStocks(sectorName), fetchSectors()])
      .then(([stockData, sectors]) => {
        setStocks(stockData);
        const found = sectors.find((s) => s.name === sectorName || s.name.replace(/[/ ]/g, "_") === sectorName);
        setSector(found ?? null);
        setError(null);
      })
      .catch(() => setError("섹터 데이터를 불러오는 데 실패했습니다."))
      .finally(() => setLoading(false));
  }, [sectorName]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-[var(--color-bg-hover)] rounded w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 bg-[var(--color-bg-hover)] rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <p className="text-[var(--color-accent-red)]">{error}</p>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">{sector?.name ?? sectorName}</h2>
      {sector?.description && (
        <p className="text-sm text-[var(--color-text-secondary)]">{sector.description}</p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stocks.map((stock) => (
          <StockCard key={stock.ticker} stock={stock} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <NewsPanel sectorName={sectorName} />
        <CommodityTracker relatedCommodities={sector?.relatedCommodities} />
      </div>
    </div>
  );
}

function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const decodedTicker = ticker ?? "";

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold font-mono">{decodedTicker}</h2>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-4">
          <ChartView ticker={decodedTicker} />
        </div>
        <div className="space-y-4">
          <AnalysisDashboard ticker={decodedTicker} />
          <NewsPanel keyword={decodedTicker} />
          <CommodityTracker />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SectorList />} />
        <Route path="/sector/:name" element={<SectorDetailPage />} />
        <Route path="/stock/:ticker" element={<StockDetailPage />} />
      </Routes>
    </Layout>
  );
}
