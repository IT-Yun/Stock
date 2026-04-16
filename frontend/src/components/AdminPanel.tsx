import { useState, useEffect, useCallback } from "react";
import { UserPlus, Trash2, Users, LogOut, Search, BarChart3, Clock, Eye, Globe } from "lucide-react";
import { useLanguage } from "@/i18n";

interface MemberData {
  admins: string[];
  members: string[];
}

interface VisitStat {
  nickname: string;
  visit_count: number;
  last_visit: string | null;
}

interface VisitStats {
  stats: VisitStat[];
  total_visits: number;
}

function timeAgo(iso: string | null, lang: "ko" | "en"): string {
  if (!iso) return "-";
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return lang === "ko" ? "방금 전" : "Just now";
  if (min < 60) return lang === "ko" ? `${min}분 전` : `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return lang === "ko" ? `${hr}시간 전` : `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return lang === "ko" ? `${day}일 전` : `${day}d ago`;
  return lang === "ko" ? `${Math.floor(day / 30)}개월 전` : `${Math.floor(day / 30)}mo ago`;
}

export default function AdminPanel() {
  const { lang, toggleLang, t } = useLanguage();
  const [data, setData] = useState<MemberData>({ admins: [], members: [] });
  const [visitStats, setVisitStats] = useState<VisitStats>({ stats: [], total_visits: 0 });
  const [newName, setNewName] = useState("");
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"members" | "visits">("visits");

  const nickname = localStorage.getItem("stock-nickname") || "";
  const headers = { "X-Auth-Nickname": encodeURIComponent(nickname) };

  const fetchMembers = useCallback(async () => {
    try {
      const res = await fetch("/api/members/list", { headers });
      const json = await res.json();
      setData(json);
    } catch { /* ignore */ }
  }, []);

  const fetchVisits = useCallback(async () => {
    try {
      const res = await fetch("/api/members/stats", { headers });
      const json = await res.json();
      setVisitStats(json);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchMembers();
    fetchVisits();
  }, [fetchMembers, fetchVisits]);

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
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ nickname: name }),
      });
      const json = await res.json();
      if (res.ok) {
        showMessage(json.message, "success");
        setNewName("");
        fetchMembers();
      } else {
        showMessage(json.detail || t("addFailed"), "error");
      }
    } catch {
      showMessage(t("serverError"), "error");
    }
    setLoading(false);
  };

  const handleRemove = async (name: string) => {
    if (!confirm(`'${name}' ${t("confirmDeleteMember")}`)) return;
    try {
      const res = await fetch("/api/members/remove", {
        method: "DELETE",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ nickname: name }),
      });
      const json = await res.json();
      if (res.ok) {
        showMessage(json.message, "success");
        fetchMembers();
      } else {
        showMessage(json.detail || t("deleteFailed"), "error");
      }
    } catch {
      showMessage(t("serverError"), "error");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("stock-nickname");
    localStorage.removeItem("stock-role");
    window.location.href = "/";
  };

  const filtered = data.members.filter((m) =>
    m.toLowerCase().includes(search.toLowerCase())
  );

  const visitMap = new Map<string, VisitStat>();
  for (const s of visitStats.stats) {
    visitMap.set(s.nickname.toLowerCase().trim(), s);
  }

  const filteredVisits = visitStats.stats.filter((s) =>
    s.nickname.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-[100dvh] w-screen bg-[var(--color-bg-primary)] bg-dot-grid overflow-hidden flex flex-col">
      {/* Header */}
      <header className="glass-strong h-14 border-b border-[var(--color-border)] flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}>
            <Users size={16} color="white" />
          </div>
          <div>
            <span className="text-sm font-bold text-[var(--color-text-primary)]">{t("adminPanel")}</span>
            <span className="text-[10px] text-[var(--color-text-muted)] ml-2">{nickname}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleLang}
            className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[#3b82f6] transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
          >
            <Globe size={12} />
            <span className="font-bold">{lang === "ko" ? "EN" : "KR"}</span>
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[#ef4444] transition-colors px-3 py-1.5 rounded-lg hover:bg-red-500/10"
          >
            <LogOut size={14} />
            {t("logout")}
          </button>
        </div>
      </header>

      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 pt-3 pb-2">
        <button
          onClick={() => setTab("visits")}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            tab === "visits"
              ? "bg-[#3b82f6] text-white shadow-lg shadow-blue-500/20"
              : "text-[var(--color-text-muted)] hover:bg-white/5"
          }`}
        >
          <BarChart3 size={14} />
          {t("visitStats")}
        </button>
        <button
          onClick={() => setTab("members")}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            tab === "members"
              ? "bg-[#3b82f6] text-white shadow-lg shadow-blue-500/20"
              : "text-[var(--color-text-muted)] hover:bg-white/5"
          }`}
        >
          <Users size={14} />
          {t("memberManagement")}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {/* Toast */}
          {message && (
            <div className={`px-4 py-3 rounded-xl text-sm font-medium border ${
              message.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-red-500/10 border-red-500/30 text-red-400"
            }`}>
              {message.text}
            </div>
          )}

          {tab === "visits" && (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="glass rounded-2xl border border-white/10 p-4 text-center">
                  <p className="text-2xl font-black text-[#3b82f6]">{visitStats.total_visits}</p>
                  <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{t("totalVisits")}</p>
                </div>
                <div className="glass rounded-2xl border border-white/10 p-4 text-center">
                  <p className="text-2xl font-black text-[#22c55e]">{visitStats.stats.length}</p>
                  <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{t("visitedUsers")}</p>
                </div>
                <div className="glass rounded-2xl border border-white/10 p-4 text-center">
                  <p className="text-2xl font-black text-[#8b5cf6]">{data.members.length}</p>
                  <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{t("totalMembers")}</p>
                </div>
              </div>

              {/* Search */}
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={t("searchUsers")}
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[#3b82f6] transition-colors"
                />
              </div>

              {/* Visit table */}
              <div className="glass rounded-2xl border border-white/10 overflow-hidden" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>
                <div className="grid grid-cols-[1fr_80px_100px] sm:grid-cols-[1fr_100px_140px] px-4 py-2.5 border-b border-[var(--color-border)] text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                  <span>{t("user")}</span>
                  <span className="text-center">{t("visitCount")}</span>
                  <span className="text-right">{t("lastVisit")}</span>
                </div>
                <div className="max-h-[50vh] overflow-y-auto divide-y divide-white/5">
                  {filteredVisits.length === 0 ? (
                    <div className="px-4 py-8 text-center">
                      <Eye size={24} className="text-[var(--color-text-muted)] mx-auto mb-2 opacity-40" />
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {search ? t("noSearchResults") : t("noVisitHistory")}
                      </p>
                    </div>
                  ) : (
                    filteredVisits.map((stat, i) => {
                      const isTopVisitor = i < 3 && !search;
                      return (
                        <div
                          key={stat.nickname}
                          className="grid grid-cols-[1fr_80px_100px] sm:grid-cols-[1fr_100px_140px] px-4 py-3 items-center hover:bg-white/3 transition-colors"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            {isTopVisitor && (
                              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black shrink-0 ${
                                i === 0 ? "bg-yellow-500/20 text-yellow-400" :
                                i === 1 ? "bg-gray-400/20 text-gray-300" :
                                "bg-amber-700/20 text-amber-600"
                              }`}>
                                {i + 1}
                              </span>
                            )}
                            <span className="text-sm text-[var(--color-text-primary)] truncate font-medium">
                              {stat.nickname}
                            </span>
                          </div>
                          <div className="text-center">
                            <span className="text-sm font-black text-[#3b82f6]">{stat.visit_count}</span>
                            <span className="text-[10px] text-[var(--color-text-muted)] ml-0.5">{t("times")}</span>
                          </div>
                          <div className="text-right flex items-center justify-end gap-1">
                            <Clock size={10} className="text-[var(--color-text-muted)]" />
                            <span className="text-[11px] text-[var(--color-text-muted)]">
                              {timeAgo(stat.last_visit, lang)}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </>
          )}

          {tab === "members" && (
            <>
              {/* Add member */}
              <div className="glass rounded-2xl border border-white/10 p-5" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>
                <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                  {t("addMember")}
                </h2>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                    placeholder={t("enterNewMember")}
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
                    {t("add")}
                  </button>
                </div>
              </div>

              {/* Search */}
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={t("searchMembers")}
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[#3b82f6] transition-colors"
                />
              </div>

              {/* Member list */}
              <div className="glass rounded-2xl border border-white/10 p-5" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                    {t("registeredMembers")} ({data.members.length})
                  </h2>
                </div>

                <div className="space-y-1 max-h-[55vh] overflow-y-auto">
                  {filtered.map((member) => {
                    const stat = visitMap.get(member.toLowerCase().trim());
                    return (
                      <div
                        key={member}
                        className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors group"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-sm text-[var(--color-text-primary)] truncate">{member}</span>
                          {stat && (
                            <span className="text-[10px] text-[var(--color-text-muted)] shrink-0 px-2 py-0.5 rounded-full bg-[var(--color-bg-hover)]">
                              {stat.visit_count}{t("times")}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => handleRemove(member)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-[var(--color-text-muted)] hover:text-red-400 transition-all"
                          title={t("delete")}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    );
                  })}
                  {filtered.length === 0 && (
                    <p className="text-xs text-[var(--color-text-muted)] text-center py-4">
                      {search ? t("noSearchResults") : t("noRegisteredMembers")}
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
