"""
External research data sources for comprehensive stock analysis.
Provides analyst reports, filings, consensus estimates, and economic calendars.

Data sources:
  - DART (dart.fss.or.kr): Korean company filings & disclosures
  - Naver Research: Korean analyst reports & consensus estimates
  - SEC EDGAR: US company filings (10-K, 10-Q, 8-K)
  - Naver Finance Consensus: KRX target prices & EPS estimates
  - Yahoo Finance Analysis: US analyst ratings & price targets

All results are cached with appropriate TTLs.
"""
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from services.runtime_controls import limit_http

try:
    from curl_cffi.requests import Session as CffiSession
    _cffi_available = True
except ImportError:
    _cffi_available = False


# ─── Shared cache ───

_RESEARCH_CACHE: dict[str, tuple[float, object]] = {}

def _get_cached(key: str, ttl: int = 3600) -> object | None:
    cached = _RESEARCH_CACHE.get(key)
    if cached and time.time() - cached[0] < ttl:
        return cached[1]
    return None

def _set_cached(key: str, value: object):
    _RESEARCH_CACHE[key] = (time.time(), value)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ═══════════════════════════════════════════════════════════
# 1. DART — Korean company filings & major disclosures
# ═══════════════════════════════════════════════════════════

# DART Open API key — free tier, 1000 calls/day
# Users can set DART_API_KEY env var; if absent, we fall back to web scraping
import os
_DART_API_KEY = os.getenv("DART_API_KEY", "")

# KRX code → DART corp_code mapping (cached on first use)
_DART_CORP_MAP: dict[str, str] = {}


def fetch_dart_disclosures(ticker: str, count: int = 10) -> list[dict]:
    """
    Fetch recent DART disclosures for a Korean stock.
    Returns list of {title, date, url, type} dicts.
    Falls back to web scraping if no API key.
    """
    if not (ticker.endswith(".KS") or ticker.endswith(".KQ")):
        return []

    cache_key = f"dart:{ticker}"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    code = ticker.split(".")[0]
    results = []

    try:
        # Web scraping approach (no API key required)
        url = f"https://dart.fss.or.kr/dsab007/detailSearch.ax?textCrpNm={code}"
        search_url = (
            f"https://dart.fss.or.kr/dsab007/detailSearch.ax?"
            f"currentPage=1&maxResults={count}&textCrpNm={code}"
            f"&startDate=&endDate=&publicType=&textPresenterNm="
        )
        with limit_http():
            r = requests.get(search_url, headers=_HEADERS, timeout=10)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tbody tr")

        for row in rows[:count]:
            cells = row.select("td")
            if len(cells) < 5:
                continue
            date_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            title_el = cells[2].select_one("a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            doc_url = f"https://dart.fss.or.kr{href}" if href.startswith("/") else href
            doc_type = cells[1].get_text(strip=True) if len(cells) > 1 else ""

            results.append({
                "title": title,
                "date": date_text,
                "url": doc_url,
                "type": doc_type,
                "source": "DART",
            })

    except Exception:
        pass

    _set_cached(cache_key, results)
    return results


def fetch_dart_major_shareholder(ticker: str) -> list[dict]:
    """Fetch major shareholder change disclosures from DART."""
    if not (ticker.endswith(".KS") or ticker.endswith(".KQ")):
        return []

    cache_key = f"dart_share:{ticker}"
    cached = _get_cached(cache_key, ttl=7200)
    if cached is not None:
        return cached

    code = ticker.split(".")[0]
    results = []

    try:
        url = (
            f"https://dart.fss.or.kr/dsab007/detailSearch.ax?"
            f"currentPage=1&maxResults=5&textCrpNm={code}"
            f"&publicType=F&textPresenterNm="
        )
        with limit_http():
            r = requests.get(url, headers=_HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for row in soup.select("table tbody tr")[:5]:
                cells = row.select("td")
                if len(cells) < 5:
                    continue
                title_el = cells[2].select_one("a")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "date": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                        "source": "DART",
                    })
    except Exception:
        pass

    _set_cached(cache_key, results)
    return results


# ═══════════════════════════════════════════════════════════
# 2. Naver Research — Korean analyst reports
# ═══════════════════════════════════════════════════════════

def fetch_naver_analyst_reports(ticker: str, count: int = 8) -> list[dict]:
    """
    Fetch recent analyst reports from Naver Finance research section.
    Returns list of {title, date, source, target_price, opinion, url}.
    """
    if not (ticker.endswith(".KS") or ticker.endswith(".KQ")):
        return []

    cache_key = f"naver_research:{ticker}"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    code = ticker.split(".")[0]
    results = []

    try:
        url = f"https://finance.naver.com/research/company_list.naver?searchType=itemCode&itemCode={code}"
        with limit_http():
            r = requests.get(url, headers=_HEADERS, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("table.type_1")
        if not table:
            _set_cached(cache_key, [])
            return []

        for row in table.select("tr"):
            cells = row.select("td")
            if len(cells) < 6:
                continue

            # columns: 종목명, 제목/링크, 증권사, 의견, 목표가, 날짜
            title_el = cells[1].select_one("a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            report_url = f"https://finance.naver.com/research/{href}" if href and not href.startswith("http") else href

            broker = cells[2].get_text(strip=True)
            opinion = cells[3].get_text(strip=True)  # 매수/중립/매도
            target_price_text = cells[4].get_text(strip=True).replace(",", "")
            date = cells[5].get_text(strip=True)

            target_price = None
            try:
                target_price = int(target_price_text) if target_price_text.isdigit() else None
            except (ValueError, TypeError):
                pass

            results.append({
                "title": title,
                "date": date,
                "broker": broker,
                "opinion": opinion,
                "target_price": target_price,
                "url": report_url,
                "source": "네이버 리서치",
            })

            if len(results) >= count:
                break

    except Exception:
        pass

    _set_cached(cache_key, results)
    return results


def fetch_naver_consensus(ticker: str) -> dict:
    """
    Fetch consensus estimates from Naver Finance.
    Returns {target_price, opinion_buy/hold/sell counts, eps_estimates, etc.}
    """
    if not (ticker.endswith(".KS") or ticker.endswith(".KQ")):
        return {}

    cache_key = f"naver_consensus:{ticker}"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    code = ticker.split(".")[0]
    result = {}

    try:
        url = f"https://finance.naver.com/item/coinfo.naver?code={code}&target=consensus_tab"
        with limit_http():
            r = requests.get(url, headers=_HEADERS, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # Target price consensus
        for div in soup.select("div.gray"):
            text = div.get_text()
            m = re.search(r"목표주가\s*(\d[\d,]*)", text)
            if m:
                result["consensus_target_price"] = int(m.group(1).replace(",", ""))
            m2 = re.search(r"투자의견\s*(\S+)", text)
            if m2:
                result["consensus_opinion"] = m2.group(1)

        # Also scrape from main page (more reliable)
        main_url = f"https://finance.naver.com/item/main.naver?code={code}"
        with limit_http():
            r2 = requests.get(main_url, headers=_HEADERS, timeout=10)
        if r2.status_code == 200:
            soup2 = BeautifulSoup(r2.text, "html.parser")
            # Consensus target price from main page
            for td in soup2.select("td"):
                text = td.get_text(strip=True)
                if "목표주가" in text:
                    m = re.search(r"([\d,]+)\s*원", text)
                    if m:
                        result["consensus_target_price"] = int(m.group(1).replace(",", ""))

    except Exception:
        pass

    _set_cached(cache_key, result)
    return result


# ═══════════════════════════════════════════════════════════
# 3. SEC EDGAR — US company filings
# ═══════════════════════════════════════════════════════════

# Common ticker → CIK mapping (most used US stocks)
_TICKER_CIK: dict[str, str] = {
    "NVDA": "1045810", "TSM": "1046179", "AVGO": "1649338",
    "TSLA": "1318605", "AAPL": "320193", "MSFT": "789019",
    "GOOGL": "1652044", "META": "1326801", "AMZN": "1018724",
    "AMD": "2488", "INTC": "50863", "ISRG": "1035267",
    "CEG": "1868275", "CCJ": "1005163", "CRWD": "1535527",
    "CRSP": "1674416", "LLY": "59478", "IONQ": "1812364",
    "RKLB": "1819994", "BE": "1664703", "LMT": "936468",
    "RTX": "101829", "GD": "40533",
}


def fetch_sec_filings(ticker: str, count: int = 8) -> list[dict]:
    """
    Fetch recent SEC EDGAR filings for a US stock.
    Returns list of {title, date, form_type, url}.
    Uses the free EDGAR EFTS full-text search API.
    """
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return []

    cache_key = f"sec:{ticker}"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    results = []
    cik = _TICKER_CIK.get(ticker.upper())

    try:
        if cik:
            # Use submissions API (faster, more reliable)
            url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
            headers = {
                "User-Agent": "StockAnalysisApp/1.0 tmddbsgld@naver.com",
                "Accept": "application/json",
            }
            with limit_http():
                r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                descs = recent.get("primaryDocument", [])
                acc_nos = recent.get("accessionNumber", [])

                # Filter to important filings only
                important_forms = {"10-K", "10-Q", "8-K", "6-K", "20-F", "S-1", "DEF 14A"}
                for i in range(min(len(forms), 50)):
                    if forms[i] not in important_forms:
                        continue
                    acc = acc_nos[i].replace("-", "") if i < len(acc_nos) else ""
                    doc = descs[i] if i < len(descs) else ""
                    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}" if acc and doc else ""
                    results.append({
                        "title": f"{forms[i]} Filing",
                        "date": dates[i] if i < len(dates) else "",
                        "form_type": forms[i],
                        "url": filing_url,
                        "source": "SEC EDGAR",
                    })
                    if len(results) >= count:
                        break
        else:
            # Search by ticker using EFTS
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2025-01-01&forms=10-K,10-Q,8-K"
            headers = {
                "User-Agent": "StockAnalysisApp/1.0 tmddbsgld@naver.com",
            }
            with limit_http():
                r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for hit in data.get("hits", {}).get("hits", [])[:count]:
                    src = hit.get("_source", {})
                    results.append({
                        "title": src.get("display_names", [ticker])[0] + f" - {src.get('form_type', '')}",
                        "date": src.get("file_date", ""),
                        "form_type": src.get("form_type", ""),
                        "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=&dateb=&owner=include&count=10",
                        "source": "SEC EDGAR",
                    })

    except Exception:
        pass

    _set_cached(cache_key, results)
    return results


# ═══════════════════════════════════════════════════════════
# 4. Yahoo Finance Analysis — US analyst ratings & targets
# ═══════════════════════════════════════════════════════════

def fetch_yahoo_analyst_data(ticker: str) -> dict:
    """
    Fetch analyst ratings, price targets, and EPS estimates from Yahoo Finance.
    Returns {target_price, recommendation, num_analysts, eps_current, eps_next, ...}
    """
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return {}

    cache_key = f"yahoo_analyst:{ticker}"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    result = {}

    try:
        if _cffi_available:
            session = CffiSession(impersonate="chrome")
            with limit_http():
                r = session.get(
                    f"https://finance.yahoo.com/quote/{ticker}/analysis/",
                    timeout=15
                )
            if r.status_code != 200:
                return {}
            html = r.text
        else:
            with limit_http():
                r = requests.get(
                    f"https://finance.yahoo.com/quote/{ticker}/analysis/",
                    headers=_HEADERS, timeout=15
                )
            if r.status_code != 200:
                return {}
            html = r.text

        soup = BeautifulSoup(html, "html.parser")

        # Parse analyst recommendation from page
        for section in soup.select("section"):
            heading = section.select_one("h2, h3")
            if not heading:
                continue
            h_text = heading.get_text(strip=True)

            if "Earnings Estimate" in h_text:
                rows = section.select("tr")
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.select("td, th")]
                    if len(cells) >= 3:
                        label = cells[0]
                        if "Avg. Estimate" in label:
                            result["eps_current_q"] = _parse_num(cells[1])
                            result["eps_next_q"] = _parse_num(cells[2]) if len(cells) > 2 else None
                        elif "No. of Analysts" in label:
                            result["num_analysts_eps"] = _parse_num(cells[1])

            if "Revenue Estimate" in h_text:
                rows = section.select("tr")
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.select("td, th")]
                    if len(cells) >= 3 and "Avg. Estimate" in cells[0]:
                        result["revenue_estimate_current"] = cells[1]
                        result["revenue_estimate_next"] = cells[2] if len(cells) > 2 else None

        # Target price from quote page
        try:
            if _cffi_available:
                with limit_http():
                    r2 = session.get(
                        f"https://finance.yahoo.com/quote/{ticker}/",
                        timeout=15
                    )
            else:
                with limit_http():
                    r2 = requests.get(
                        f"https://finance.yahoo.com/quote/{ticker}/",
                        headers=_HEADERS, timeout=15
                    )
            if r2.status_code == 200:
                soup2 = BeautifulSoup(r2.text, "html.parser")
                for li in soup2.select("li"):
                    text = li.get_text(strip=True)
                    if "1y Target Est" in text:
                        m = re.search(r"([\d,.]+)", text.replace("1y Target Est", ""))
                        if m:
                            result["target_price_1y"] = float(m.group(1).replace(",", ""))
                    elif "Recommendation" in text.lower():
                        m = re.search(r"([\d.]+)", text)
                        if m:
                            result["recommendation_score"] = float(m.group(1))

        except Exception:
            pass

    except Exception:
        pass

    _set_cached(cache_key, result)
    return result


def _parse_num(s: str) -> float | None:
    """Parse a number from analyst data, handling B/M/K suffixes."""
    if not s:
        return None
    s = s.strip().replace(",", "")
    if s in ("", "-", "N/A"):
        return None
    try:
        if s.endswith("B"):
            return float(s[:-1]) * 1e9
        elif s.endswith("M"):
            return float(s[:-1]) * 1e6
        elif s.endswith("K"):
            return float(s[:-1]) * 1e3
        return float(s)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════
# 5. Economic Calendar — Major upcoming events
# ═══════════════════════════════════════════════════════════

def fetch_investing_calendar() -> list[dict]:
    """
    Fetch upcoming major economic events from Investing.com calendar.
    Returns list of {event, date, time, country, importance, actual, forecast, previous}.
    """
    cache_key = "econ_calendar"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    results = []

    try:
        # Use the Investing.com economic calendar page
        url = "https://www.investing.com/economic-calendar/"
        headers = {
            **_HEADERS,
            "Referer": "https://www.investing.com/",
        }
        with limit_http():
            r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("table#economicCalendarData")
        if not table:
            _set_cached(cache_key, [])
            return []

        current_date = ""
        for row in table.select("tr"):
            # Date header rows
            date_cell = row.select_one("td.theDay")
            if date_cell:
                current_date = date_cell.get_text(strip=True)
                continue

            cells = row.select("td")
            if len(cells) < 5:
                continue

            time_text = cells[0].get_text(strip=True) if cells else ""
            country = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            # Importance: count bull icons
            importance = len(row.select("i.grayFullBullishIcon"))
            event_name = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            if not event_name or importance < 2:  # Only high-importance events
                continue

            actual = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            forecast = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            previous = cells[6].get_text(strip=True) if len(cells) > 6 else ""

            results.append({
                "event": event_name,
                "date": current_date,
                "time": time_text,
                "country": country,
                "importance": importance,
                "actual": actual,
                "forecast": forecast,
                "previous": previous,
                "source": "Economic Calendar",
            })

            if len(results) >= 20:
                break

    except Exception:
        pass

    _set_cached(cache_key, results)
    return results


# ═══════════════════════════════════════════════════════════
# 6. Naver Finance Industry News — sector-level intelligence
# ═══════════════════════════════════════════════════════════

def fetch_naver_industry_report(sector_keyword: str, count: int = 8) -> list[dict]:
    """
    Fetch industry/sector-level analyst reports from Naver Finance.
    Returns list of {title, date, broker, url}.
    """
    cache_key = f"naver_industry:{sector_keyword}"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached

    results = []

    try:
        url = f"https://finance.naver.com/research/industry_list.naver?keyword={quote(sector_keyword)}"
        with limit_http():
            r = requests.get(url, headers=_HEADERS, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("table.type_1")
        if not table:
            _set_cached(cache_key, [])
            return []

        for row in table.select("tr"):
            cells = row.select("td")
            if len(cells) < 4:
                continue
            title_el = cells[0].select_one("a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            report_url = f"https://finance.naver.com/research/{href}" if href and not href.startswith("http") else href
            broker = cells[1].get_text(strip=True)
            date = cells[2].get_text(strip=True)

            results.append({
                "title": title,
                "date": date,
                "broker": broker,
                "url": report_url,
                "source": "네이버 업종분석",
            })
            if len(results) >= count:
                break

    except Exception:
        pass

    _set_cached(cache_key, results)
    return results


# ═══════════════════════════════════════════════════════════
# 7. Unified fetch — all research for a single ticker
# ═══════════════════════════════════════════════════════════

def fetch_all_research(ticker: str) -> dict:
    """
    Fetch all available research data for a ticker.
    Returns {analyst_reports, filings, consensus, analyst_targets}.
    Dispatches to KRX or US sources based on ticker suffix.
    """
    cache_key = f"all_research:{ticker}"
    cached = _get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached

    is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")
    result = {
        "ticker": ticker,
        "analyst_reports": [],
        "filings": [],
        "consensus": {},
        "analyst_targets": {},
    }

    try:
        if is_krx:
            result["analyst_reports"] = fetch_naver_analyst_reports(ticker)
            result["filings"] = fetch_dart_disclosures(ticker)
            result["consensus"] = fetch_naver_consensus(ticker)
        else:
            result["filings"] = fetch_sec_filings(ticker)
            result["analyst_targets"] = fetch_yahoo_analyst_data(ticker)
    except Exception:
        pass

    _set_cached(cache_key, result)
    return result
