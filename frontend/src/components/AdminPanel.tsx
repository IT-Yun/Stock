import { useState, useEffect, useCallback } from "react";
import { UserPlus, Trash2, Users, LogOut, Search } from "lucide-react";

interface MemberData {
  admins: string[];
  members: string[];
}

export default function AdminPanel() {
  const [data, setData] = useState<MemberData>({ admins: [], members: [] });
  const [newName, setNewName] = useState("");
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const nickname = localStorage.getItem("stock-nickname") || "";

  const fetchMembers = useCallback(async () => {
    try {
      const res = await fetch("/api/members/list");
      const json = await res.json();
      setData(json);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  const showMessage = (text: string, type: "success" | "error") => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleAdd = async () => {
    const name = newName.trim();
    if (!name) return;
    setLoading(true);
    try {
      const res = await fetch("/api/members/add", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Auth-Nickname": encodeURIComponent(nickname),
        },
        body: JSON.stringify({ nickname: name }),
      });
      const json = await res.json();
      if (res.ok) {
        showMessage(json.message, "success");
        setNewName("");
        fetchMembers();
      } else {
        showMessage(json.detail || "추가 실패", "error");
      }
    } catch {
      showMessage("서버 연결 실패", "error");
    }
    setLoading(false);
  };

  const handleRemove = async (name: string) => {
    if (!confirm(`'${name}' 멤버를 삭제하시겠습니까?`)) return;
    try {
      const res = await fetch("/api/members/remove", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-Auth-Nickname": encodeURIComponent(nickname),
        },
        body: JSON.stringify({ nickname: name }),
      });
      const json = await res.json();
      if (res.ok) {
        showMessage(json.message, "success");
        fetchMembers();
      } else {
        showMessage(json.detail || "삭제 실패", "error");
      }
    } catch {
      showMessage("서버 연결 실패", "error");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("stock-nickname");
    window.location.href = "/";
  };

  const filtered = data.members.filter((m) =>
    m.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-[100dvh] w-screen bg-[var(--color-bg-primary)] bg-dot-grid overflow-hidden flex flex-col">
      {/* Header */}
      <header className="glass-strong h-12 border-b border-[var(--color-border)] flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-2">
          <Users size={16} className="text-[#3b82f6]" />
          <span className="text-sm font-bold text-[var(--color-text-primary)]">멤버 관리</span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[#ef4444] transition-colors"
        >
          <LogOut size={14} />
          로그아웃
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="max-w-lg mx-auto space-y-5">
          {/* Toast message */}
          {message && (
            <div className={`px-4 py-3 rounded-xl text-sm font-medium border ${
              message.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-red-500/10 border-red-500/30 text-red-400"
            }`}>
              {message.text}
            </div>
          )}

          {/* Add member */}
          <div className="glass rounded-2xl border border-white/10 p-5" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>
            <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
              멤버 추가
            </h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                placeholder="새 멤버 닉네임 입력"
                className="flex-1 px-4 py-2.5 rounded-xl bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[#3b82f6] transition-colors"
                autoFocus
              />
              <button
                onClick={handleAdd}
                disabled={loading || !newName.trim()}
                className="px-4 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-1.5"
                style={{
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  boxShadow: "0 4px 16px rgba(59,130,246,0.3)",
                }}
              >
                <UserPlus size={16} />
                추가
              </button>
            </div>
          </div>

          {/* Member list */}
          <div className="glass rounded-2xl border border-white/10 p-5" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                등록된 멤버 ({data.members.length}명)
              </h2>
            </div>

            {/* Search */}
            <div className="relative mb-3">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="멤버 검색..."
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[#3b82f6] transition-colors"
              />
            </div>

            <div className="space-y-1 max-h-[50vh] overflow-y-auto">
              {filtered.map((member) => (
                <div
                  key={member}
                  className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/5 transition-colors group"
                >
                  <span className="text-sm text-[var(--color-text-primary)]">{member}</span>
                  <button
                    onClick={() => handleRemove(member)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-[var(--color-text-muted)] hover:text-red-400 transition-all"
                    title="삭제"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {filtered.length === 0 && (
                <p className="text-xs text-[var(--color-text-muted)] text-center py-4">
                  {search ? "검색 결과가 없습니다" : "등록된 멤버가 없습니다"}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
