import { Link, useLocation } from "react-router-dom";
import { LogOut } from "lucide-react";

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isFullBleed = location.pathname === "/" || location.pathname.startsWith("/sector/");
  const nickname = localStorage.getItem("stock-nickname") || "";

  const handleLogout = () => {
    localStorage.removeItem("stock-nickname");
    localStorage.removeItem("stock-role");
    window.location.href = "/";
  };

  return (
    <div className="h-[100dvh] bg-[var(--color-bg-primary)] flex flex-col overflow-hidden">
      <header className="glass-strong h-10 sm:h-10 border-b border-[var(--color-border)] flex items-center justify-between px-3 shrink-0">
        <Link
          to="/"
          className="text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          미래 먹거리 주식 분석기
        </Link>

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--color-text-muted)] hidden sm:inline">{nickname}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[#ef4444] transition-colors"
            title="로그아웃"
          >
            <LogOut size={12} />
          </button>
        </div>
      </header>

      <main className={`flex-1 overflow-hidden ${isFullBleed ? "" : "overflow-y-auto p-3 sm:p-4 lg:p-6"}`}>
        {children}
      </main>
    </div>
  );
}
