import { useEffect, useState, useRef } from "react";
import { fetchNews, searchNews } from "@/api/client";
import { useLanguage } from "@/i18n";
import type { NewsArticle } from "@/types";

interface NewsPanelProps {
  sectorName?: string;
  keyword?: string;
}

export default function NewsPanel({ sectorName, keyword }: NewsPanelProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { t } = useLanguage();

  function relativeTime(dateStr: string): string {
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diffSec = Math.floor((now - then) / 1000);
    if (diffSec < 60) return t("justNow");
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}${t("minutesAgo")}`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}${t("hoursAgo")}`;
    const diffDay = Math.floor(diffHour / 24);
    return `${diffDay}${t("daysAgo")}`;
  }

  const loadNews = () => {
    const promise = keyword ? searchNews(keyword) : sectorName ? fetchNews(sectorName) : Promise.resolve([]);
    promise
      .then((data) => {
        setArticles(data);
        setError(null);
      })
      .catch(() => setError(t("newsLoadFailed")))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setLoading(true);
    loadNews();

    intervalRef.current = setInterval(loadNews, 60000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectorName, keyword]);

  if (loading) {
    return (
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5">
        <h3 className="text-lg font-bold mb-4">{t("news")}</h3>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-[var(--color-bg-hover)] rounded w-3/4 mb-2" />
              <div className="h-3 bg-[var(--color-bg-hover)] rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-5">
      <h3 className="text-lg font-bold mb-4">{t("news")}</h3>
      {error ? (
        <p className="text-[var(--color-accent-red)] text-sm">{error}</p>
      ) : articles.length === 0 ? (
        <p className="text-[var(--color-text-muted)] text-sm">{t("noNews")}</p>
      ) : (
        <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
          {articles.map((article, idx) => (
            <div key={idx} className="border-b border-[var(--color-border)] pb-3 last:border-b-0">
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-[var(--color-accent-blue)] hover:underline leading-snug block"
              >
                {article.title}
              </a>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-[var(--color-text-muted)]">
                  {article.source}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {relativeTime(article.published_at ?? article.publishedAt ?? "")}
                </span>
              </div>
              {article.summary && (
                <p className="text-xs text-[var(--color-text-secondary)] mt-1 line-clamp-2">
                  {article.summary}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
