import { Routes, Route, useParams, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import SectorMindMap from "./components/SectorMindMap";
import SectorList from "./components/SectorList";
import SectorDetailPage from "./components/SectorDetailPage";
import { SECTORS } from "./data/sectors";

/** Redirect /stock/:ticker → /sector/:sectorId?stock=ticker */
function StockRedirect() {
  const { ticker } = useParams<{ ticker: string }>();
  const decoded = ticker ?? "";
  const sector = SECTORS.find((s) => s.picks.some((p) => p.ticker === decoded));
  if (sector) {
    return <Navigate to={`/sector/${sector.id}?stock=${encodeURIComponent(decoded)}`} replace />;
  }
  return <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SectorMindMap />} />
        <Route path="/list" element={<SectorList />} />
        <Route path="/sector/:id" element={<SectorDetailPage />} />
        <Route path="/stock/:ticker" element={<StockRedirect />} />
      </Routes>
    </Layout>
  );
}
