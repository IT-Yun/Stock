import re
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import feedparser
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
    def crawl_google_news_rss(keyword: str, lang: str = "ko") -> list[NewsArticle]:
        """Fetch news via Google News RSS feed."""
        try:
            encoded_kw = quote(keyword)
            if lang == "en":
                url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=en&gl=US&ceid=US:en"
            else:
                url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=ko&gl=KR&ceid=KR:ko"
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

    # Mapping Korean keywords → English equivalents for dual-language search
    KEYWORD_EN_MAP: dict[str, str] = {
        "반도체": "semiconductor AI chip",
        "로봇": "robotics automation",
        "원자력": "nuclear SMR energy",
        "사이버보안": "cybersecurity",
        "우주항공": "space launch satellite",
        "바이오": "biotech gene therapy",
        "양자컴퓨팅": "quantum computing",
        "수소": "hydrogen fuel cell clean energy",
    }

    @staticmethod
    def get_sector_news(sector_name: str) -> list[NewsArticle]:
        """Aggregate news from Korean + English sources for a sector."""
        articles: list[NewsArticle] = []

        # Korean sources
        naver_articles = NewsCrawlerService.crawl_naver_news(sector_name)
        articles.extend(naver_articles)

        google_ko = NewsCrawlerService.crawl_google_news_rss(sector_name, lang="ko")
        articles.extend(google_ko)

        # English sources — use mapped keyword or original
        en_keyword = NewsCrawlerService.KEYWORD_EN_MAP.get(sector_name, sector_name)
        google_en = NewsCrawlerService.crawl_google_news_rss(en_keyword, lang="en")
        articles.extend(google_en)

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique_articles: list[NewsArticle] = []
        for article in articles:
            if article.title not in seen_titles:
                seen_titles.add(article.title)
                unique_articles.append(article)

        return unique_articles

    @staticmethod
    def crawl_preliminary_earnings(company_name: str, ticker: str) -> dict:
        """
        Crawl news for preliminary/flash earnings numbers.
        Returns extracted revenue/operating_profit/net_income if found.
        Searches both Korean (잠정실적) and English (preliminary earnings).
        """
        result: dict = {"found": False, "source": "", "data": {}, "headlines": []}

        try:
            # Korean search: 잠정실적, 실적발표
            ko_keywords = [
                f"{company_name} 잠정실적",
                f"{company_name} 영업이익 실적",
                f"{company_name} 매출 실적발표",
            ]
            # English search
            en_keywords = [
                f"{ticker} preliminary earnings results",
                f"{ticker} quarterly revenue operating profit",
            ]

            all_articles: list[NewsArticle] = []
            for kw in ko_keywords:
                try:
                    arts = NewsCrawlerService.crawl_naver_news(kw)
                    all_articles.extend(arts)
                except Exception:
                    pass
            for kw in en_keywords[:1]:
                try:
                    arts = NewsCrawlerService.crawl_google_news_rss(kw, lang="en")
                    all_articles.extend(arts)
                except Exception:
                    pass

            if not all_articles:
                return result

            # Collect text from titles + summaries
            texts = []
            for a in all_articles[:15]:
                t = (a.title or "") + " " + (a.summary or "")
                texts.append(t)
                result["headlines"].append(a.title)

            combined = " ".join(texts)

            # ── Extract Korean numbers ──
            # Pattern: 영업이익 XX조 YY억, 매출 XX조
            def parse_korean_amount(text: str, keyword: str) -> float | None:
                """Extract amount in 억원 after keyword. Returns value in 억원."""
                patterns = [
                    # XX조 YY억
                    rf"{keyword}\s*(\d+\.?\d*)\s*조\s*(\d+\.?\d*)?\s*억",
                    # XX조
                    rf"{keyword}\s*(\d+\.?\d*)\s*조",
                    # XX억
                    rf"{keyword}\s*(\d+\.?\d*)\s*억",
                    # XX만억 (rare)
                    rf"{keyword}\s*(\d+\.?\d*)\s*만억",
                ]
                for p in patterns:
                    m = re.search(p, text)
                    if m:
                        groups = m.groups()
                        if "조" in p and len(groups) >= 2 and groups[1]:
                            return float(groups[0]) * 10000 + float(groups[1])
                        elif "조" in p:
                            return float(groups[0]) * 10000
                        elif "만억" in p:
                            return float(groups[0]) * 10000
                        else:
                            return float(groups[0])
                return None

            # Try extracting Korean numbers
            rev = parse_korean_amount(combined, "매출")
            op_profit = parse_korean_amount(combined, "영업이익")
            net_income = parse_korean_amount(combined, "순이익")

            # ── Extract English numbers ──
            # Pattern: revenue of $XX billion, operating profit $XX billion
            def parse_english_amount(text: str, keyword: str) -> float | None:
                """Extract USD amount after keyword. Returns value in billions."""
                patterns = [
                    rf"{keyword}[^.]*?\$\s*(\d+\.?\d*)\s*(billion|trillion|million)",
                    rf"{keyword}[^.]*?(\d+\.?\d*)\s*(billion|trillion|million)\s*(dollars|won|USD)?",
                ]
                for p in patterns:
                    m = re.search(p, text, re.IGNORECASE)
                    if m:
                        val = float(m.group(1))
                        unit = m.group(2).lower()
                        if unit == "trillion":
                            return val * 1000
                        elif unit == "million":
                            return val / 1000
                        return val  # billion
                return None

            if rev is None:
                rev_en = parse_english_amount(combined, "revenue")
                if rev_en:
                    result["data"]["revenue_usd_b"] = rev_en
            if op_profit is None:
                op_en = parse_english_amount(combined, "operating profit")
                if op_en:
                    result["data"]["op_profit_usd_b"] = op_en

            if rev is not None:
                result["data"]["revenue_억"] = rev
                result["found"] = True
            if op_profit is not None:
                result["data"]["operating_profit_억"] = op_profit
                result["found"] = True
            if net_income is not None:
                result["data"]["net_income_억"] = net_income
                result["found"] = True

            if result["found"]:
                result["source"] = "뉴스 잠정실적 크롤링"

        except Exception:
            pass

        return result
