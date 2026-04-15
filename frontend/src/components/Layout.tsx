import { Link, useLocation } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isFullBleed = location.pathname === "/" || location.pathname.startsWith("/sector/");

  return (
    <div className="h-screen bg-[var(--color-bg-primary)] flex flex-col overflow-hidden">
      <header className="glass-strong h-10 border-b border-[var(--color-border)] flex items-center px-3 shrink-0">
        <Link
          to="/"
          className="text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          미래 먹거리 주식 분석기
        </Link>
      </header>

      <main className={`flex-1 overflow-hidden ${isFullBleed ? "" : "overflow-y-auto p-4 lg:p-6"}`}>
        {children}
      </main>
    </div>
  );
}
