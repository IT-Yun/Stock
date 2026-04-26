import { Link } from "react-router-dom";
import { LogOut, Globe } from "lucide-react";
import { useLanguage } from "@/i18n";

export default function Layout({ children }: { children: React.ReactNode }) {
  const nickname = localStorage.getItem("stock-nickname") || "";
  const { lang, toggleLang, t } = useLanguage();

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
          {t("siteTitle")}
        </Link>

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--color-text-muted)] hidden sm:inline">{nickname}</span>
          <button
            onClick={toggleLang}
            className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[#3b82f6] transition-colors px-1.5 py-0.5 rounded-md hover:bg-white/5"
            title={lang === "ko" ? "Switch to English" : "한국어로 전환"}
          >
            <Globe size={11} />
            <span className="font-bold">{lang === "ko" ? "EN" : "KR"}</span>
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[#ef4444] transition-colors"
            title={t("logout")}
          >
            <LogOut size={12} />
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
