import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";
import Layout from "./components/Layout";
import { SECTORS } from "./data/sectors";

const SectorMindMap = lazy(() => import("./components/SectorMindMap"));
const SectorList = lazy(() => import("./components/SectorList"));
const SectorDetailPage = lazy(() => import("./components/SectorDetailPage"));

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
      <Suspense
        fallback={
          <div className="h-full flex items-center justify-center text-sm text-[var(--color-text-secondary)]">
            화면 로딩 중...
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<SectorMindMap />} />
          <Route path="/list" element={<SectorList />} />
          <Route path="/sector/:id" element={<SectorDetailPage />} />
          <Route path="/stock/:ticker" element={<StockRedirect />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
