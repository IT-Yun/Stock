import requests
from bs4 import BeautifulSoup
import feedparser

from config import settings
from models.schemas import NewsArticle


class NewsCrawlerService:
    """Service for crawling news from multiple sources."""

    @staticmethod
    def crawl_naver_news(keyword: str) -> list[NewsArticle]:
        """Scrape Naver finance news for a keyword."""
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            articles = []

            news_items = soup.select("div.news_area")[:10]
            for item in news_items:
                title_tag = item.select_one("a.news_tit")
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")

                source_tag = item.select_one("a.info.press")
                source = source_tag.get_text(strip=True) if source_tag else "Naver"

                desc_tag = item.select_one("div.news_dsc")
                summary = desc_tag.get_text(strip=True) if desc_tag else None

                date_tag = item.select_one("span.info")
                published_at = date_tag.get_text(strip=True) if date_tag else None

                articles.append(NewsArticle(
                    title=title,
                    url=link,
                    source=source,
                    published_at=published_at,
                    summary=summary,
                ))

            return articles
        except Exception:
            return []

    @staticmethod
    def crawl_google_news_rss(keyword: str) -> list[NewsArticle]:
        """Fetch news via Google News RSS feed."""
        try:
            url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
            feed = feedparser.parse(url)
            articles = []

            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", "Google News") if hasattr(entry, "source") else "Google News"
                published_at = entry.get("published", None)

                articles.append(NewsArticle(
                    title=title,
                    url=link,
                    source=source,
                    published_at=published_at,
                    summary=None,
                ))

            return articles
        except Exception:
            return []

    @staticmethod
    def search_news(keyword: str) -> list[NewsArticle]:
        """Aggregate news from configured sources for a keyword."""
        articles: list[NewsArticle] = []

        sources = {source.strip().lower() for source in settings.NEWS_SOURCES if source.strip()}

        if "naver" in sources:
            articles.extend(NewsCrawlerService.crawl_naver_news(keyword))

        if "google" in sources:
            articles.extend(NewsCrawlerService.crawl_google_news_rss(keyword))

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique_articles: list[NewsArticle] = []
        for article in articles:
            if article.title not in seen_titles:
                seen_titles.add(article.title)
                unique_articles.append(article)

        return unique_articles

    @staticmethod
    def get_sector_news(sector_name: str) -> list[NewsArticle]:
        """Aggregate news from multiple sources for a sector."""
        return NewsCrawlerService.search_news(sector_name)
