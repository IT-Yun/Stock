import re
import time
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import feedparser
from services.runtime_controls import limit_http

from config import settings
from models.schemas import NewsArticle


_NEWS_CACHE: dict[str, tuple[float, object]] = {}
NEWS_CACHE_TTL = 180  # 3분 — 뉴스는 실시간이 중요, rate limit 없음


def _get_cached(key: str):
    cached = _NEWS_CACHE.get(key)
    if cached and time.time() - cached[0] < NEWS_CACHE_TTL:
        return cached[1]
    return None


def _set_cached(key: str, value: object):
    _NEWS_CACHE[key] = (time.time(), value)


class NewsCrawlerService:
    """Service for crawling news from multiple sources."""

    @staticmethod
    def crawl_naver_news(keyword: str) -> list[NewsArticle]:
        """Scrape Naver finance news for a keyword."""
        cache_key = f"naver:{keyword}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            with limit_http():
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

            _set_cached(cache_key, articles)
            return articles
        except Exception:
            return []

    @staticmethod
    def crawl_google_news_rss(keyword: str, lang: str = "ko") -> list[NewsArticle]:
        """Fetch news via Google News RSS feed."""
        cache_key = f"google:{lang}:{keyword}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

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

            _set_cached(cache_key, articles)
            return articles
        except Exception:
            return []

    @staticmethod
    def crawl_naver_finance_news(stock_code: str, count: int = 15) -> list[NewsArticle]:
        """
        Crawl stock-SPECIFIC news from Naver Finance item news page.
        Every article is guaranteed to be about this stock — no relevance filtering needed.
        Uses NaverFinanceService as the data source.
        """
        cache_key = f"naver_finance_news:{stock_code}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            from services.naver_finance import NaverFinanceService
            raw = NaverFinanceService.fetch_stock_news(stock_code, count=count)
            articles = []
            for item in raw:
                articles.append(NewsArticle(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source=item.get("source", "네이버 금융"),
                    published_at=item.get("date"),
                    summary=None,
                ))
            _set_cached(cache_key, articles)
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
    def search_news(keyword: str) -> list[NewsArticle]:
        """Aggregate news from configured sources for a keyword.
        For Korean stock codes (6-digit), prioritizes Naver Finance stock-specific news.
        """
        cache_key = f"search:{keyword}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        articles: list[NewsArticle] = []

        # If keyword looks like a Korean stock code, use Naver Finance stock news first
        stock_code = re.sub(r"\.(KS|KQ)$", "", keyword.strip())
        if re.match(r"^\d{6}$", stock_code):
            nf_articles = NewsCrawlerService.crawl_naver_finance_news(stock_code)
            articles.extend(nf_articles)

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

        _set_cached(cache_key, unique_articles)
        return unique_articles

    @staticmethod
    def get_sector_news(sector_name: str) -> list[NewsArticle]:
        """Aggregate news from Korean + English sources for a sector."""
        cache_key = f"sector:{sector_name}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

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

        _set_cached(cache_key, unique_articles)
        return unique_articles

    # Korean name mapping for earnings search — yfinance returns English names
    _KOREAN_NAMES: dict[str, str] = {
        "005930.KS": "삼성전자", "000660.KS": "SK하이닉스",
        "006400.KS": "삼성SDI", "373220.KS": "LG에너지솔루션",
        "086520.KS": "에코프로", "247540.KS": "에코프로비엠",
        "012450.KS": "한화에어로스페이스", "047810.KS": "한국항공우주",
        "207940.KS": "삼성바이오로직스", "068270.KS": "셀트리온",
        "005380.KS": "현대자동차", "000270.KS": "기아",
        "003670.KS": "포스코퓨처엠", "066970.KS": "엘앤에프",
        "035420.KS": "NAVER", "035720.KS": "카카오",
        "051910.KS": "LG화학", "105560.KS": "KB금융",
        "055550.KS": "신한지주", "000810.KS": "삼성화재",
        "028260.KS": "삼성물산", "018260.KS": "삼성에스디에스",
        "009150.KS": "삼성전기", "042700.KS": "한미반도체",
        "003550.KS": "LG", "066570.KS": "LG전자",
        "034730.KS": "SK", "017670.KS": "SK텔레콤",
        "030200.KS": "KT", "036570.KS": "엔씨소프트",
        "259960.KS": "크래프톤", "352820.KS": "하이브",
    }

    @staticmethod
    def crawl_preliminary_earnings(company_name: str, ticker: str) -> dict:
        """
        Crawl news for preliminary/flash earnings numbers.
        Returns extracted revenue/operating_profit/net_income if found.
        Searches both Korean (잠정실적) and English (preliminary earnings).
        """
        cache_key = f"prelim:{company_name}:{ticker}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        result: dict = {"found": False, "source": "", "data": {}, "headlines": []}

        # Resolve Korean name — yfinance may give English name
        ko_name = NewsCrawlerService._KOREAN_NAMES.get(ticker)
        if not ko_name:
            code = ticker.split(".")[0]
            ko_name = NewsCrawlerService._KOREAN_NAMES.get(f"{code}.KS")
        # If still no Korean name but company_name has Korean chars, use it
        if not ko_name and any("\uac00" <= ch <= "\ud7a3" for ch in company_name):
            ko_name = company_name
        search_name = ko_name or company_name

        try:
            # Korean search: 잠정실적, 실적발표
            ko_keywords = [
                f"{search_name} 잠정실적",
                f"{search_name} 영업이익 실적",
                f"{search_name} 매출 실적발표",
                f"{search_name} 1분기 실적",
                f"{search_name} 실적 서프라이즈",
            ]
            # Also try original company name if different
            if search_name != company_name and company_name:
                ko_keywords.append(f"{company_name} 잠정실적")
            # English search
            en_keywords = [
                f"{ticker.replace('.KS','').replace('.KQ','')} preliminary earnings results",
                f"{ticker.replace('.KS','').replace('.KQ','')} quarterly revenue operating profit",
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

        _set_cached(cache_key, result)
        return result
