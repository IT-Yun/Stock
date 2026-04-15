import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

const sectors = [
  { name: "반도체", path: "/sector/반도체" },
  { name: "로봇", path: "/sector/로봇" },
  { name: "생명공학/유전자", path: "/sector/생명공학_유전자" },
  { name: "SMR 소형원전", path: "/sector/SMR_소형원전" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-30 w-64 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] transform transition-transform lg:transform-none ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="p-4 border-b border-[var(--color-border)]">
          <Link to="/" className="block" onClick={() => setSidebarOpen(false)}>
            <h1 className="text-lg font-bold text-[var(--color-accent-blue)]">
              미래 먹거리
            </h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              주식 분석기
            </p>
          </Link>
        </div>
        <nav className="p-3 space-y-1">
          <p className="px-3 py-2 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            섹터
          </p>
          {sectors.map((sector) => {
            const isActive = location.pathname === sector.path;
            return (
              <Link
                key={sector.name}
                to={sector.path}
                onClick={() => setSidebarOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--color-accent-blue)] text-white"
                    : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                {sector.name}
              </Link>
            );
          })}
          <div className="pt-3">
            <Link
              to="/"
              onClick={() => setSidebarOpen(false)}
              className="block px-3 py-2 rounded-lg text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              전체 보기
            </Link>
          </div>
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] flex items-center px-4 shrink-0">
          <button
            className="lg:hidden mr-3 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            onClick={() => setSidebarOpen(true)}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">
            미래 먹거리 주식 분석기
          </h2>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
