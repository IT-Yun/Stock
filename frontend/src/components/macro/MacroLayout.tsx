// Macro 페이지 공통 wrapper — 사이드 nav + 본문
import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { Droplet, Activity, Telescope, GitBranch } from "lucide-react";

const NAV = [
  { to: "/commodities", label: "원자재", icon: Droplet, desc: "52개 원자재 → 섹터 시그널" },
  { to: "/indicators", label: "선행 지표", icon: Activity, desc: "27섹터 × 178지표" },
  { to: "/outlook", label: "거시 전망", icon: Telescope, desc: "9개 시나리오 → 섹터 매핑" },
  { to: "/value-chain", label: "Value Chain", icon: GitBranch, desc: "27섹터 Tier 0~5" },
];

export default function MacroLayout({ children, title, subtitle }: {
  children: ReactNode;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="h-full flex flex-col lg:flex-row">
      {/* 사이드 네비 (lg+) / 상단 탭 (모바일) */}
      <nav className="lg:w-56 lg:border-r lg:border-[var(--color-border)] lg:overflow-y-auto shrink-0">
        <div className="hidden lg:block px-4 py-4 border-b border-[var(--color-border)]">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Macro</div>
          <div className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">거시 의사결정</div>
        </div>

        <div className="flex lg:flex-col overflow-x-auto lg:overflow-x-visible border-b border-[var(--color-border)] lg:border-b-0">
          {NAV.map(({ to, label, icon: Icon, desc }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex-shrink-0 lg:flex-shrink flex items-center gap-2 px-3 lg:px-4 py-2.5 lg:py-2 text-xs lg:text-sm transition-colors border-b-2 lg:border-b-0 lg:border-l-2 ${
                  isActive
                    ? "border-[#3b82f6] text-[var(--color-text-primary)] bg-white/5"
                    : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5"
                }`
              }
            >
              <Icon size={14} className="shrink-0" />
              <div className="flex flex-col items-start min-w-0">
                <span className="font-medium whitespace-nowrap">{label}</span>
                <span className="hidden lg:inline text-[10px] text-[var(--color-text-muted)] truncate">{desc}</span>
              </div>
            </NavLink>
          ))}
        </div>
      </nav>

      {/* 본문 */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6">
        <header className="mb-6">
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--color-text-primary)]">{title}</h1>
          {subtitle && <p className="text-xs sm:text-sm text-[var(--color-text-muted)] mt-1">{subtitle}</p>}
        </header>
        {children}
      </div>
    </div>
  );
}
