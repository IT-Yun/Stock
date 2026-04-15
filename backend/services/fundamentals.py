"""
Alternative fundamentals data service.
Provides earnings/valuation metrics from multiple sources to avoid
yfinance rate limits and fill gaps for Korean stocks.

Data sources:
  - Korean stocks (.KS/.KQ): Naver Finance (no rate limits, highly reliable)
  - US stocks: Yahoo Finance web scraping via curl_cffi (browser impersonation)
  - Fallback: yfinance quarterly_financials / balance_sheet (computed metrics)

All results are cached 30 min.
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from services.runtime_controls import limit_http

try:
    from curl_cffi.requests import Session as CffiSession
    _cffi_available = True
except ImportError:
    _cffi_available = False

_FUND_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 1800  # 30 min


def _get_cached(key: str) -> dict | None:
    cached = _FUND_CACHE.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    return None


def _set_cached(key: str, data: dict):
    _FUND_CACHE[key] = (time.time(), data)


def _parse_float(s: str | None) -> float | None:
    """Parse a float from a string, stripping %, commas, etc."""
    if not s:
        return None
    s = s.strip().replace(",", "").replace("%", "").replace("배", "")
    if s in ("", "-", "N/A", "nan"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ─── Korean stocks: Naver Finance ───

_NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def _fetch_naver_fundamentals(ticker: str) -> dict:
    """
    Fetch PER, PBR, ROE, dividend yield, revenue growth, margins from Naver Finance.
    Works for KRX stocks (.KS, .KQ). No rate limits.
    """
    code = ticker.split(".")[0]
    result: dict = {}

    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        with limit_http():
            r = requests.get(url, headers=_NAVER_HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # PER, PBR from dedicated elements
        per_el = soup.select_one("em#_per")
        pbr_el = soup.select_one("em#_pbr")
        cns_per_el = soup.select_one("em#_cns_per")

        if per_el:
            result["pe_ratio"] = _parse_float(per_el.text)
        if cns_per_el:
            result["forward_pe"] = _parse_float(cns_per_el.text)
        if pbr_el:
            result["price_to_book"] = _parse_float(pbr_el.text)

        # Dividend yield from per_table
        per_table = soup.select_one("table.per_table")
        if per_table:
            text = per_table.get_text()
            m = re.search(r"배당수익률.*?([\d.]+)\s*%", text, re.DOTALL)
            if m:
                result["dividend_yield"] = float(m.group(1)) / 100  # as ratio

        # Financial summary table (매출액, 영업이익, 영업이익률, ROE)
        for div in soup.select("div.section"):
            h4 = div.select_one("h4")
            if not h4 or "기업실적" not in h4.get_text():
                continue
            table = div.select_one("table")
            if not table:
                continue

            rows = {}
            for tr in table.select("tbody tr"):
                cells = [td.get_text(strip=True) for td in tr.select("td,th")]
                if len(cells) >= 3:
                    label = cells[0]
                    rows[label] = cells[1:]  # annual columns followed by quarterly

            # Revenue growth: compare last 2 annual columns
            if "매출액" in rows:
                rev_vals = rows["매출액"]
                if len(rev_vals) >= 2:
                    cur = _parse_float(rev_vals[1])  # most recent full year
                    prev = _parse_float(rev_vals[0])  # year before
                    if cur and prev and prev != 0:
                        result["revenue_growth"] = (cur - prev) / abs(prev)

            # Operating margin (latest)
            if "영업이익률" in rows:
                vals = rows["영업이익률"]
                for v in reversed(vals):
                    parsed = _parse_float(v)
                    if parsed is not None:
                        result["operating_margin"] = parsed / 100  # as ratio
                        break

            # Net profit margin
            if "순이익률" in rows:
                vals = rows["순이익률"]
                for v in reversed(vals):
                    parsed = _parse_float(v)
                    if parsed is not None:
                        result["profit_margin"] = parsed / 100
                        break

            # ROE
            if "ROE(지배주주)" in rows:
                vals = rows["ROE(지배주주)"]
                for v in reversed(vals):
                    parsed = _parse_float(v)
                    if parsed is not None:
                        result["roe"] = parsed / 100
                        break

            # Earnings growth from net income
            if "당기순이익" in rows:
                ni_vals = rows["당기순이익"]
                if len(ni_vals) >= 2:
                    cur = _parse_float(ni_vals[1])
                    prev = _parse_float(ni_vals[0])
                    if cur and prev and prev != 0:
                        result["earnings_growth"] = (cur - prev) / abs(prev)

    except Exception:
        pass

    return result


# ─── US stocks: Yahoo Finance web scraping ───

_YAHOO_IMPERSONATIONS = ["chrome", "safari", "safari_ios", "edge"]


def _fetch_yahoo_web_fundamentals(ticker: str) -> dict:
    """
    Scrape Yahoo Finance key-statistics page for US stocks.
    Uses curl_cffi with browser impersonation to bypass rate limits.
    """
    if not _cffi_available:
        return {}

    result: dict = {}
    try:
        session = CffiSession(impersonate="chrome")

        url = f"https://finance.yahoo.com/quote/{ticker}/key-statistics/"
        with limit_http():
            r = session.get(url, timeout=15)
        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, "html.parser")

        # Parse sections
        for section in soup.select("section"):
            h = section.select_one("h2, h3")
            if not h:
                continue
            heading = h.get_text(strip=True)

            for tr in section.select("tr"):
                cells = [td.get_text(strip=True) for td in tr.select("td")]
                if len(cells) < 2:
                    continue
                label = cells[0]
                value = cells[1]  # most recent value

                if "Trailing P/E" in label:
                    result["pe_ratio"] = _parse_float(value)
                elif "Forward P/E" in label:
                    result["forward_pe"] = _parse_float(value)
                elif "Price/Book" in label:
                    result["price_to_book"] = _parse_float(value)
                elif "Profit Margin" in label and "Operating" not in label:
                    v = _parse_float(value)
                    if v is not None:
                        result["profit_margin"] = v / 100
                elif "Operating Margin" in label:
                    v = _parse_float(value)
                    if v is not None:
                        result["operating_margin"] = v / 100
                elif "Return on Equity" in label:
                    v = _parse_float(value)
                    if v is not None:
                        result["roe"] = v / 100
                elif "Quarterly Revenue Growth" in label:
                    v = _parse_float(value)
                    if v is not None:
                        result["revenue_growth"] = v / 100
                elif "Quarterly Earnings Growth" in label:
                    v = _parse_float(value)
                    if v is not None:
                        result["earnings_growth"] = v / 100
                elif "Trailing Annual Dividend Yield" in label:
                    v = _parse_float(value)
                    if v is not None:
                        result["dividend_yield"] = v / 100
                elif "5 Year Average Dividend Yield" in label and "dividend_yield" not in result:
                    v = _parse_float(value)
                    if v is not None:
                        result["dividend_yield"] = v / 100

    except Exception:
        pass

    return result


# ─── Public API ───

def fetch_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamental metrics from the best available source.
    Returns dict with keys:
      revenue_growth, earnings_growth, profit_margin, operating_margin,
      roe, dividend_yield, price_to_book, pe_ratio, forward_pe
    All ratios are in decimal form (e.g., 0.25 = 25%).
    """
    cache_key = f"fund:{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")

    if is_krx:
        data = _fetch_naver_fundamentals(ticker)
    else:
        data = _fetch_yahoo_web_fundamentals(ticker)

    if data:
        _set_cached(cache_key, data)

    return data
