import { useEffect, useRef, useState } from "react";
import { fetchChartData } from "@/api/client";

interface SparklineProps {
  ticker: string | null | undefined;
  width?: number;
  height?: number;
  period?: string;
  fallbackText?: string;
  dataOverride?: number[] | null;
}

const DATA_CACHE: Map<string, number[] | "error"> = new Map();

export default function Sparkline({
  ticker,
  width = 120,
  height = 32,
  period = "3mo",
  fallbackText = "no data",
  dataOverride,
}: SparklineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<number[] | null>(
    dataOverride?.length ? dataOverride : ticker ? (DATA_CACHE.get(`${ticker}|${period}`) as number[]) ?? null : null
  );
  const [errored, setErrored] = useState(
    ticker ? DATA_CACHE.get(`${ticker}|${period}`) === "error" : false
  );
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.1, rootMargin: "200px 0px" }
    );
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (dataOverride?.length) {
      setData(dataOverride);
      return;
    }
    if (!visible || !ticker || data || errored) return;
    const cacheKey = `${ticker}|${period}`;
    const cached = DATA_CACHE.get(cacheKey);
    if (cached === "error") {
      setErrored(true);
      return;
    }
    if (cached) {
      setData(cached as number[]);
      return;
    }
    let cancelled = false;
    fetchChartData(ticker, period)
      .then((points) => {
        const closes = points.map((p) => p.close ?? 0).filter((v) => v > 0);
        if (cancelled) return;
        DATA_CACHE.set(cacheKey, closes.length >= 2 ? closes : "error");
        if (closes.length >= 2) setData(closes);
        else setErrored(true);
      })
      .catch(() => {
        if (cancelled) return;
        DATA_CACHE.set(cacheKey, "error");
        setErrored(true);
      });
    return () => {
      cancelled = true;
    };
  }, [visible, ticker, period, data, errored, dataOverride]);

  if (!ticker && !dataOverride?.length) {
    return (
      <div
        style={{ width, height }}
        className="rounded bg-slate-800/20 flex items-center justify-center text-[9px] text-slate-600"
      >
        {fallbackText}
      </div>
    );
  }

  if (!visible || (!data && !errored)) {
    return (
      <div
        ref={containerRef}
        style={{ width, height }}
        className="rounded bg-slate-800/30 animate-pulse"
      />
    );
  }

  if (errored || !data || data.length < 2) {
    return (
      <div
        ref={containerRef}
        style={{ width, height }}
        className="rounded bg-slate-800/20 flex items-center justify-center text-[9px] text-slate-600"
      >
        {fallbackText}
      </div>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const pts = data
    .map((v, i) => `${(i * stepX).toFixed(1)},${(height - ((v - min) / range) * height).toFixed(1)}`)
    .join(" ");
  const trend = data[data.length - 1] - data[0];
  const trendPct = (trend / data[0]) * 100;
  const color = trend >= 0 ? "#10b981" : "#ef4444";

  return (
    <div ref={containerRef} className="relative" style={{ width, height }} title={`${trendPct.toFixed(1)}% over ${period}`}>
      <svg width={width} height={height} className="block">
        <defs>
          <linearGradient id={`g-${ticker ?? "series"}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon
          points={`0,${height} ${pts} ${width},${height}`}
          fill={`url(#g-${ticker ?? "series"})`}
        />
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
