import { useState, useEffect } from "react";
import { TrendingUp } from "lucide-react";

// 허용된 닉네임 목록 — 여기에 추가/삭제하면 됩니다
const ALLOWED_NICKNAMES = [
  "admin",
  "seungyun",
  "이승윤",
  "fan",
  "test",
];

export default function LoginGate({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Check if already logged in
  useEffect(() => {
    const saved = localStorage.getItem("stock-nickname");
    if (saved && ALLOWED_NICKNAMES.includes(saved.toLowerCase())) {
      setAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleLogin = () => {
    const trimmed = nickname.trim();
    if (!trimmed) {
      setError("닉네임을 입력해주세요");
      return;
    }
    if (ALLOWED_NICKNAMES.includes(trimmed.toLowerCase())) {
      localStorage.setItem("stock-nickname", trimmed.toLowerCase());
      setAuthenticated(true);
      setError("");
    } else {
      setError("접근 권한이 없는 닉네임입니다");
    }
  };

  if (loading) return null;
  if (authenticated) return <>{children}</>;

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[var(--color-bg-primary)] bg-dot-grid">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full" style={{ background: "radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)" }} />
      </div>

      <div className="relative z-10 w-full max-w-sm px-6">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 rounded-3xl mx-auto flex items-center justify-center mb-4" style={{
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            boxShadow: "0 12px 40px rgba(59,130,246,0.3)",
          }}>
            <TrendingUp size={36} color="white" strokeWidth={2.5} />
          </div>
          <h1 className="text-3xl font-black text-[var(--color-text-primary)]">Stock Future</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-2">AI 기반 실시간 주식 분석 플랫폼</p>
        </div>

        {/* Login form */}
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
            className="w-full mt-4 py-3 rounded-xl text-sm font-bold text-white transition-all hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              boxShadow: "0 4px 16px rgba(59,130,246,0.3)",
            }}
          >
            로그인
          </button>
        </div>

        <p className="text-center text-[10px] text-[var(--color-text-muted)] mt-6">
          Powered by AI Deep Analysis Engine
        </p>
      </div>
    </div>
  );
}
