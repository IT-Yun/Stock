import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import LoginGate, { isAdmin } from "./components/LoginGate";

const AdminPanel = lazy(() => import("./components/AdminPanel"));
const MacroCommodities = lazy(() => import("./components/macro/Commodities"));
const MacroIndicators = lazy(() => import("./components/macro/Indicators"));
const MacroOutlook = lazy(() => import("./components/macro/Outlook"));
const MacroValueChain = lazy(() => import("./components/macro/ValueChain"));

export default function App() {
  return (
    <LoginGate>
      {isAdmin() ? (
        <Suspense fallback={<div className="h-full flex items-center justify-center text-sm text-[var(--color-text-secondary)]">Loading...</div>}>
          <AdminPanel />
        </Suspense>
      ) : (
        <Layout>
          <Suspense
            fallback={
              <div className="h-full flex items-center justify-center text-sm text-[var(--color-text-secondary)]">
                Loading...
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Navigate to="/commodities" replace />} />
              <Route path="/commodities" element={<MacroCommodities />} />
              <Route path="/indicators" element={<MacroIndicators />} />
              <Route path="/outlook" element={<MacroOutlook />} />
              <Route path="/value-chain" element={<MacroValueChain />} />
              {/* 구버전 URL backward-compat */}
              <Route path="/macro" element={<Navigate to="/commodities" replace />} />
              <Route path="/macro/commodities" element={<Navigate to="/commodities" replace />} />
              <Route path="/macro/indicators" element={<Navigate to="/indicators" replace />} />
              <Route path="/macro/outlook" element={<Navigate to="/outlook" replace />} />
              <Route path="/macro/value-chain" element={<Navigate to="/value-chain" replace />} />
              <Route path="*" element={<Navigate to="/commodities" replace />} />
            </Routes>
          </Suspense>
        </Layout>
      )}
    </LoginGate>
  );
}
