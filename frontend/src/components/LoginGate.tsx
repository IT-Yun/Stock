import { useState, useEffect } from "react";
import { TrendingUp } from "lucide-react";

export function isAdmin(): boolean {
  return localStorage.getItem("stock-role") === "admin";
}

export default function LoginGate({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  // Check if already logged in (verify with server)
  useEffect(() => {
    const saved = localStorage.getItem("stock-nickname");
    if (!saved) {
      setLoading(false);
      return;
    }
    fetch("/api/members/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname: saved }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.allowed) {
          localStorage.setItem("stock-role", data.role);
          setAuthenticated(true);
          // Record visit silently
          fetch("/api/members/visit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nickname: saved }),
          }).catch(() => {});
        } else {
          localStorage.removeItem("stock-nickname");
          localStorage.removeItem("stock-role");
        }
      })
      .catch(() => {
        // Offline fallback: trust saved session
        setAuthenticated(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = async () => {
    const trimmed = nickname.trim();
    if (!trimmed) {
      setError("닉네임을 입력해주세요");
      return;
    }

    setChecking(true);
    try {
      const res = await fetch("/api/members/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nickname: trimmed }),
      });
      const data = await res.json();

      if (data.allowed) {
        localStorage.setItem("stock-nickname", trimmed);
        localStorage.setItem("stock-role", data.role);
        setAuthenticated(true);
        setError("");
        // Record visit
        fetch("/api/members/visit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nickname: trimmed }),
        }).catch(() => {});
        if (window.location.pathname !== "/") {
          window.location.href = "/";
        }
      } else {
        setError("접근 권한이 없는 닉네임입니다");
      }
    } catch {
      setError("서버 연결에 실패했습니다");
    }
    setChecking(false);
  };

  if (loading) return null;
  if (authenticated) return <>{children}</>;

  return (
    <div className="h-[100dvh] w-screen flex items-center justify-center bg-[var(--color-bg-primary)] bg-dot-grid">
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] sm:w-[600px] sm:h-[600px] rounded-full" style={{ background: "radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)" }} />
      </div>

      <div className="relative z-10 w-full max-w-sm px-5 sm:px-6">
        <div className="text-center mb-6 sm:mb-8">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl sm:rounded-3xl mx-auto flex items-center justify-center mb-3 sm:mb-4" style={{
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            boxShadow: "0 12px 40px rgba(59,130,246,0.3)",
          }}>
            <TrendingUp size={28} color="white" strokeWidth={2.5} className="sm:hidden" />
            <TrendingUp size={36} color="white" strokeWidth={2.5} className="hidden sm:block" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-[var(--color-text-primary)]">Stock Future</h1>
          <p className="text-xs sm:text-sm text-[var(--color-text-muted)] mt-1.5 sm:mt-2">AI 기반 실시간 주식 분석 플랫폼</p>
        </div>

        <div className="glass rounded-2xl border border-white/10 p-6" style={{ boxShadow: "0 16px 48px rgba(0,0,0,0.3)" }}>
          <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">닉네임</label>
          <input
            type="text"
            value={nickname}
            onChange={(e) => { setNickname(e.target.value); setError(""); }}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="닉네임을 입력하세요"
            className="w-full mt-2 px-4 py-3 rounded-xl bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[#3b82f6] transition-colors"
            autoFocus
          />
          {error && (
            <p className="text-xs text-[#ef4444] mt-2 font-medium">{error}</p>
          )}
          <button
            onClick={handleLogin}
            disabled={checking}
            className="w-full mt-4 py-3 rounded-xl text-sm font-bold text-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
            style={{
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              boxShadow: "0 4px 16px rgba(59,130,246,0.3)",
            }}
          >
            {checking ? "확인 중..." : "로그인"}
          </button>
        </div>

        <p className="text-center text-[10px] text-[var(--color-text-muted)] mt-6">
          Powered by AI Deep Analysis Engine
        </p>
      </div>
    </div>
  );
}
