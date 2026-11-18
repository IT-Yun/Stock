"""
Naver Finance integration service for Korean stocks.

Provides:
  - Stock search (finance.naver.com/search)
  - Stock-specific news (finance.naver.com/item/news)
  - Company profile with fundamentals (finance.naver.com/item/main)

All results are cached with appropriate TTLs.
No rate limits on Naver Finance, but uses limit_http() for concurrency control.
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from services.runtime_controls import limit_http

_CACHE: dict[str, tuple[float, object]] = {}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def _get_cached(key: str, ttl: int):
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < ttl:
        return cached[1]
    return None


def _set_cached(key: str, value: object):
    _CACHE[key] = (time.time(), value)


def _parse_float(s: str | None) -> float | None:
    if not s:
        return None
    s = s.strip().replace(",", "").replace("%", "").replace("배", "").replace("원", "")
    if s in ("", "-", "N/A", "nan", "−"):
        return None
    # Handle negative sign variants
    s = s.replace("−", "-")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    s = s.strip().replace(",", "").replace("원", "").replace("주", "")
    if s in ("", "-", "N/A"):
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


class NaverFinanceService:
    """Korean stock data from Naver Finance (finance.naver.com)."""

    # ─── Stock Search ───

    @staticmethod
    def search_stocks(query: str, max_results: int = 10) -> list[dict]:
        """
        Search Naver Finance for Korean stocks using autocomplete API.
        Returns list of {code, name, market}.
        """
        cache_key = f"nf-search:{query}"
        cached = _get_cached(cache_key, 600)  # 10min
        if cached is not None:
            return cached

        results: list[dict] = []
        try:
            url = f"https://ac.stock.naver.com/ac?q={quote(query)}&target=stock"
            with limit_http():
                r = requests.get(url, headers=_HEADERS, timeout=8)
            if r.status_code != 200:
                return []

            data = r.json()
            for item in data.get("items", []):
                code = item.get("code", "")
                name = item.get("name", "")
                if not code or not name:
                    continue
                # Only Korean stocks
                if item.get("nationCode") != "KOR":
                    continue
                # Skip preferred shares (우선주)
                if name.endswith("우") and item.get("category") == "stock":
                    pass  # include preferred shares too
                type_code = item.get("typeCode", "KOSPI")
                market = "KOSPI" if type_code == "KOSPI" else "KOSDAQ"
                results.append({
                    "code": code,
                    "name": name,
                    "market": market,
                })
                if len(results) >= max_results:
                    break

        except Exception:
            pass

        _set_cached(cache_key, results)
        return results

    # ─── Stock-Specific News ───

    @staticmethod
    def fetch_stock_news(code: str, count: int = 15) -> list[dict]:
        """
        Fetch stock-SPECIFIC news from Naver Finance item news page.
        Every article here is directly about this stock — no relevance filtering needed.
        Returns list of {title, url, source, date, info_type}.
        """
        cache_key = f"nf-news:{code}"
        cached = _get_cached(cache_key, 180)  # 3min
        if cached is not None:
            return cached

        articles: list[dict] = []
        try:
            url = f"https://finance.naver.com/item/news.naver?code={code}&page=1"
            with limit_http():
                r = requests.get(url, headers=_HEADERS, timeout=8)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "html.parser")

            # Parse the news table — two sections: 관련기사 (related) and 뉴스
            # Both are in table.type5 rows
            for table in soup.select("table.type5"):
                for tr in table.select("tbody tr"):
                    # Skip separator rows
                    if tr.get("class") and any(c in ("blank", "relation_tit") for c in tr.get("class", [])):
                        continue

                    title_tag = tr.select_one("td.title a")
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    if not title:
                        continue

                    href = title_tag.get("href", "")
                    # Build full URL
                    if href and not href.startswith("http"):
                        article_url = f"https://finance.naver.com{href}"
                    else:
                        article_url = href

                    # Source (info provider)
                    source_tag = tr.select_one("td.info")
                    source = source_tag.get_text(strip=True) if source_tag else "네이버 금융"

                    # Date
                    date_tag = tr.select_one("td.date")
                    date = date_tag.get_text(strip=True) if date_tag else None

                    articles.append({
                        "title": title,
                        "url": article_url,
                        "source": source,
                        "date": date,
                    })

                    if len(articles) >= count:
                        break
                if len(articles) >= count:
                    break

        except Exception:
            pass

        _set_cached(cache_key, articles)
        return articles

    # ─── Company Profile (comprehensive) ───

    @staticmethod
    def fetch_company_profile(code: str) -> dict:
        """
        Fetch comprehensive company profile from Naver Finance main page.
        Single HTTP request replaces both _fetch_stock_industry() and _fetch_naver_fundamentals().

        Returns dict with: name, industry, sector, current_price, market_cap,
        per, pbr, roe, dividend_yield, revenue_growth, operating_margin, profit_margin,
        foreign_ownership_pct, business_summary, etc.
        """
        cache_key = f"nf-profile:{code}"
        cached = _get_cached(cache_key, 1800)  # 30min
        if cached is not None:
            return cached

        result: dict = {"code": code}
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            with limit_http():
                r = requests.get(url, headers=_HEADERS, timeout=10)
            if r.status_code != 200:
                return result

            soup = BeautifulSoup(r.text, "html.parser")

            # ── Company name ──
            name_el = soup.select_one("div.wrap_company h2 a")
            if name_el:
                result["name"] = name_el.get_text(strip=True)

            # ── Current price ──
            price_el = soup.select_one("p.no_today span.blind")
            if price_el:
                result["current_price"] = _parse_int(price_el.get_text(strip=True))

            # ── PER, PBR from dedicated elements ──
            per_el = soup.select_one("em#_per")
            pbr_el = soup.select_one("em#_pbr")
            cns_per_el = soup.select_one("em#_cns_per")

            if per_el:
                result["per"] = _parse_float(per_el.text)
            if cns_per_el:
                result["forward_per"] = _parse_float(cns_per_el.text)
            if pbr_el:
                result["pbr"] = _parse_float(pbr_el.text)

            # ── Dividend yield from per_table ──
            per_table = soup.select_one("table.per_table")
            if per_table:
                text = per_table.get_text()
                m = re.search(r"배당수익률.*?([\d.]+)\s*%", text, re.DOTALL)
                if m:
                    result["dividend_yield"] = float(m.group(1)) / 100

            # ── Industry / sector ──
            # Method 1: trade_compare category link
            category_el = soup.select_one("div.trade_compare em a")
            if category_el:
                result["industry"] = category_el.get_text(strip=True)

            # Method 2: sub_section with 업종
            if "industry" not in result:
                for section in soup.select("div.section div.sub_section"):
                    text = section.get_text()
                    if "업종" in text:
                        a_tag = section.select_one("a")
                        if a_tag:
                            result["industry"] = a_tag.get_text(strip=True)
                            break

            # ── Market cap ──
            for em in soup.select("em"):
                prev = em.find_previous_sibling(string=True) or ""
                parent_text = (em.parent.get_text() if em.parent else "") if not prev.strip() else prev.strip()
                # Market cap is usually near "시가총액" text
            # More reliable: parse from the table
            for table in soup.select("table"):
                table_text = table.get_text()
                if "시가총액" in table_text:
                    for tr in table.select("tr"):
                        cells = tr.select("td,th")
                        for i, cell in enumerate(cells):
                            if "시가총액" in cell.get_text():
                                # Next cell or em inside has the value
                                em = cell.select_one("em") or (cells[i + 1] if i + 1 < len(cells) else None)
                                if em:
                                    val_text = em.get_text(strip=True).replace(",", "").replace("조", "").replace("억", "")
                                    # Parse "XX조 YY억원" pattern from full text
                                    full = cell.get_text()
                                    jo_match = re.search(r"(\d[\d,]*)\s*조", full)
                                    eok_match = re.search(r"조\s*(\d[\d,]*)\s*억", full)
                                    if jo_match:
                                        jo = int(jo_match.group(1).replace(",", ""))
                                        eok = int(eok_match.group(1).replace(",", "")) if eok_match else 0
                                        result["market_cap_억"] = jo * 10000 + eok
                    break

            # ── Foreign ownership ──
            for td in soup.select("td"):
                text = td.get_text(strip=True)
                if "외국인" in text and "%" in text:
                    pct_match = re.search(r"([\d.]+)\s*%", text)
                    if pct_match:
                        result["foreign_ownership_pct"] = float(pct_match.group(1))
                        break

            # ── Financial summary table (매출액, 영업이익, 영업이익률, ROE) ──
            for div in soup.select("div.section"):
                h4 = div.select_one("h4")
                if not h4 or "기업실적" not in h4.get_text():
                    continue
                table = div.select_one("table")
                if not table:
                    continue

                rows: dict[str, list[str]] = {}
                for tr in table.select("tbody tr"):
                    cells = [td.get_text(strip=True) for td in tr.select("td,th")]
                    if len(cells) >= 3:
                        label = cells[0]
                        rows[label] = cells[1:]

                # Revenue growth: compare last 2 annual columns
                if "매출액" in rows:
                    rev_vals = rows["매출액"]
                    if len(rev_vals) >= 2:
                        cur = _parse_float(rev_vals[1])
                        prev = _parse_float(rev_vals[0])
                        if cur and prev and prev != 0:
                            result["revenue_growth"] = (cur - prev) / abs(prev)

                # Operating margin
                if "영업이익률" in rows:
                    for v in reversed(rows["영업이익률"]):
                        parsed = _parse_float(v)
                        if parsed is not None:
                            result["operating_margin"] = parsed / 100
                            break

                # Profit margin
                if "순이익률" in rows:
                    for v in reversed(rows["순이익률"]):
                        parsed = _parse_float(v)
                        if parsed is not None:
                            result["profit_margin"] = parsed / 100
                            break

                # ROE
                if "ROE(지배주주)" in rows:
                    for v in reversed(rows["ROE(지배주주)"]):
                        parsed = _parse_float(v)
                        if parsed is not None:
                            result["roe"] = parsed / 100
                            break

                # Earnings growth
                if "당기순이익" in rows:
                    ni_vals = rows["당기순이익"]
                    if len(ni_vals) >= 2:
                        cur = _parse_float(ni_vals[1])
                        prev = _parse_float(ni_vals[0])
                        if cur and prev and prev != 0:
                            result["earnings_growth"] = (cur - prev) / abs(prev)
                break

            # ── Business summary (기업개요) ──
            # Try to get from the corporate overview section
            for div in soup.select("div.section"):
                h4 = div.select_one("h4")
                if not h4:
                    continue
                h4_text = h4.get_text(strip=True)
                if "기업개요" in h4_text or "기업현황" in h4_text:
                    summary_el = div.select_one("div.summary_info, p")
                    if summary_el:
                        result["business_summary"] = summary_el.get_text(strip=True)[:500]
                    break

        except Exception:
            pass

        if len(result) > 1:  # more than just "code"
            _set_cached(cache_key, result)
        return result

    # ─── Naver Pay Securities JSON APIs (m.stock.naver.com) ───
    # Clean JSON, no HTML parsing needed. No auth required.

    _NPAY_BASE = "https://m.stock.naver.com/api/stock"
    _NPAY_HEADERS = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    }

    @staticmethod
    def _npay_parse_number(s: str | None) -> float | None:
        """Parse Korean-formatted number string: '1,271조 5,656억', '+64,984', '33.14배', '0.77%' etc."""
        if not s:
            return None
        s = s.strip()
        if s in ("", "-", "N/A"):
            return None

        # Handle 조/억 pattern: "1,271조 5,656억"
        jo_match = re.search(r'([\d,]+)\s*조', s)
        eok_match = re.search(r'조\s*([\d,]+)\s*억', s)
        if jo_match:
            jo = int(jo_match.group(1).replace(",", ""))
            eok = int(eok_match.group(1).replace(",", "")) if eok_match else 0
            return float(jo * 10000 + eok)  # return in 억 units

        # Strip suffixes
        s = s.replace(",", "").replace("배", "").replace("원", "").replace("%", "").replace("백만", "")
        s = s.replace("+", "").strip()
        if s in ("", "-", "N/A"):
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def fetch_stock_integration(code: str) -> dict:
        """
        Fetch comprehensive stock data from Naver Pay Securities integration API.
        Single API call returns: valuation metrics, consensus, investor flow, peers, analyst reports.
        Cache: 10 min (real-time price data included).
        """
        cache_key = f"npay-integration:{code}"
        cached = _get_cached(cache_key, 600)
        if cached is not None:
            return cached

        result: dict = {"code": code}
        parse = NaverFinanceService._npay_parse_number

        try:
            url = f"{NaverFinanceService._NPAY_BASE}/{code}/integration"
            with limit_http():
                r = requests.get(url, headers=NaverFinanceService._NPAY_HEADERS, timeout=10)
            if r.status_code != 200:
                return result
            data = r.json()

            result["name"] = data.get("stockName", "")

            # ── Parse totalInfos (valuation metrics) ──
            info_map: dict[str, str] = {}
            for item in data.get("totalInfos", []):
                info_map[item.get("code", "")] = item.get("value", "")

            if info_map.get("per"):
                result["per"] = parse(info_map["per"])
            if info_map.get("cnsPer"):
                result["forward_per"] = parse(info_map["cnsPer"])
            if info_map.get("eps"):
                result["eps"] = parse(info_map["eps"])
            if info_map.get("cnsEps"):
                result["forward_eps"] = parse(info_map["cnsEps"])
            if info_map.get("pbr"):
                result["pbr"] = parse(info_map["pbr"])
            if info_map.get("bps"):
                result["bps"] = parse(info_map["bps"])
            if info_map.get("dividendYieldRatio"):
                v = parse(info_map["dividendYieldRatio"])
                if v is not None:
                    result["dividend_yield"] = v / 100
            if info_map.get("dividend"):
                result["dividend_per_share"] = parse(info_map["dividend"])
            if info_map.get("marketValue"):
                # Returns in 억 units via our parser
                result["market_cap_억"] = parse(info_map["marketValue"])
            if info_map.get("foreignRate"):
                result["foreign_ownership_pct"] = parse(info_map["foreignRate"])
            if info_map.get("highPriceOf52Weeks"):
                result["high_52w"] = parse(info_map["highPriceOf52Weeks"])
            if info_map.get("lowPriceOf52Weeks"):
                result["low_52w"] = parse(info_map["lowPriceOf52Weeks"])
            if info_map.get("accumulatedTradingVolume"):
                result["volume"] = parse(info_map["accumulatedTradingVolume"])
            # Current price from lastClosePrice or openPrice
            for key in ("lastClosePrice", "openPrice"):
                if info_map.get(key):
                    result["current_price"] = parse(info_map[key])
                    break

            # ── Consensus (analyst target price + recommendation) ──
            consensus = data.get("consensusInfo")
            if consensus:
                tp = parse(consensus.get("priceTargetMean"))
                if tp:
                    result["consensus_target_price"] = tp
                rec = parse(consensus.get("recommMean"))
                if rec:
                    # 5=Strong Buy, 4=Buy, 3=Hold, 2=Sell, 1=Strong Sell
                    result["consensus_score"] = rec
                    if rec >= 4.5:
                        result["consensus_opinion"] = "적극매수"
                    elif rec >= 3.5:
                        result["consensus_opinion"] = "매수"
                    elif rec >= 2.5:
                        result["consensus_opinion"] = "중립"
                    elif rec >= 1.5:
                        result["consensus_opinion"] = "매도"
                    else:
                        result["consensus_opinion"] = "적극매도"
                result["consensus_date"] = consensus.get("createDate", "")

            # ── Investor flow (5-day) ──
            deal_trends = data.get("dealTrendInfos", [])
            if deal_trends:
                investor_flow = []
                for dt in deal_trends[:5]:
                    investor_flow.append({
                        "date": dt.get("bizdate", ""),
                        "foreign": parse(dt.get("foreignerPureBuyQuant")),
                        "institution": parse(dt.get("organPureBuyQuant")),
                        "individual": parse(dt.get("individualPureBuyQuant")),
                        "foreign_hold_pct": parse(dt.get("foreignerHoldRatio")),
                    })
                result["investor_flow"] = investor_flow

                # Summary: 5-day cumulative
                foreign_5d = sum(f.get("foreign") or 0 for f in investor_flow)
                inst_5d = sum(f.get("institution") or 0 for f in investor_flow)
                result["foreign_net_5d"] = foreign_5d
                result["institution_net_5d"] = inst_5d

            # ── Industry peers ──
            peers_raw = data.get("industryCompareInfo", [])
            if peers_raw:
                peers = []
                for p in peers_raw[:6]:
                    peers.append({
                        "code": p.get("itemCode", ""),
                        "name": p.get("stockName", ""),
                        "price": parse(p.get("closePrice")),
                        "change_pct": parse(p.get("fluctuationsRatio")),
                        "market_cap": parse(p.get("marketValue")),
                        "market": p.get("stockExchangeType", {}).get("nameKor", ""),
                    })
                result["peers"] = peers

            # ── Recent analyst reports ──
            researches = data.get("researches", [])
            if researches:
                reports = []
                for rpt in researches[:5]:
                    reports.append({
                        "title": rpt.get("tit", ""),
                        "broker": rpt.get("bnm", ""),
                        "date": rpt.get("wdt", ""),
                        "views": parse(rpt.get("rcnt")),
                    })
                result["recent_reports"] = reports

        except Exception as e:
            print(f"[NPAY] integration {code} error: {e}")

        if len(result) > 1:
            _set_cached(cache_key, result)
        return result

    @staticmethod
    def fetch_financials(code: str, period: str = "annual") -> dict:
        """
        Fetch financial statements from Naver Pay Securities.
        period: 'annual' or 'quarter'
        Returns dict with revenue, operating_profit, net_income, etc. per period.
        Cache: 30 min.
        """
        cache_key = f"npay-finance:{code}:{period}"
        cached = _get_cached(cache_key, 1800)
        if cached is not None:
            return cached

        parse = NaverFinanceService._npay_parse_number
        result: dict = {"code": code, "period": period, "statements": []}

        try:
            url = f"{NaverFinanceService._NPAY_BASE}/{code}/finance/{period}"
            with limit_http():
                r = requests.get(url, headers=NaverFinanceService._NPAY_HEADERS, timeout=10)
            if r.status_code != 200:
                return result
            data = r.json()

            fi = data.get("financeInfo", {})
            titles = fi.get("trTitleList", [])
            rows = fi.get("rowList", [])

            if not titles or not rows:
                return result

            # Build period list (sorted by key)
            period_keys = sorted([t["key"] for t in titles], key=lambda k: k)
            result["periods"] = []
            for t in sorted(titles, key=lambda x: x["key"]):
                result["periods"].append({
                    "key": t["key"],
                    "title": t.get("title", ""),
                    "is_consensus": t.get("isConsensus") == "Y",
                })

            # Parse each financial row
            row_map: dict[str, str] = {
                "매출액": "revenue",
                "영업이익": "operating_profit",
                "당기순이익": "net_income",
                "지배주주순이익": "controlling_net_income",
                "영업이익률": "operating_margin",
                "순이익률": "net_margin",
                "ROE(지배주주)": "roe",
                "부채비율": "debt_ratio",
                "당좌비율": "quick_ratio",
                "유보율": "retention_ratio",
                "EPS(원)": "eps",
                "PER(배)": "per",
                "BPS(원)": "bps",
                "PBR(배)": "pbr",
                "주당배당금(원)": "dps",
                "배당수익률(%)": "dividend_yield",
                "배당성향(%)": "payout_ratio",
            }

            for row in rows:
                title = row.get("title", "").strip()
                metric_key = row_map.get(title)
                if not metric_key:
                    continue
                cols = row.get("columns", {})
                values: dict[str, float | None] = {}
                for pk in period_keys:
                    cell = cols.get(pk, {})
                    values[pk] = parse(cell.get("value"))
                result[metric_key] = values

            # Compute growth rates from revenue
            if "revenue" in result and len(period_keys) >= 2:
                rev = result["revenue"]
                # Find last two non-consensus actual periods
                actual_keys = [t["key"] for t in sorted(titles, key=lambda x: x["key"]) if t.get("isConsensus") != "Y"]
                if len(actual_keys) >= 2:
                    prev_rev = rev.get(actual_keys[-2])
                    cur_rev = rev.get(actual_keys[-1])
                    if prev_rev and cur_rev and prev_rev != 0:
                        result["revenue_growth"] = (cur_rev - prev_rev) / abs(prev_rev)
                    prev_op = (result.get("operating_profit") or {}).get(actual_keys[-2])
                    cur_op = (result.get("operating_profit") or {}).get(actual_keys[-1])
                    if prev_op and cur_op and prev_op != 0:
                        result["operating_profit_growth"] = (cur_op - prev_op) / abs(prev_op)
                    prev_ni = (result.get("net_income") or {}).get(actual_keys[-2])
                    cur_ni = (result.get("net_income") or {}).get(actual_keys[-1])
                    if prev_ni and cur_ni and prev_ni != 0:
                        result["earnings_growth"] = (cur_ni - prev_ni) / abs(prev_ni)

                # Consensus growth (next year vs latest actual)
                consensus_keys = [t["key"] for t in sorted(titles, key=lambda x: x["key"]) if t.get("isConsensus") == "Y"]
                if actual_keys and consensus_keys:
                    latest_actual = rev.get(actual_keys[-1])
                    next_consensus = rev.get(consensus_keys[0])
                    if latest_actual and next_consensus and latest_actual != 0:
                        result["consensus_revenue_growth"] = (next_consensus - latest_actual) / abs(latest_actual)

        except Exception as e:
            print(f"[NPAY] finance {code} error: {e}")

        if result.get("periods"):
            _set_cached(cache_key, result)
        return result

    @staticmethod
    def fetch_investor_trend(code: str) -> dict:
        """
        Fetch 5-day investor trend (foreign/institution/individual net buy).
        Cache: 10 min.
        """
        cache_key = f"npay-trend:{code}"
        cached = _get_cached(cache_key, 600)
        if cached is not None:
            return cached

        parse = NaverFinanceService._npay_parse_number
        result: dict = {"code": code, "trend": []}

        try:
            url = f"{NaverFinanceService._NPAY_BASE}/{code}/trend"
            with limit_http():
                r = requests.get(url, headers=NaverFinanceService._NPAY_HEADERS, timeout=10)
            if r.status_code != 200:
                return result
            data = r.json()

            if not isinstance(data, list):
                return result

            for entry in data[:10]:
                result["trend"].append({
                    "date": entry.get("bizdate", ""),
                    "foreign": parse(entry.get("foreignerPureBuyQuant")),
                    "foreign_hold_pct": parse(entry.get("foreignerHoldRatio")),
                    "institution": parse(entry.get("organPureBuyQuant")),
                    "individual": parse(entry.get("individualPureBuyQuant")),
                    "close": parse(entry.get("closePrice")),
                    "volume": parse(entry.get("accumulatedTradingVolume")),
                })

            if result["trend"]:
                # 5-day summary
                foreign_sum = sum(t.get("foreign") or 0 for t in result["trend"][:5])
                inst_sum = sum(t.get("institution") or 0 for t in result["trend"][:5])
                indiv_sum = sum(t.get("individual") or 0 for t in result["trend"][:5])
                result["summary"] = {
                    "foreign_net_5d": foreign_sum,
                    "institution_net_5d": inst_sum,
                    "individual_net_5d": indiv_sum,
                    "foreign_buying": foreign_sum > 0,
                    "institution_buying": inst_sum > 0,
                }

        except Exception as e:
            print(f"[NPAY] trend {code} error: {e}")

        if result.get("trend"):
            _set_cached(cache_key, result)
        return result
