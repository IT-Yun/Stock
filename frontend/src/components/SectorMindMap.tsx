import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Factory } from "lucide-react";
import { SECTORS, normalizeWeights } from "@/data/sectors";
import type { SectorDef } from "@/data/sectors";

/* ───────────────────────── HELPERS ───────────────────────── */

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

/* ───────────────────────── COMPONENT ───────────────────────── */

export default function SectorMindMap() {
  const [year, setYear] = useState(10);
  const [selected, setSelected] = useState<SectorDef | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 1200, h: 800 });
  const navigate = useNavigate();

  const measure = useCallback(() => {
    if (containerRef.current) {
      const r = containerRef.current.getBoundingClientRect();
      setDims({ w: r.width, h: r.height });
    }
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  const cx = dims.w / 2;
  const cy = dims.h / 2;
  const orbitR = Math.min(dims.w, dims.h) * 0.34;

  const yearIdx = year - 1; // 0-based index
  const weights = normalizeWeights(SECTORS, yearIdx);

  return (
    <div className="flex h-full">
      {/* ─── Stock Panel (left slide) ─── */}
      <div
        className="shrink-0 overflow-y-auto overflow-x-hidden border-r border-white/5 glass-strong transition-all duration-500 ease-out"
        style={{ width: selected ? 340 : 0, opacity: selected ? 1 : 0 }}
      >
        {selected && (
          <div className="p-6 space-y-5" style={{ animation: "fadeInUp 0.35s ease-out" }}>
            {/* Header */}
            <div className="flex items-center gap-3">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{
                  background: `linear-gradient(135deg, ${selected.color}30, ${selected.color}10)`,
                  border: `1.5px solid ${selected.color}50`,
                  boxShadow: `0 8px 32px ${selected.color}20`,
                }}
              >
                <selected.icon size={26} strokeWidth={1.5} style={{ color: selected.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-bold" style={{ color: selected.color }}>
                  {selected.name}
                </h3>
                <p className="text-[11px] text-[var(--color-text-muted)]">
                  {2025 + year}년 투자 비중{" "}
                  <span style={{ color: selected.color, fontWeight: 700 }}>
                    {Math.round((weights.get(selected.id) ?? 0) * 100)}%
                  </span>
                </p>
              </div>
              <button
                className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-white hover:bg-white/10 transition-all"
                onClick={() => setSelected(null)}
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
              {selected.desc}
            </p>

            {/* Materials tags */}
            {selected.materials.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {selected.materials.map((m) => (
                  <span
                    key={m}
                    className="px-2.5 py-1 rounded-full text-[10px] font-medium"
                    style={{
                      background: `linear-gradient(135deg, ${selected.color}15, ${selected.color}08)`,
                      color: selected.color,
                      border: `1px solid ${selected.color}25`,
                    }}
                  >
                    {m}
                  </span>
                ))}
              </div>
            )}

            {/* Divider */}
            <div className="h-px w-full" style={{ background: `linear-gradient(90deg, transparent, ${selected.color}30, transparent)` }} />

            {/* TOP PICKS */}
            <div>
              <p className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-widest mb-3">
                Top 5 Picks
              </p>
              <div className="space-y-2">
                {selected.picks.map((pick, i) => (
                  <div
                    key={pick.ticker}
                    className="flex items-center gap-3 px-3.5 py-3 rounded-xl cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(255,255,255,0.02)",
                      border: "1px solid rgba(255,255,255,0.04)",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = `${selected.color}12`;
                      e.currentTarget.style.borderColor = `${selected.color}30`;
                      e.currentTarget.style.transform = "translateX(4px)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.04)";
                      e.currentTarget.style.transform = "translateX(0)";
                    }}
                    onClick={() => navigate(`/sector/${selected.id}?stock=${encodeURIComponent(pick.ticker)}`)}
                  >
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-bold shrink-0"
                      style={{
                        background: `linear-gradient(135deg, ${selected.color}, ${selected.color}bb)`,
                        color: "#fff",
                        boxShadow: `0 4px 12px ${selected.color}30`,
                      }}
                    >
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-white transition-colors">
                          {pick.name}
                        </span>
                        <span
                          className="text-[9px] px-1.5 py-0.5 rounded font-bold"
                          style={{
                            background: pick.flag === "US" ? "rgba(59,130,246,0.15)" : "rgba(239,68,68,0.15)",
                            color: pick.flag === "US" ? "#60a5fa" : "#f87171",
                          }}
                        >
                          {pick.flag}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--color-text-muted)] truncate mt-0.5">
                        {pick.desc}
                      </p>
                    </div>
                    <svg className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-white/60 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                ))}
              </div>
            </div>

            {/* Sector Detail Button */}
            <button
              className="w-full py-3 rounded-xl text-sm font-bold transition-all duration-300"
              style={{
                background: `linear-gradient(135deg, ${selected.color}, ${selected.color}bb)`,
                color: "#fff",
                boxShadow: `0 4px 20px ${selected.color}40`,
                border: "1px solid rgba(255,255,255,0.1)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = `0 8px 30px ${selected.color}60`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = `0 4px 20px ${selected.color}40`;
              }}
              onClick={() => navigate(`/sector/${selected.id}`)}
            >
              섹터 상세 분석 →
            </button>
          </div>
        )}
      </div>

      {/* ─── Mind Map Canvas ─── */}
      <div
        ref={containerRef}
        className="flex-1 relative overflow-hidden bg-[var(--color-bg-primary)] bg-dot-grid"
      >
        {/* Ambient glow blobs */}
        <div className="absolute pointer-events-none" style={{ left: cx - 250, top: cy - 250, width: 500, height: 500, background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%)", animation: "breathe 8s ease-in-out infinite" }} />
        <div className="absolute pointer-events-none" style={{ left: cx + 100, top: cy - 200, width: 400, height: 400, background: "radial-gradient(circle, rgba(168,85,247,0.04) 0%, transparent 70%)", animation: "breathe 10s ease-in-out infinite 2s" }} />

        {/* ─── Year Slider (fixed right) ─── */}
        <div className="fixed top-14 right-5 z-40 flex flex-col items-end gap-2">
          <div className="glass rounded-2xl px-5 py-3 flex flex-col gap-2" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.4)", width: 260 }}>
            <div className="flex items-center justify-between w-full">
              <span className="text-[11px] text-[var(--color-text-muted)] font-medium">투자 시점</span>
              <span className="text-sm font-bold text-gradient">{2025 + year}년</span>
            </div>
            <div className="w-full relative">
              <input
                type="range"
                min={1}
                max={30}
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(90deg, #3b82f6 ${((year - 1) / 29) * 100}%, rgba(255,255,255,0.08) ${((year - 1) / 29) * 100}%)`,
                  WebkitAppearance: "none",
                }}
              />
              <div className="flex justify-between mt-1.5 px-0.5">
                {[1, 5, 10, 15, 20, 25, 30].map((y) => (
                  <button
                    key={y}
                    onClick={() => setYear(y)}
                    className={`text-[9px] font-mono transition-all ${
                      y === year ? "text-white font-bold" : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                    }`}
                  >
                    {y}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="text-[9px] text-[var(--color-text-muted)] tracking-wide pr-1">
            {2025 + year}년에 투자한다면? — 선반영 감안 추천 비중
          </p>
        </div>

        {/* SVG Lines & Effects */}
        <svg width={dims.w} height={dims.h} className="absolute inset-0 pointer-events-none">
          <defs>
            {SECTORS.map((s) => (
              <linearGradient key={`grad-${s.id}`} id={`grad-${s.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={s.color} stopOpacity="0" />
                <stop offset="50%" stopColor={s.color} stopOpacity="0.5" />
                <stop offset="100%" stopColor={s.color} stopOpacity="0.1" />
              </linearGradient>
            ))}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Orbit rings */}
          {[0.96, 1, 1.04].map((scale, i) => (
            <circle key={i} cx={cx} cy={cy} r={orbitR * scale} fill="none" stroke="var(--color-border)" strokeWidth={i === 1 ? 0.8 : 0.3} strokeDasharray={i === 1 ? "6 12" : "2 16"} opacity={i === 1 ? 0.3 : 0.12} />
          ))}

          {/* Connection lines */}
          {SECTORS.map((s) => {
            const rad = (s.angle * Math.PI) / 180;
            const sx = cx + Math.cos(rad) * orbitR;
            const sy = cy + Math.sin(rad) * orbitR;
            const w = weights.get(s.id) ?? 0;
            const isActive = selected?.id === s.id;
            const isHov = hovered === s.id;

            return (
              <g key={s.id}>
                <line x1={cx} y1={cy} x2={sx} y2={sy} stroke={`url(#grad-${s.id})`} strokeWidth={isActive || isHov ? lerp(2, 4, w) : lerp(1, 2.5, w)} opacity={isActive ? 0.8 : isHov ? 0.6 : lerp(0.15, 0.35, w)} style={{ transition: "all 0.4s ease" }} />
                <circle r={isActive ? 3 : 2} fill={s.color} opacity={isActive ? 0.9 : 0.4} filter={isActive ? "url(#glow)" : ""}>
                  <animateMotion dur={`${3 - w * 1.5}s`} repeatCount="indefinite" path={`M${cx},${cy} L${sx},${sy}`} />
                </circle>
                {isActive && (
                  <>
                    <circle cx={sx} cy={sy} r={lerp(55, 100, w)} fill="none" stroke={s.color} strokeWidth={1} opacity={0.15}>
                      <animate attributeName="r" values={`${lerp(55, 100, w)};${lerp(70, 120, w)};${lerp(55, 100, w)}`} dur="3s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.15;0.05;0.15" dur="3s" repeatCount="indefinite" />
                    </circle>
                    <circle cx={sx} cy={sy} r={lerp(45, 85, w)} fill={s.color} opacity={0.06}>
                      <animate attributeName="r" values={`${lerp(45, 85, w)};${lerp(55, 95, w)};${lerp(45, 85, w)}`} dur="2s" repeatCount="indefinite" />
                    </circle>
                  </>
                )}
              </g>
            );
          })}
        </svg>

        {/* Central Node */}
        <div
          className="absolute z-20 rounded-full flex flex-col items-center justify-center cursor-default select-none"
          style={{
            left: cx - 55, top: cy - 55, width: 110, height: 110,
            background: "radial-gradient(circle at 30% 30%, #1e3a5f 0%, #0c1220 80%)",
            border: "1.5px solid rgba(59,130,246,0.3)",
            boxShadow: "0 0 80px rgba(59,130,246,0.12), 0 0 30px rgba(59,130,246,0.06), inset 0 1px 0 rgba(255,255,255,0.05)",
            animation: "breathe 6s ease-in-out infinite",
          }}
          onClick={() => setSelected(null)}
        >
          <div className="absolute inset-2 rounded-full" style={{ border: "1px solid rgba(59,130,246,0.1)" }} />
          <Factory size={32} className="mb-1" style={{ color: "#60a5fa", filter: "drop-shadow(0 0 10px rgba(59,130,246,0.4))" }} strokeWidth={1.5} />
          <span className="text-[13px] font-bold text-center leading-tight text-gradient">
            미래 성장
            <br />
            산업
          </span>
        </div>

        {/* Sector Nodes */}
        {SECTORS.map((s, idx) => {
          const w = weights.get(s.id) ?? 0;
          const rad = (s.angle * Math.PI) / 180;
          const sx = cx + Math.cos(rad) * orbitR;
          const sy = cy + Math.sin(rad) * orbitR;
          const size = lerp(75, 155, w * 8);
          const clampedSize = Math.max(75, Math.min(155, size));
          const isActive = selected?.id === s.id;
          const isHov = hovered === s.id;
          const pct = Math.round(w * 100);

          return (
            <div
              key={s.id}
              className="absolute z-20 rounded-full flex flex-col items-center justify-center cursor-pointer select-none node-hover"
              style={{
                left: sx - clampedSize / 2,
                top: sy - clampedSize / 2,
                width: clampedSize,
                height: clampedSize,
                background: isActive
                  ? `radial-gradient(circle at 30% 30%, ${s.color}dd, ${s.color}88)`
                  : `radial-gradient(circle at 30% 30%, ${s.color}22, ${s.color}08)`,
                border: `1.5px solid ${isActive ? s.color : `${s.color}${isHov ? "80" : "40"}`}`,
                boxShadow: isActive
                  ? `0 0 50px ${s.color}35, 0 0 100px ${s.color}15, inset 0 1px 0 rgba(255,255,255,0.1)`
                  : isHov
                  ? `0 0 40px ${s.color}25, inset 0 1px 0 rgba(255,255,255,0.05)`
                  : `0 0 20px ${s.color}08, inset 0 1px 0 rgba(255,255,255,0.03)`,
                transform: isActive ? "scale(1.06)" : "scale(1)",
                animation: `fadeInUp 0.5s ease-out ${idx * 0.06}s both`,
                transition: "width 0.5s ease, height 0.5s ease, left 0.5s ease, top 0.5s ease, background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease",
              }}
              onClick={() => setSelected(isActive ? null : s)}
              onMouseEnter={() => setHovered(s.id)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="absolute inset-1.5 rounded-full pointer-events-none" style={{ border: `1px solid ${s.color}${isActive ? "30" : "10"}` }} />
              <s.icon
                size={lerp(22, 38, w * 8)}
                strokeWidth={1.5}
                style={{
                  color: isActive ? "#fff" : s.color,
                  filter: `drop-shadow(0 0 ${isActive ? 12 : 6}px ${s.color}${isActive ? "aa" : "60"})`,
                  transition: "all 0.5s ease",
                }}
              />
              <span
                className="text-center font-bold leading-tight mt-1"
                style={{
                  fontSize: Math.max(11, lerp(11, 17, w * 8)),
                  color: isActive ? "#fff" : "var(--color-text-primary)",
                  whiteSpace: "pre-line",
                  textShadow: isActive ? `0 0 20px ${s.color}60` : "none",
                  transition: "all 0.3s ease",
                }}
              >
                {s.name}
              </span>
              <span
                className="text-[11px] font-mono mt-1 px-2.5 py-0.5 rounded-full font-bold"
                style={{
                  background: isActive ? "rgba(255,255,255,0.15)" : `linear-gradient(135deg, ${s.color}20, ${s.color}10)`,
                  color: isActive ? "#fff" : s.color,
                  border: `1px solid ${isActive ? "rgba(255,255,255,0.2)" : `${s.color}20`}`,
                  backdropFilter: "blur(4px)",
                  transition: "all 0.3s ease",
                }}
              >
                {pct}%
              </span>
            </div>
          );
        })}

        {/* Legend bottom-right */}
        <div className="absolute bottom-5 right-5 z-30 flex items-center gap-4 text-[10px] text-[var(--color-text-muted)] glass rounded-xl px-4 py-2.5">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: "rgba(59,130,246,0.2)", border: "1px solid rgba(59,130,246,0.3)" }} />
            낮은 비중
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-5 h-5 rounded-full" style={{ background: "rgba(59,130,246,0.2)", border: "1px solid rgba(59,130,246,0.3)" }} />
            중간
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-7 h-7 rounded-full" style={{ background: "rgba(59,130,246,0.2)", border: "1px solid rgba(59,130,246,0.3)" }} />
            높은 비중
          </span>
        </div>

        {/* Sector count */}
        <div className="absolute bottom-5 left-5 z-30 text-[11px] text-[var(--color-text-muted)] glass rounded-xl px-4 py-2.5 font-medium">
          {SECTORS.length}개 섹터 · {SECTORS.reduce((a, s) => a + s.picks.length, 0)}개 종목
        </div>
      </div>
    </div>
  );
}
