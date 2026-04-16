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
    Fetch PER, PBR, ROE, dividend yield, revenue growth, margins from Naver Pay Securities API.
    Primary: m.stock.naver.com JSON API (integration + finance).
    Fallback: finance.naver.com HTML scraping (fetch_company_profile).
    """
    try:
        from services.naver_finance import NaverFinanceService
    except ImportError:
        return {}

    code = ticker.split(".")[0]
    result: dict = {}

    # ── Primary: Naver Pay Securities JSON API ──
    integ = NaverFinanceService.fetch_stock_integration(code)
    if integ and len(integ) > 2:
        if integ.get("per") is not None:
            result["pe_ratio"] = integ["per"]
        if integ.get("forward_per") is not None:
            result["forward_pe"] = integ["forward_per"]
        if integ.get("pbr") is not None:
            result["price_to_book"] = integ["pbr"]
        if integ.get("dividend_yield") is not None:
            result["dividend_yield"] = integ["dividend_yield"]
        if integ.get("eps") is not None:
            result["eps"] = integ["eps"]
        if integ.get("forward_eps") is not None:
            result["forward_eps"] = integ["forward_eps"]
        if integ.get("bps") is not None:
            result["bps"] = integ["bps"]
        if integ.get("market_cap_억") is not None:
            result["market_cap"] = integ["market_cap_억"] * 100_000_000
        if integ.get("consensus_target_price") is not None:
            result["consensus_target_price"] = integ["consensus_target_price"]
            result["consensus_opinion"] = integ.get("consensus_opinion", "")

    # ── Supplement with financials API for growth/margins ──
    fin = NaverFinanceService.fetch_financials(code, "annual")
    if fin.get("revenue_growth") is not None:
        result["revenue_growth"] = fin["revenue_growth"]
    if fin.get("earnings_growth") is not None:
        result["earnings_growth"] = fin["earnings_growth"]
    if fin.get("operating_profit_growth") is not None:
        result["operating_profit_growth"] = fin["operating_profit_growth"]
    if fin.get("consensus_revenue_growth") is not None:
        result["consensus_revenue_growth"] = fin["consensus_revenue_growth"]

    # Get margins/ROE from financials rows (latest actual period)
    if fin.get("periods"):
        actual_periods = [p for p in fin["periods"] if not p.get("is_consensus")]
        if actual_periods:
            latest_key = actual_periods[-1]["key"]
            if fin.get("operating_margin"):
                v = fin["operating_margin"].get(latest_key)
                if v is not None:
                    result["operating_margin"] = v / 100
            if fin.get("net_margin"):
                v = fin["net_margin"].get(latest_key)
                if v is not None:
                    result["profit_margin"] = v / 100
            if fin.get("roe"):
                v = fin["roe"].get(latest_key)
                if v is not None:
                    result["roe"] = v / 100
            if fin.get("debt_ratio"):
                v = fin["debt_ratio"].get(latest_key)
                if v is not None:
                    result["debt_ratio"] = v / 100

    # ── Fallback: HTML scraping for any missing fields ──
    if len(result) < 5:
        profile = NaverFinanceService.fetch_company_profile(code)
        if profile:
            field_map = {
                "per": "pe_ratio", "forward_per": "forward_pe", "pbr": "price_to_book",
                "dividend_yield": "dividend_yield", "revenue_growth": "revenue_growth",
                "operating_margin": "operating_margin", "profit_margin": "profit_margin",
                "roe": "roe", "earnings_growth": "earnings_growth",
            }
            for src_key, dst_key in field_map.items():
                if dst_key not in result and profile.get(src_key) is not None:
                    result[dst_key] = profile[src_key]

    return result


# ─── US stocks: Finnhub API (primary for US) ───

def _fetch_finnhub_fundamentals(ticker: str) -> dict:
    """
    Fetch financial metrics from Finnhub API.
    Free tier: 60 calls/min — plenty for our use case with 30min cache.
    """
    try:
        from config import settings
        api_key = settings.FINNHUB_API_KEY
        if not api_key:
            return {}
    except Exception:
        return {}

    result: dict = {}
    try:
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={api_key}"
        with limit_http():
            r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"[FINNHUB] {ticker} status {r.status_code}")
            return {}

        data = r.json()
        m = data.get("metric", {})
        if not m:
            return {}

        # PE ratio
        pe = m.get("peBasicExclExtraTTM") or m.get("peTTM")
        if pe:
            result["pe_ratio"] = pe

        # Forward PE (from annual estimate)
        fpe = m.get("peBasicExclExtraAnnual")
        if fpe:
            result["forward_pe"] = fpe

        # Price to Book
        pb = m.get("pbQuarterly") or m.get("pbAnnual")
        if pb:
            result["price_to_book"] = pb

        # Profit margin (net margin)
        npm = m.get("netProfitMarginTTM") or m.get("netProfitMarginAnnual")
        if npm is not None:
            result["profit_margin"] = npm / 100

        # Operating margin
        opm = m.get("operatingMarginTTM") or m.get("operatingMarginAnnual")
        if opm is not None:
            result["operating_margin"] = opm / 100

        # ROE
        roe = m.get("roeTTM") or m.get("roeAnnual")
        if roe is not None:
            result["roe"] = roe / 100

        # Revenue growth (YoY)
        rg = m.get("revenueGrowthQuarterlyYoy") or m.get("revenueGrowth3Y")
        if rg is not None:
            result["revenue_growth"] = rg / 100

        # Earnings growth (EPS growth)
        eg = m.get("epsGrowthQuarterlyYoy") or m.get("epsGrowth3Y")
        if eg is not None:
            result["earnings_growth"] = eg / 100

        # Dividend yield
        dy = m.get("dividendYieldIndicatedAnnual")
        if dy is not None:
            result["dividend_yield"] = dy / 100

        # Market cap
        mc = m.get("marketCapitalization")
        if mc:
            result["market_cap"] = mc * 1_000_000  # Finnhub returns in millions

        # Beta
        beta = m.get("beta")
        if beta:
            result["beta"] = beta

        # Free cash flow
        fcf = m.get("freeCashFlowTTM")
        if fcf:
            result["free_cash_flow"] = fcf * 1_000_000

        if result:
            print(f"[FINNHUB] {ticker}: got {len(result)} metrics")

    except Exception as e:
        print(f"[FINNHUB] {ticker} error: {e}")

    return result


# ─── US stocks: Yahoo Finance web scraping (fallback) ───

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
        # US stocks: Finnhub first, then fill gaps with Yahoo scraping
        data = _fetch_finnhub_fundamentals(ticker)
        if len(data) < 5:
            # Not enough data from Finnhub — supplement with Yahoo
            yahoo = _fetch_yahoo_web_fundamentals(ticker)
            for k, v in yahoo.items():
                if k not in data or data[k] is None:
                    data[k] = v

    if data:
        _set_cached(cache_key, data)

    return data
