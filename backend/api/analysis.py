import pandas as pd
import numpy as np
import re
import time
import requests
import yfinance as yf
from fastapi import APIRouter
from bs4 import BeautifulSoup
from models.schemas import AnalysisResult, TechnicalIndicators, CommodityPrice
from services.stock_data import StockDataService
from services.technical_analysis import TechnicalAnalysisService
from services.commodity_data import CommodityDataService
from services.news_crawler import NewsCrawlerService

router = APIRouter(prefix="/api", tags=["analysis"])


_ANALYSIS_CACHE: dict[str, tuple[float, object]] = {}
ANALYSIS_CACHE_TTL = 300


def _get_cached(key: str):
    cached = _ANALYSIS_CACHE.get(key)
    if cached and time.time() - cached[0] < ANALYSIS_CACHE_TTL:
        return cached[1]
    return None


def _set_cached(key: str, value: object, ttl: int = ANALYSIS_CACHE_TTL):
    _ANALYSIS_CACHE[key] = (time.time(), value)


def _get_cached_ttl(key: str, ttl: int):
    cached = _ANALYSIS_CACHE.get(key)
    if cached and time.time() - cached[0] < ttl:
        return cached[1]
    return None


ISSUE_KEYWORDS: dict[str, list[str]] = {
    "실적": ["earnings", "revenue", "profit", "guidance", "실적", "잠정", "매출", "영업이익", "순이익"],
    "가이던스": ["guidance", "outlook", "forecast", "가이던스", "전망", "목표"],
    "수급": ["volume", "flow", "upgrade", "downgrade", "수급", "매수", "매도", "투자의견"],
    "규제": ["regulation", "ban", "tariff", "probe", "lawsuit", "규제", "소송", "관세", "제재"],
    "제품": ["launch", "shipment", "release", "approval", "수주", "출시", "승인", "양산", "공급"],
    "원가/원자재": ["oil", "copper", "uranium", "lithium", "dram", "nand", "구리", "우라늄", "리튬", "dram", "nand"],
    "매크로": ["cpi", "fed", "rate", "inflation", "macro", "금리", "인플레이션", "환율", "경기"],
}

NEWS_DRIVER_KEYWORDS: dict[str, list[str]] = {
    "HBM/메모리": ["hbm", "dram", "nand", "memory", "메모리", "디램", "낸드"],
    "AI CAPEX": ["capex", "data center", "datacenter", "gpu", "ai spending", "ai 투자", "데이터센터"],
    "고객사/공급": ["supply", "shipment", "customer", "approval", "certification", "납품", "공급", "인증", "승인"],
    "실적/가이던스": ["earnings", "guidance", "results", "revenue", "profit", "실적", "가이던스", "매출", "영업이익"],
    "가격/업황": ["price", "pricing", "spot", "contract", "업황", "가격", "현물", "계약가격"],
    "정책/규제": ["regulation", "tariff", "ban", "export control", "규제", "관세", "제재", "수출규제"],
    "수주/제품": ["launch", "order", "deal", "contract", "수주", "출시", "계약", "파트너십"],
}


def _issue_category_from_titles(titles: list[str]) -> str:
    combined = " ".join(titles).lower()
    best_category = "이슈"
    best_score = 0
    for category, keywords in ISSUE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in combined)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def _summarize_move_issue(titles: list[str], pct: float, volume_ratio: float) -> tuple[str, str]:
    category = _issue_category_from_titles(titles)
    direction = "상방" if pct > 0 else "하방"
    volume_note = "거래 동반" if volume_ratio >= 1.5 else "거래 무난"

    if category == "실적":
        summary = f"실적/잠정실적 이슈가 {direction} 변동을 만든 구간"
    elif category == "가이던스":
        summary = f"가이던스 기대 또는 실망이 반영된 구간"
    elif category == "규제":
        summary = f"규제·정책 관련 뉴스가 가격에 반영된 구간"
    elif category == "제품":
        summary = f"출시·수주·승인 같은 사업 이벤트가 반영된 구간"
    elif category == "원가/원자재":
        summary = f"원자재/업황 변화가 선반영된 구간"
    elif category == "매크로":
        summary = f"금리·환율·매크로 변화가 반영된 구간"
    elif category == "수급":
        summary = f"수급 변화와 리포트 영향이 반영된 구간"
    else:
        summary = "복합 이슈가 반영된 변동 구간"

    return category, f"{summary} · {volume_note}"


def _classify_news_driver(title: str) -> str:
    text = (title or "").lower()
    best_label = "일반"
    best_score = 0
    for label, keywords in NEWS_DRIVER_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_label = label
    return best_label


def _build_stock_news_queries(ticker: str, info: dict | None = None, sector_id: str | None = None) -> list[str]:
    normalized = _ticker_key(ticker)
    company_name = str((info or {}).get("shortName") or (info or {}).get("longName") or ticker).strip()
    queries: list[str] = [company_name, normalized]

    if normalized in {"005930.KS", "005930"}:
        queries.extend(["삼성전자 HBM", "삼성전자 반도체", "Samsung Electronics HBM", "Samsung foundry"])
    elif normalized in {"000660.KS", "000660"}:
        queries.extend(["SK하이닉스 HBM", "SK hynix NVIDIA HBM", "SK hynix DRAM"])
    elif normalized == "NVDA":
        queries.extend(["NVIDIA HBM supply", "NVIDIA AI capex", "엔비디아 HBM"])
    elif normalized == "TSM":
        queries.extend(["TSMC CoWoS", "TSMC 2nm", "TSMC AI demand"])
    elif normalized == "AVGO":
        queries.extend(["Broadcom custom AI chip", "Broadcom VMware synergy"])

    sector_terms = {
        "ai-semi": ["HBM", "semiconductor", "AI chip"],
        "robotics": ["robot", "automation"],
        "smr-nuclear": ["nuclear", "uranium", "power"],
        "cybersec": ["cybersecurity", "security platform"],
        "space": ["space", "launch", "satellite"],
        "biotech": ["drug", "clinical", "approval"],
        "quantum": ["quantum", "roadmap"],
        "hydrogen": ["hydrogen", "fuel cell", "clean energy"],
    }.get(sector_id or "", [])
    for term in sector_terms[:2]:
        queries.append(f"{company_name} {term}")

    deduped: list[str] = []
    seen = set()
    for query in queries:
        query = query.strip()
        if query and query.lower() not in seen:
            seen.add(query.lower())
            deduped.append(query)
    return deduped[:6]


def _extract_news_drivers(ticker: str, info: dict | None = None, sector_id: str | None = None) -> list[dict]:
    cache_key = f"news-drivers:{_ticker_key(ticker)}"
    cached = _get_cached_ttl(cache_key, 900)
    if cached is not None:
        return cached

    articles = []
    seen_titles = set()
    for query in _build_stock_news_queries(ticker, info=info, sector_id=sector_id):
        try:
            for article in NewsCrawlerService.search_news(query)[:8]:
                title = getattr(article, "title", "") or ""
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    articles.append(article)
        except Exception:
            pass

    buckets: dict[str, dict] = {}
    for article in articles[:30]:
        title = getattr(article, "title", "") or ""
        if not title:
            continue
        label = _classify_news_driver(title)
        bucket = buckets.setdefault(label, {
            "name": label,
            "count": 0,
            "headlines": [],
            "why_it_matters": "",
        })
        bucket["count"] += 1
        if len(bucket["headlines"]) < 3:
            bucket["headlines"].append(title)

    why_map = {
        "HBM/메모리": "메모리·HBM 관련 뉴스 빈도는 공급/점유율 기대를 선반영하는 경우가 많습니다.",
        "AI CAPEX": "대형 고객 투자 뉴스는 수요 지속성 기대를 가장 빠르게 흔듭니다.",
        "고객사/공급": "고객사 승인·공급 기사 방향은 실제 매출 반영 전에 주가가 먼저 반응합니다.",
        "실적/가이던스": "실적과 가이던스 헤드라인은 밸류 재평가의 직접 트리거입니다.",
        "가격/업황": "가격과 업황 기사 흐름은 사이클 피크아웃 여부를 빠르게 보여줍니다.",
        "정책/규제": "정책·규제 이슈는 실적보다 먼저 멀티플에 반영됩니다.",
        "수주/제품": "신제품·수주 기사는 기대감의 확장 여부를 보여줍니다.",
        "일반": "반복 노출되는 일반 이슈도 단기 수급에는 영향을 줄 수 있습니다.",
    }

    results = []
    for label, bucket in buckets.items():
        results.append({
            "name": label,
            "count": bucket["count"],
            "headlines": bucket["headlines"],
            "why_it_matters": why_map.get(label, why_map["일반"]),
        })
    results.sort(key=lambda item: item["count"], reverse=True)
    results = results[:5]
    _set_cached(cache_key, results)
    return results


def _score_live_article_impact(title: str, ticker: str, company_name: str, sector_id: str | None) -> int:
    """Score article relevance. MUST contain company name or ticker to score above threshold."""
    text = (title or "").lower()
    score = 0

    # Hard requirement: article must mention the company or ticker
    company_lower = (company_name or "").lower().strip()
    ticker_base = _ticker_key(ticker).replace(".KS", "").replace(".KQ", "").lower()

    # Build name variants for matching
    name_variants = [company_lower]
    # For Korean companies, try shorter name (e.g., "삼성전자" from "SamsungElec")
    if company_lower:
        # Split on spaces, try each part that's >= 2 chars
        for part in company_lower.split():
            if len(part) >= 2:
                name_variants.append(part)

    has_company_mention = any(variant in text for variant in name_variants if variant)
    has_ticker_mention = bool(ticker_base) and ticker_base in text

    if not has_company_mention and not has_ticker_mention:
        return 0  # Completely irrelevant — reject immediately

    if has_company_mention:
        score += 6
    if has_ticker_mention:
        score += 4

    # Bonus for actionable content
    if any(word in text for word in ["실적", "매출", "영업이익", "earnings", "revenue", "profit", "가이던스", "guidance"]):
        score += 3
    if any(word in text for word in ["승인", "approval", "수주", "contract", "deal", "계약", "납품"]):
        score += 3
    if any(word in text for word in ["하락", "부진", "miss", "falls", "delay", "지연", "리콜", "규제", "소송"]):
        score += 2
    if any(word in text for word in ["상승", "호실적", "beat", "surge", "record", "신고가", "목표가"]):
        score += 2

    return score


POSITIVE_KEYWORDS = ["상승", "호실적", "beat", "surge", "record", "신고가", "목표가", "수혜", "호재",
                     "승인", "approval", "수주", "contract", "deal", "계약", "긍정", "확대", "성장",
                     "상향", "upgrade", "outperform", "매수", "돌파", "최고", "흑자", "개선"]
NEGATIVE_KEYWORDS = ["하락", "부진", "miss", "falls", "slump", "delay", "지연", "리콜", "규제",
                     "소송", "lawsuit", "probe", "악재", "우려", "하향", "downgrade", "매도",
                     "적자", "감소", "축소", "실패", "위험", "이탈", "sell", "warning"]


def _explain_live_article_impact(title: str, ticker: str, sector_id: str | None) -> tuple[str, str]:
    """Generate a SPECIFIC explanation based on actual article title content."""
    text = (title or "").lower()

    # Determine sentiment
    pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text]
    neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text]

    if len(pos_hits) > len(neg_hits):
        direction = "positive"
    elif len(neg_hits) > len(pos_hits):
        direction = "negative"
    else:
        direction = "neutral"

    # Classify the issue type
    label = _classify_news_driver(title)

    # Build explanation from actual title content
    title_clean = title.strip()
    if direction == "positive":
        if "실적" in text or "매출" in text or "영업이익" in text or "earnings" in text:
            explanation = f"호재 — {title_clean}. 실적 개선/호실적 기대는 주가 상승 압력으로 작용합니다."
        elif "승인" in text or "approval" in text or "수주" in text or "계약" in text:
            explanation = f"호재 — {title_clean}. 신규 수주/승인은 매출 성장 가시성을 높여줍니다."
        elif "상향" in text or "upgrade" in text or "목표가" in text:
            explanation = f"호재 — {title_clean}. 애널리스트 투자의견 상향은 시장 기대치를 높입니다."
        else:
            explanation = f"호재 — {title_clean}. 주가에 긍정적 영향이 예상됩니다."
    elif direction == "negative":
        if "실적" in text or "부진" in text or "miss" in text:
            explanation = f"악재 — {title_clean}. 실적 부진은 밸류에이션 하향 조정의 직접적 원인입니다."
        elif "규제" in text or "소송" in text or "probe" in text:
            explanation = f"악재 — {title_clean}. 규제/법적 리스크는 불확실성을 키워 주가를 압박합니다."
        elif "하향" in text or "downgrade" in text:
            explanation = f"악재 — {title_clean}. 투자의견 하향은 매도 압력을 높입니다."
        else:
            explanation = f"악재 — {title_clean}. 주가에 부정적 영향이 우려됩니다."
    else:
        explanation = f"중립 — {title_clean}. 방향성 판단이 필요하며, 후속 뉴스를 주시해야 합니다."

    return label, explanation


def _extract_live_impact_news(ticker: str, info: dict | None = None, sector_id: str | None = None) -> list[dict]:
    cache_key = f"live-impact-news:{_ticker_key(ticker)}"
    cached = _get_cached_ttl(cache_key, 900)
    if cached is not None:
        return cached

    company_name = str((info or {}).get("shortName") or (info or {}).get("longName") or ticker).strip()
    candidates = []
    seen_titles = set()
    for query in _build_stock_news_queries(ticker, info=info, sector_id=sector_id):
        try:
            for article in NewsCrawlerService.search_news(query)[:6]:
                title = getattr(article, "title", "") or ""
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                score = _score_live_article_impact(title, ticker, company_name, sector_id)
                if score < 6:
                    continue
                issue_label, explanation = _explain_live_article_impact(title, ticker, sector_id)
                # Determine sentiment direction
                title_lower = title.lower()
                pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in title_lower)
                neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title_lower)
                impact_direction = "positive" if pos_count > neg_count else "negative" if neg_count > pos_count else "neutral"
                candidates.append({
                    "title": title,
                    "source": getattr(article, "source", None),
                    "published_at": getattr(article, "published_at", None),
                    "url": getattr(article, "url", None),
                    "impact_score": score,
                    "impact_direction": impact_direction,
                    "issue_label": issue_label,
                    "explanation": explanation,
                })
        except Exception:
            pass

    candidates.sort(key=lambda item: item["impact_score"], reverse=True)
    top = candidates[:5]  # Take top 5 most impactful articles
    _set_cached(cache_key, top)
    return top


def _derive_earnings_fallbacks(stock: yf.Ticker) -> dict:
    fallback = {
        "revenue_growth": None,
        "profit_margin": None,
        "operating_margin": None,
        "roe": None,
    }
    try:
        qf = stock.quarterly_financials
        if qf is None or qf.empty:
            return fallback
        cols = list(qf.columns)
        if len(cols) >= 2 and "Total Revenue" in qf.index:
            cur_rev = qf.loc["Total Revenue", cols[0]]
            prev_rev = qf.loc["Total Revenue", cols[1]]
            if not pd.isna(cur_rev) and not pd.isna(prev_rev) and float(prev_rev) != 0:
                fallback["revenue_growth"] = (float(cur_rev) - float(prev_rev)) / abs(float(prev_rev))
        if "Total Revenue" in qf.index:
            cur_rev = qf.loc["Total Revenue", cols[0]]
            if not pd.isna(cur_rev) and float(cur_rev) != 0:
                if "Net Income" in qf.index and not pd.isna(qf.loc["Net Income", cols[0]]):
                    fallback["profit_margin"] = float(qf.loc["Net Income", cols[0]]) / float(cur_rev)
                if "Operating Income" in qf.index and not pd.isna(qf.loc["Operating Income", cols[0]]):
                    fallback["operating_margin"] = float(qf.loc["Operating Income", cols[0]]) / float(cur_rev)
    except Exception:
        pass

    try:
        bs = stock.balance_sheet
        fin = stock.financials
        if bs is not None and fin is not None and not bs.empty and not fin.empty:
            eq_row = next((row for row in ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"] if row in bs.index), None)
            ni_row = "Net Income" if "Net Income" in fin.index else None
            if eq_row and ni_row:
                eq = bs.loc[eq_row].dropna()
                ni = fin.loc[ni_row].dropna()
                common = [c for c in ni.index if c in eq.index]
                if common:
                    equity = float(eq[common[0]])
                    income = float(ni[common[0]])
                    if equity != 0:
                        fallback["roe"] = income / equity
    except Exception:
        pass
    return fallback


def _format_expected_condition(item: dict, source: dict) -> str:
    thresholds = item.get("thresholds", {})
    current = thresholds.get("current")
    safe_line = thresholds.get("safe_line")
    positive_if = source.get("positive_if", "above")

    if source["type"] == "earnings_metric":
        threshold = source.get("threshold", 0)
        if source.get("metric", "").endswith(("growth", "margin", "yield")) or source.get("metric") == "roe":
            target = round(threshold * 100, 1)
            if positive_if == "above":
                return f"최소 {target}% 이상 유지되어야 주가를 방어할 가능성이 높습니다."
            return f"최대 {target}% 이하로 관리되어야 부담이 줄어듭니다."
        if positive_if == "below":
            return f"{threshold} 이하로 내려와야 부담이 완화됩니다."
        return f"{threshold} 이상이 유지되어야 긍정적입니다."

    if current is not None and safe_line is not None:
        if positive_if == "up":
            return f"최소 {safe_line} 이상은 유지되어야 기대감이 꺾이지 않습니다."
        if positive_if == "down":
            return f"최소 {safe_line} 이하로 내려와야 비용/경쟁 부담이 완화됩니다."
        return f"{safe_line} 부근에서 안정돼야 변동성 부담이 줄어듭니다."

    return "현재 추세가 유지되는지 확인이 필요합니다."


def _infer_item_metadata(source: dict) -> dict:
    item = source.get("item", "")
    metric = source.get("metric", "")
    symbol = source.get("symbol", "")

    thesis = source.get("thesis", "")
    window = source.get("window", "")
    weight = int(source.get("weight", 0) or 0)

    if not thesis:
        if "매출 성장" in item or metric == "revenue_growth":
            thesis = "외형 성장 둔화는 기대감 훼손으로 바로 이어질 수 있어 주가 선반영 여부를 판단하는 핵심 지표입니다."
        elif "이익률" in item or "margin" in metric:
            thesis = "이익률은 기대가 실적으로 전환되는지 보여주는 가장 직접적인 검증 포인트입니다."
        elif metric == "roe":
            thesis = "ROE는 자본 효율이 유지되는지 보여주며, 프리미엄 밸류를 정당화하는 핵심 지표입니다."
        elif "환율" in item:
            thesis = "환율 변화는 수출 경쟁력과 원화 환산 실적 기대를 빠르게 흔드는 선행 변수입니다."
        elif "경쟁사" in item:
            thesis = "경쟁사 상대강도는 산업 내 점유율 기대와 멀티플 프리미엄 변화를 먼저 보여줍니다."
        elif any(keyword in item for keyword in ["우라늄", "리튬", "구리", "백금", "천연가스"]):
            thesis = "원자재 추세는 업황 기대와 원가 압박을 동시에 반영하는 선행 체크포인트입니다."
        elif symbol:
            thesis = f"{symbol} 흐름은 해당 종목의 업황 기대와 위험 선호가 살아있는지 확인하는 프록시입니다."
        else:
            thesis = "이 항목은 주가를 선행해서 움직일 수 있는 핵심 체크포인트입니다."

    if not window:
        if source.get("type") == "earnings_metric":
            window = "향후 1~2분기"
        elif "환율" in item or any(keyword in item for keyword in ["구리", "리튬", "우라늄", "천연가스", "백금"]):
            window = "향후 1~2개월"
        else:
            window = "향후 1~3개월"

    if weight <= 0:
        if metric in {"revenue_growth", "profit_margin", "operating_margin"}:
            weight = 80
        elif metric in {"roe", "forward_pe", "price_to_book"}:
            weight = 65
        elif "경쟁사" in item:
            weight = 68
        elif "환율" in item:
            weight = 52
        elif any(keyword in item for keyword in ["구리", "리튬", "우라늄", "천연가스", "백금"]):
            weight = 48
        else:
            weight = 60

    return {
        "thesis": thesis,
        "window": window,
        "weight": weight,
    }


def _build_checklist_summary(results: list[dict]) -> dict:
    scored_items = [item for item in results if item.get("status") in {"positive", "negative", "neutral"}]
    if not scored_items:
        return {"score": 50, "positives": 0, "negatives": 0, "neutrals": 0, "momentum_notes": []}

    weighted_total = 0.0
    weighted_score = 0.0
    for item in scored_items:
        weight = max(20, float(item.get("importance", 40)))
        signal = 1.0 if item["status"] == "positive" else (-1.0 if item["status"] == "negative" else 0.0)
        weighted_total += weight
        weighted_score += signal * weight

    summary_score = round(max(0, min(100, 50 + (weighted_score / weighted_total) * 50))) if weighted_total else 50
    positives = sum(1 for item in scored_items if item["status"] == "positive")
    negatives = sum(1 for item in scored_items if item["status"] == "negative")
    neutrals = sum(1 for item in scored_items if item["status"] == "neutral")

    ranked = sorted(scored_items, key=lambda item: item.get("importance", 0), reverse=True)
    momentum_notes = []
    for item in ranked[:5]:
        lead = "긍정 선행" if item["status"] == "positive" else ("부정 선행" if item["status"] == "negative" else "중립")
        momentum_notes.append({
            "title": item["name"],
            "lead": lead,
            "detail": item.get("detail", ""),
            "why_it_matters": item.get("why_it_matters", ""),
            "expected_condition": item.get("expected_condition", ""),
            "window": item.get("window", "향후 1~3개월"),
            "status": item["status"],
            "importance": item.get("importance", 0),
        })

    leading_risks = [note for note in momentum_notes if note["status"] == "negative"][:3]
    leading_supports = [note for note in momentum_notes if note["status"] == "positive"][:3]

    return {
        "score": summary_score,
        "positives": positives,
        "negatives": negatives,
        "neutrals": neutrals,
        "momentum_notes": momentum_notes,
        "leading_risks": leading_risks,
        "leading_supports": leading_supports,
    }


SECTOR_NAME_MAP: dict[str, str] = {
    "ai-semi": "AI / 반도체",
    "robotics": "로봇 / 자동화",
    "smr-nuclear": "SMR / 원자력",
    "cybersec": "사이버보안",
    "space": "우주항공",
    "biotech": "생명공학",
    "quantum": "양자컴퓨팅",
    "hydrogen": "수소 / 에너지",
}


TOP_PICK_SECTOR_MAP: dict[str, str] = {
    "NVDA": "ai-semi",
    "TSM": "ai-semi",
    "AVGO": "ai-semi",
    "000660.KS": "ai-semi",
    "005930.KS": "ai-semi",
    "TSLA": "robotics",
    "ISRG": "robotics",
    "454910.KS": "robotics",
    "FANUY": "robotics",
    "267250.KS": "robotics",
    "CEG": "smr-nuclear",
    "CCJ": "smr-nuclear",
    "BWXT": "smr-nuclear",
    "034020.KS": "smr-nuclear",
    "015760.KS": "smr-nuclear",
    "CRWD": "cybersec",
    "PANW": "cybersec",
    "FTNT": "cybersec",
    "ZS": "cybersec",
    "S": "cybersec",
    "RKLB": "space",
    "LMT": "space",
    "LHX": "space",
    "047810.KS": "space",
    "BA": "space",
    "CRSP": "biotech",
    "LLY": "biotech",
    "ILMN": "biotech",
    "207940.KS": "biotech",
    "068270.KS": "biotech",
    "IONQ": "quantum",
    "GOOG": "quantum",
    "IBM": "quantum",
    "RGTI": "quantum",
    "MSFT": "quantum",
    "BE": "hydrogen",
    "PLUG": "hydrogen",
    "ENPH": "hydrogen",
    "005380.KS": "hydrogen",
    "336260.KS": "hydrogen",
}


SECTOR_DISCOVERY_UNIVERSE: dict[str, list[dict[str, str]]] = {
    "ai-semi": [
        {"symbol": "SOXX", "label": "반도체 ETF", "why": "반도체 업황 전체 기대를 가장 빠르게 반영합니다."},
        {"symbol": "SMH", "label": "반도체 ETF 2", "why": "대형 반도체 밸류체인 강도를 같이 확인합니다."},
        {"symbol": "NVDA", "label": "엔비디아", "why": "AI CAPEX 기대의 핵심 축입니다."},
        {"symbol": "MU", "label": "마이크론", "why": "메모리 업황과 ASP 기대를 선행 반영합니다."},
        {"symbol": "AMD", "label": "AMD", "why": "AI 반도체 경쟁 구도를 보여줍니다."},
        {"symbol": "TSM", "label": "TSMC", "why": "파운드리 가동과 첨단 공정 수요를 보여줍니다."},
        {"symbol": "QQQ", "label": "빅테크 ETF", "why": "대형 성장주 위험선호가 반도체 밸류를 밀어줍니다."},
        {"symbol": "HG=F", "label": "구리", "why": "IT/산업 수요 기대를 보조적으로 반영합니다."},
        {"symbol": "KRW=X", "label": "USD/KRW", "why": "한국 수출 반도체주의 원화 실적 기대에 직접적입니다."},
    ],
    "robotics": [
        {"symbol": "ROBO", "label": "로봇 ETF", "why": "로봇 자동화 섹터 전체 위험선호를 보여줍니다."},
        {"symbol": "BOTZ", "label": "로봇 ETF 2", "why": "글로벌 로봇 밸류체인 흐름을 보완합니다."},
        {"symbol": "TSLA", "label": "테슬라", "why": "휴머노이드와 자율주행 기대의 핵심 심볼입니다."},
        {"symbol": "ISRG", "label": "인튜이티브 서지컬", "why": "고부가 로봇 상용화 수요를 보여줍니다."},
        {"symbol": "HG=F", "label": "구리", "why": "산업용 자동화 설비 수요의 보조 지표입니다."},
        {"symbol": "LIT", "label": "리튬 ETF", "why": "배터리/전장 부품 원가 부담을 점검합니다."},
        {"symbol": "XLI", "label": "산업재 ETF", "why": "제조업 CAPEX 사이클과 함께 움직입니다."},
    ],
    "smr-nuclear": [
        {"symbol": "URA", "label": "우라늄 ETF", "why": "우라늄 가격과 섹터 심리를 가장 직접적으로 보여줍니다."},
        {"symbol": "CCJ", "label": "카메코", "why": "우라늄 공급 부족 기대를 선행 반영합니다."},
        {"symbol": "XLU", "label": "유틸리티 ETF", "why": "전력 수요와 안정적 현금흐름 프리미엄을 같이 봅니다."},
        {"symbol": "NG=F", "label": "천연가스", "why": "대체 에너지원 가격과 전력 믹스 변화를 봅니다."},
        {"symbol": "TLT", "label": "장기채", "why": "장기 성장/인프라 밸류의 할인율에 영향을 줍니다."},
    ],
    "cybersec": [
        {"symbol": "BUG", "label": "보안 ETF", "why": "섹터 멀티플과 성장주 심리를 보여줍니다."},
        {"symbol": "CIBR", "label": "보안 ETF 2", "why": "사이버보안 업종 수급을 보조 확인합니다."},
        {"symbol": "CRWD", "label": "크라우드스트라이크", "why": "고성장 보안주의 선행 심리입니다."},
        {"symbol": "PANW", "label": "팔로알토", "why": "대형 플랫폼 보안 수요를 보여줍니다."},
        {"symbol": "QQQ", "label": "빅테크 ETF", "why": "소프트웨어 성장주 밸류에 직접 연결됩니다."},
    ],
    "space": [
        {"symbol": "ITA", "label": "방산 ETF", "why": "정부 예산과 방산 수요를 반영합니다."},
        {"symbol": "UFO", "label": "우주 ETF", "why": "우주항공 테마 심리를 가장 빠르게 보여줍니다."},
        {"symbol": "RKLB", "label": "로켓랩", "why": "민간 우주 일정 기대를 선행 반영합니다."},
        {"symbol": "BA", "label": "보잉", "why": "항공우주 공급망 정상화 기대를 점검합니다."},
        {"symbol": "XAR", "label": "항공우주 ETF", "why": "방산·항공우주 전반 수급을 봅니다."},
    ],
    "biotech": [
        {"symbol": "XBI", "label": "바이오 ETF", "why": "임상/승인 기대가 가장 빠르게 반영됩니다."},
        {"symbol": "IBB", "label": "대형 바이오 ETF", "why": "대형 제약·바이오 멀티플 흐름을 봅니다."},
        {"symbol": "LLY", "label": "일라이 릴리", "why": "비만/혁신 신약 기대를 반영하는 대표주입니다."},
        {"symbol": "MRNA", "label": "모더나", "why": "바이오 위험선호와 파이프라인 기대를 보조 확인합니다."},
        {"symbol": "XLV", "label": "헬스케어 ETF", "why": "방어주 성격과 자금 유입을 같이 봅니다."},
    ],
    "quantum": [
        {"symbol": "QTUM", "label": "양자 ETF", "why": "양자 테마 심리의 가장 직접적인 프록시입니다."},
        {"symbol": "IONQ", "label": "아이온큐", "why": "순수 양자 기대의 방향성을 보여줍니다."},
        {"symbol": "IBM", "label": "IBM", "why": "기업용 양자 상용화 기대를 확인합니다."},
        {"symbol": "GOOG", "label": "알파벳", "why": "대형 플랫폼의 양자 옵션 가치를 반영합니다."},
        {"symbol": "QQQ", "label": "빅테크 ETF", "why": "초장기 성장 옵션 선호도를 확인합니다."},
    ],
    "hydrogen": [
        {"symbol": "ICLN", "label": "클린에너지 ETF", "why": "정책·금리·위험선호가 같이 반영됩니다."},
        {"symbol": "TAN", "label": "태양광 ETF", "why": "청정에너지 설치 경기와 함께 움직입니다."},
        {"symbol": "PL=F", "label": "백금", "why": "수소 밸류체인 원가와 기대를 보조 확인합니다."},
        {"symbol": "BE", "label": "블룸에너지", "why": "데이터센터 전력 대체 수요를 선행 반영합니다."},
        {"symbol": "ENPH", "label": "엔페이즈", "why": "분산형 전력 설비 수요를 보여줍니다."},
    ],
}


def _ticker_key(ticker: str) -> str:
    normalized = (ticker or "").upper().strip()
    if normalized.endswith(".KS") or normalized.endswith(".KQ"):
        return normalized
    return normalized


def _infer_sector_id_from_profile(ticker: str, info: dict | None = None, quote: dict | None = None) -> str | None:
    normalized = _ticker_key(ticker)
    if normalized in TOP_PICK_SECTOR_MAP:
        return TOP_PICK_SECTOR_MAP[normalized]
    if normalized.replace(".KS", "").replace(".KQ", "") in TOP_PICK_SECTOR_MAP:
        return TOP_PICK_SECTOR_MAP[normalized.replace(".KS", "").replace(".KQ", "")]

    payload = info or quote or {}
    text_parts = [
        str(payload.get("sectorDisp") or payload.get("sector") or ""),
        str(payload.get("industryDisp") or payload.get("industry") or ""),
        str(payload.get("quoteType") or payload.get("typeDisp") or ""),
        str(payload.get("longBusinessSummary") or ""),
        str(payload.get("shortName") or payload.get("shortname") or ""),
        str(payload.get("longName") or payload.get("longname") or ""),
    ]
    text = " ".join(text_parts).lower()

    if any(keyword in text for keyword in ["semiconductor", "chip", "foundry", "memory", "gpu", "electronics"]):
        return "ai-semi"
    if any(keyword in text for keyword in ["robot", "automation", "auto manufacturer", "machinery", "industrial"]):
        return "robotics"
    if any(keyword in text for keyword in ["uranium", "nuclear", "utility", "power generation"]):
        return "smr-nuclear"
    if any(keyword in text for keyword in ["cyber", "security", "cloud software", "software - infrastructure"]):
        return "cybersec"
    if any(keyword in text for keyword in ["aerospace", "defense", "space", "satellite", "aircraft"]):
        return "space"
    if any(keyword in text for keyword in ["biotech", "drug", "pharma", "healthcare", "genomics", "life sciences"]):
        return "biotech"
    if any(keyword in text for keyword in ["quantum", "superconduct", "cloud computing"]):
        return "quantum"
    if any(keyword in text for keyword in ["hydrogen", "fuel cell", "solar", "clean energy", "renewable", "electric vehicle"]):
        return "hydrogen"
    # Default to ai-semi for stocks that don't match any sector keywords
    # This ensures every stock gets a valid sector_id for frontend routing
    return "ai-semi"


def _build_dynamic_checklist_sources(ticker: str, info: dict | None = None) -> list[dict]:
    """Build intelligent, stock-specific checklist sources based on industry analysis.

    For any stock not in the pre-built CHECKLIST_SOURCES, this analyzes the company's
    industry, business type, financial profile, and competitive landscape to generate
    a tailored checklist similar in quality to hand-crafted ones.
    """
    sector_id = _infer_sector_id_from_profile(ticker, info=info)
    info = info or {}
    industry = str(info.get("industry") or "").lower()
    yf_sector = str(info.get("sector") or "").lower()
    name = str(info.get("shortName") or info.get("longName") or ticker)
    market_cap = info.get("marketCap") or 0
    profit_margin = info.get("profitMargins")
    revenue_growth = info.get("revenueGrowth")
    is_profitable = profit_margin is not None and profit_margin > 0
    is_high_growth = revenue_growth is not None and revenue_growth > 0.15
    is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")

    dynamic_sources: list[dict] = []

    # ── 1. Core financial metrics (always include, but adjust thresholds by type) ──
    margin_threshold = 0.15 if is_profitable else 0.0
    margin_thesis = (
        f"{name}의 수익성이 유지되는지가 밸류에이션 프리미엄의 핵심입니다."
        if is_profitable else
        f"{name}은 아직 적자 상태로, 흑자전환 시점이 주가 방향을 결정합니다."
    )
    dynamic_sources.append(
        ck("영업이익률 추이", "earnings_metric", metric="profit_margin",
           positive_if="above", threshold=margin_threshold, weight=90,
           thesis=margin_thesis, window="향후 1~2분기")
    )
    dynamic_sources.append(
        ck("매출 성장률", "earnings_metric", metric="revenue_growth",
           positive_if="above", threshold=0.05 if not is_high_growth else 0.15, weight=85,
           thesis=f"{'고성장주인 ' if is_high_growth else ''}{name}의 매출 성장 둔화는 주가 조정의 가장 직접적인 트리거입니다.",
           window="향후 1~2분기")
    )

    # ── 2. Industry-specific peers & ETFs ──
    INDUSTRY_PEERS: dict[str, list[dict]] = {
        # Tech / Software
        "software": [
            {"symbol": "IGV", "label": "소프트웨어 ETF", "why": "소프트웨어 업종 전체 밸류에이션 흐름을 반영합니다."},
            {"symbol": "QQQ", "label": "빅테크 ETF", "why": "기술주 위험선호 변화가 직접적으로 영향을 줍니다."},
        ],
        "internet": [
            {"symbol": "KWEB", "label": "중국 인터넷 ETF", "why": "글로벌 인터넷 경쟁 구도와 위험선호를 보여줍니다."},
            {"symbol": "QQQ", "label": "빅테크 ETF", "why": "대형 플랫폼주 위험선호가 밸류에이션을 움직입니다."},
        ],
        "semiconductor": [
            {"symbol": "SOXX", "label": "반도체 ETF", "why": "반도체 업황 전체 기대를 가장 빠르게 반영합니다."},
            {"symbol": "SMH", "label": "반도체 ETF 2", "why": "대형 반도체 밸류체인 강도를 같이 확인합니다."},
        ],
        # Healthcare / Biotech
        "biotech": [
            {"symbol": "XBI", "label": "바이오텍 ETF", "why": "바이오 섹터 전체 위험선호와 자금 흐름을 반영합니다."},
            {"symbol": "IBB", "label": "바이오 대형주 ETF", "why": "대형 바이오 밸류 흐름을 보여줍니다."},
        ],
        "pharma": [
            {"symbol": "XLV", "label": "헬스케어 ETF", "why": "헬스케어 전체 자금 흐름과 방어주 선호를 반영합니다."},
            {"symbol": "XBI", "label": "바이오텍 ETF", "why": "혁신 의약 기대감 변화를 보여줍니다."},
        ],
        "drug": [
            {"symbol": "XLV", "label": "헬스케어 ETF", "why": "제약 섹터 전체 흐름과 방어적 포지셔닝을 반영합니다."},
        ],
        # Financial
        "bank": [
            {"symbol": "XLF", "label": "금융 ETF", "why": "금융 섹터 전체 건전성과 자금 흐름을 반영합니다."},
            {"symbol": "TLT", "label": "장기채 ETF", "why": "금리 방향이 은행 NIM(순이자마진)에 직결됩니다."},
        ],
        "insurance": [
            {"symbol": "XLF", "label": "금융 ETF", "why": "금융 섹터 심리와 금리 환경이 보험사 수익에 영향을 줍니다."},
        ],
        "financial": [
            {"symbol": "XLF", "label": "금융 ETF", "why": "금융 섹터 전체 흐름을 보여줍니다."},
        ],
        # Consumer
        "retail": [
            {"symbol": "XRT", "label": "소매 ETF", "why": "소매 업종 전체 소비 심리와 마진 트렌드를 반영합니다."},
            {"symbol": "XLY", "label": "경기소비재 ETF", "why": "소비 경기 사이클을 보여줍니다."},
        ],
        "consumer": [
            {"symbol": "XLY", "label": "경기소비재 ETF", "why": "소비 지출 트렌드와 경기 심리를 반영합니다."},
        ],
        "food": [
            {"symbol": "XLP", "label": "필수소비재 ETF", "why": "방어적 소비재 자금 흐름을 보여줍니다."},
        ],
        # Energy
        "oil": [
            {"symbol": "CL=F", "label": "WTI 원유", "why": "원유 가격이 에너지 기업 매출과 이익에 직접적으로 영향합니다."},
            {"symbol": "XLE", "label": "에너지 ETF", "why": "에너지 섹터 전체 흐름을 보여줍니다."},
        ],
        "energy": [
            {"symbol": "XLE", "label": "에너지 ETF", "why": "에너지 섹터 위험선호와 유가 연동을 반영합니다."},
            {"symbol": "CL=F", "label": "WTI 원유", "why": "원유 가격 추세가 에너지 기업 실적에 직결됩니다."},
        ],
        "utility": [
            {"symbol": "XLU", "label": "유틸리티 ETF", "why": "전력/유틸리티 업종 자금 흐름과 금리 민감도를 반영합니다."},
        ],
        # Industrial / Materials
        "auto": [
            {"symbol": "CARZ", "label": "자동차 ETF", "why": "글로벌 자동차 수요와 EV 트렌드를 반영합니다."},
            {"symbol": "HG=F", "label": "구리", "why": "산업 수요 기대치의 보조 지표입니다."},
        ],
        "steel": [
            {"symbol": "SLX", "label": "철강 ETF", "why": "글로벌 철강 수급과 산업 심리를 반영합니다."},
            {"symbol": "HG=F", "label": "구리", "why": "산업 금속 수요 트렌드를 보여줍니다."},
        ],
        "chemical": [
            {"symbol": "XLB", "label": "소재 ETF", "why": "소재 섹터 전체 사이클을 반영합니다."},
        ],
        "construction": [
            {"symbol": "XHB", "label": "주택건설 ETF", "why": "건설/주택 경기를 반영합니다."},
        ],
        # Aerospace / Defense
        "aerospace": [
            {"symbol": "ITA", "label": "방산 ETF", "why": "방산/항공 섹터 전체 흐름을 반영합니다."},
        ],
        "defense": [
            {"symbol": "ITA", "label": "방산 ETF", "why": "방산 예산과 수주 기대를 반영합니다."},
        ],
        # Telecom / Media
        "telecom": [
            {"symbol": "XLC", "label": "통신서비스 ETF", "why": "통신/미디어 섹터 자금 흐름을 반영합니다."},
        ],
        "entertainment": [
            {"symbol": "XLC", "label": "통신서비스 ETF", "why": "미디어/엔터 섹터 전체 심리를 반영합니다."},
        ],
        # Real Estate
        "reit": [
            {"symbol": "VNQ", "label": "리츠 ETF", "why": "부동산/리츠 전체 자금 흐름과 금리 민감도를 반영합니다."},
            {"symbol": "TLT", "label": "장기채 ETF", "why": "금리 방향이 리츠 밸류에이션에 직결됩니다."},
        ],
        "real estate": [
            {"symbol": "VNQ", "label": "리츠 ETF", "why": "부동산 전체 흐름을 보여줍니다."},
        ],
    }

    # Match industry keywords to peer lists
    matched_peers: list[dict] = []
    for keyword, peers in INDUSTRY_PEERS.items():
        if keyword in industry or keyword in yf_sector:
            matched_peers.extend(peers)
            break

    # Fallback: use yfinance sector to pick a broad ETF
    if not matched_peers:
        SECTOR_ETF_MAP = {
            "technology": [{"symbol": "XLK", "label": "기술 ETF", "why": "기술 섹터 전체 밸류에이션 흐름을 반영합니다."}],
            "healthcare": [{"symbol": "XLV", "label": "헬스케어 ETF", "why": "헬스케어 섹터 전체 자금 흐름을 반영합니다."}],
            "financial": [{"symbol": "XLF", "label": "금융 ETF", "why": "금융 섹터 심리를 반영합니다."}],
            "consumer cyclical": [{"symbol": "XLY", "label": "경기소비재 ETF", "why": "소비 경기를 반영합니다."}],
            "consumer defensive": [{"symbol": "XLP", "label": "필수소비재 ETF", "why": "방어적 소비 흐름을 반영합니다."}],
            "industrials": [{"symbol": "XLI", "label": "산업재 ETF", "why": "산업/제조 경기를 반영합니다."}],
            "basic materials": [{"symbol": "XLB", "label": "소재 ETF", "why": "소재 사이클을 반영합니다."}],
            "communication": [{"symbol": "XLC", "label": "통신서비스 ETF", "why": "통신/미디어 심리를 반영합니다."}],
            "energy": [{"symbol": "XLE", "label": "에너지 ETF", "why": "에너지 섹터 흐름을 반영합니다."}],
            "utilities": [{"symbol": "XLU", "label": "유틸리티 ETF", "why": "유틸리티 자금 흐름을 반영합니다."}],
            "real estate": [{"symbol": "VNQ", "label": "리츠 ETF", "why": "부동산 흐름을 반영합니다."}],
        }
        for sec_key, etfs in SECTOR_ETF_MAP.items():
            if sec_key in yf_sector:
                matched_peers.extend(etfs)
                break

    # Add matched sector/industry peers
    seen_symbols = {_ticker_key(ticker)}
    for peer in matched_peers[:3]:
        sym = peer["symbol"]
        if sym in seen_symbols:
            continue
        seen_symbols.add(sym)
        dynamic_sources.append(
            ck(peer["label"], "commodity", symbol=sym, positive_if="up",
               weight=75, thesis=peer["why"], window="향후 1~3개월")
        )

    # ── 3. Macro/currency sensitivity ──
    if is_krx:
        dynamic_sources.append(
            ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up",
               weight=65, thesis=f"원화 약세는 {name}의 수출 실적에 유리하고, 원화 강세는 외국인 자금 유입에 긍정적입니다.",
               window="향후 1~3개월")
        )
        dynamic_sources.append(
            ck("KOSPI 흐름", "commodity", symbol="^KS11", positive_if="up",
               weight=55, thesis="한국 시장 전체 심리가 개별 종목 수급에 영향을 줍니다.",
               window="향후 1~2개월")
        )
    else:
        # US stocks: add VIX as risk gauge
        dynamic_sources.append(
            ck("시장 공포지수 (VIX)", "commodity", symbol="^VIX", positive_if="down",
               weight=50, thesis="VIX 급등은 시장 전체 매도 압력을 높여 개별 종목에도 영향을 줍니다.",
               window="향후 1~2개월")
        )

    # ── 4. Business-type specific metrics ──
    if is_high_growth and not is_profitable:
        # Pre-profit growth stock
        dynamic_sources.append(
            ck("현금 소진율 점검", "earnings_metric", metric="roe",
               positive_if="above", threshold=-0.3, weight=78,
               thesis=f"{name}은 성장 단계 기업으로, 자금 소진 속도가 주가 방어의 핵심입니다.",
               window="향후 2~4분기")
        )
    elif is_profitable:
        # Profitable company
        dynamic_sources.append(
            ck("자본 효율성 (ROE)", "earnings_metric", metric="roe",
               positive_if="above", threshold=0.12, weight=65,
               thesis=f"{name}의 자본 효율이 유지되어야 현재 밸류에이션 프리미엄이 정당화됩니다.",
               window="향후 2~4분기")
        )

    # Add valuation check for large caps
    if market_cap > 10_000_000_000:  # >$10B
        dynamic_sources.append(
            ck("밸류 부담 점검 (P/B)", "earnings_metric", metric="price_to_book",
               positive_if="below", threshold=30.0, weight=45,
               thesis="밸류에이션이 과도하면 좋은 실적에서도 주가 조정 폭이 커질 수 있습니다.",
               window="향후 1~2개월")
        )

    # ── 5. Industry-relevant commodities ──
    INDUSTRY_COMMODITIES = {
        "semiconductor": [("HG=F", "구리 가격", "up", "반도체 수요와 IT 인프라 확장의 보조 지표입니다.")],
        "auto": [("CL=F", "원유 가격", "down", "유가 상승은 자동차 수요를 둔화시킬 수 있습니다."), ("LIT", "리튬 ETF", "up", "EV 배터리 원자재 가격이 마진에 영향을 줍니다.")],
        "steel": [("HG=F", "구리 가격", "up", "산업 금속 수요의 전반적 트렌드를 반영합니다.")],
        "mining": [("GC=F", "금 가격", "up", "금/귀금속 가격 추세가 광업 수익에 직결됩니다.")],
        "airline": [("CL=F", "원유 가격", "down", "유가 하락은 항공사 연료비 절감으로 이어집니다.")],
        "shipping": [("CL=F", "원유 가격", "down", "연료비가 해운사 수익의 핵심 변수입니다.")],
        "food": [("DBA", "농산물 ETF", "down", "원자재 가격이 식품 기업의 원가에 영향을 줍니다.")],
        "chemical": [("CL=F", "원유 가격", "down", "나프타 가격이 화학 기업 원가에 직결됩니다.")],
        "construction": [("WOOD", "목재 ETF", "down", "건설 자재 가격이 마진에 영향을 줍니다.")],
        "battery": [("LIT", "리튬 ETF", "up", "리튬 가격이 배터리 산업 전체 수급을 반영합니다.")],
        "electric vehicle": [("LIT", "리튬 ETF", "up", "배터리 원자재 가격과 EV 수요를 반영합니다.")],
        "gold": [("GC=F", "금 선물", "up", "금 가격이 관련 기업 수익에 직접적으로 영향합니다.")],
        "oil": [("CL=F", "WTI 원유", "up", "원유 가격이 매출과 이익에 직결됩니다."), ("NG=F", "천연가스", "up", "가스 가격도 에너지 기업 수익에 영향을 줍니다.")],
        "natural gas": [("NG=F", "천연가스", "up", "가스 가격이 직접적인 수익 드라이버입니다.")],
        "solar": [("TAN", "태양광 ETF", "up", "태양광 업종 전체 심리를 반영합니다.")],
        "uranium": [("URA", "우라늄 ETF", "up", "우라늄 가격 추세가 원전 관련주에 직접적입니다.")],
        "nuclear": [("URA", "우라늄 ETF", "up", "우라늄 수급이 원전 산업 전체에 영향을 줍니다.")],
    }

    for ind_key, commodities in INDUSTRY_COMMODITIES.items():
        if ind_key in industry:
            for sym, label, pos_if, thesis in commodities:
                if sym not in seen_symbols:
                    seen_symbols.add(sym)
                    dynamic_sources.append(
                        ck(label, "commodity", symbol=sym, positive_if=pos_if,
                           weight=68, thesis=thesis, window="향후 1~3개월")
                    )
            break

    # ── 6. Fallback: add sector discovery universe items if nothing matched ──
    if len(dynamic_sources) < 5:
        for candidate in SECTOR_DISCOVERY_UNIVERSE.get(sector_id or "", [])[:3]:
            symbol = candidate["symbol"]
            if symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)
            positive_if = "down" if any(kw in candidate["label"] for kw in ["백금", "천연가스"]) else "up"
            dynamic_sources.append(
                ck(candidate["label"], "commodity", symbol=symbol, positive_if=positive_if,
                   weight=68, thesis=candidate["why"], window="향후 1~3개월")
            )

    return dynamic_sources


def _compute_return_correlation(base_hist: pd.DataFrame, compare_hist: pd.DataFrame) -> tuple[float, float, float]:
    if base_hist.empty or compare_hist.empty:
        return 0.0, 0.0, 0.0
    try:
        merged = pd.DataFrame({
            "stock": base_hist["Close"],
            "signal": compare_hist["Close"],
        }).dropna()
        if len(merged) < 40:
            return 0.0, 0.0, 0.0
        stock_ret = merged["stock"].pct_change()
        signal_ret = merged["signal"].pct_change()
        aligned = pd.DataFrame({"stock": stock_ret, "signal": signal_ret}).dropna()
        if len(aligned) < 30:
            return 0.0, 0.0, 0.0
        same_day = float(aligned["stock"].corr(aligned["signal"]) or 0.0)
        future_5 = aligned["stock"].shift(-5)
        future_10 = aligned["stock"].shift(-10)
        lead_5 = float(pd.DataFrame({"future": future_5, "signal": aligned["signal"]}).dropna()["future"].corr(pd.DataFrame({"future": future_5, "signal": aligned["signal"]}).dropna()["signal"]) or 0.0)
        lead_10 = float(pd.DataFrame({"future": future_10, "signal": aligned["signal"]}).dropna()["future"].corr(pd.DataFrame({"future": future_10, "signal": aligned["signal"]}).dropna()["signal"]) or 0.0)
        return round(same_day, 3), round(lead_5, 3), round(lead_10, 3)
    except Exception:
        return 0.0, 0.0, 0.0


def _describe_signal_state(hist: pd.DataFrame, positive_if: str) -> tuple[str, str]:
    if hist.empty or len(hist) < 25:
        return "데이터 부족", "중립"
    closes = hist["Close"].dropna().astype(float).values
    if len(closes) < 25:
        return "데이터 부족", "중립"
    ma5 = float(np.mean(closes[-5:]))
    ma20 = float(np.mean(closes[-20:]))
    recent = (ma5 - ma20) / ma20 * 100 if ma20 else 0.0
    if positive_if == "down":
        if recent <= -1.5:
            return f"최근 비용/경쟁 지표 하락세 ({recent:.1f}%)", "긍정"
        if recent >= 1.5:
            return f"최근 비용/경쟁 지표 상승세 ({recent:.1f}%)", "부정"
        return "최근 횡보", "중립"
    if recent >= 1.5:
        return f"최근 선행 지표 상승세 ({recent:.1f}%)", "긍정"
    if recent <= -1.5:
        return f"최근 선행 지표 하락세 ({recent:.1f}%)", "부정"
    return "최근 횡보", "중립"


def _discover_reference_candidates(
    ticker: str,
    stock_hist: pd.DataFrame,
    sector_id: str | None,
    sources: list[dict],
    commodity_cache: dict[str, pd.DataFrame],
) -> list[dict]:
    if stock_hist.empty or len(stock_hist) < 40:
        return []

    universe = list(SECTOR_DISCOVERY_UNIVERSE.get(sector_id or "", []))
    for src in sources:
        if src.get("type") == "commodity" and src.get("symbol"):
            universe.append({
                "symbol": src["symbol"],
                "label": src.get("item", src["symbol"]),
                "why": src.get("thesis") or f'{src.get("item", src["symbol"])} 흐름을 같이 점검합니다.',
            })

    unique_candidates: list[dict] = []
    seen_symbols = {_ticker_key(ticker)}
    for candidate in universe:
        symbol = _ticker_key(candidate["symbol"])
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        unique_candidates.append({**candidate, "symbol": symbol})

    ranked: list[dict] = []
    for candidate in unique_candidates:
        hist = commodity_cache.get(candidate["symbol"], pd.DataFrame())
        if hist.empty:
            try:
                hist = StockDataService.get_stock_history(candidate["symbol"], period="1y")
                commodity_cache[candidate["symbol"]] = hist
            except Exception:
                hist = pd.DataFrame()
        if hist.empty:
            continue

        same_day, lead_5, lead_10 = _compute_return_correlation(stock_hist, hist)
        edge = max(abs(same_day), abs(lead_5), abs(lead_10))
        if edge < 0.18:
            continue

        best_value = same_day
        relation = "동행"
        window = "당일~1개월"
        if abs(lead_10) >= abs(best_value) + 0.03:
            best_value = lead_10
            relation = "선행(2주)"
            window = "향후 2주"
        elif abs(lead_5) >= abs(best_value) + 0.03:
            best_value = lead_5
            relation = "선행(1주)"
            window = "향후 1주"

        positive_if = "up"
        matched_source = next((src for src in sources if _ticker_key(src.get("symbol", "")) == candidate["symbol"]), None)
        if matched_source and matched_source.get("positive_if") == "down":
            positive_if = "down"
        trend_note, state = _describe_signal_state(hist, positive_if)
        ranked.append({
            "symbol": candidate["symbol"],
            "name": candidate["label"],
            "relationship": relation,
            "score": round(edge * 100),
            "same_day_corr": same_day,
            "lead_corr_5d": lead_5,
            "lead_corr_10d": lead_10,
            "best_corr": round(best_value, 3),
            "why_it_matters": candidate["why"],
            "current_signal": trend_note,
            "status": "positive" if state == "긍정" else ("negative" if state == "부정" else "neutral"),
            "window": window,
        })

    ranked.sort(key=lambda item: item.get("score", 0), reverse=True)
    return ranked[:6]


def _get_krx_listing() -> list[dict]:
    cache_key = "krx-listing"
    cached = _get_cached_ttl(cache_key, 60 * 60 * 12)
    if cached is not None:
        return cached

    rows: list[dict] = []
    try:
        url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
        response = requests.get(url, timeout=20)
        html = response.content.decode("euc-kr", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        trs = soup.select("table tr")
        for tr in trs[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) < 4:
                continue
            name = cells[0]
            market = cells[1]
            raw_code = cells[2]
            if not name or not raw_code or not raw_code.isdigit():
                continue
            ticker = f"{raw_code.zfill(6)}.{ 'KQ' if '코스닥' in market else 'KS' }"
            rows.append({
                "ticker": ticker,
                "name": name,
                "market": market,
                "industry": cells[3],
            })
    except Exception:
        rows = []

    _set_cached(cache_key, rows)
    return rows


STOCK_CATALYSTS: dict[str, list[dict]] = {
    "NVDA": [
        {"title": "하이퍼스케일러 AI 투자 지속", "window": "향후 2~3분기", "expected_condition": "MSFT/AMZN/META 계열의 AI CAPEX 기대가 둔화되지 않아야 합니다.", "status": "positive", "detail": "대형 고객 투자 사이클이 살아있으면 NVDA 수요 기대도 유지됩니다.", "importance": 92},
        {"title": "HBM 공급 타이트 유지", "window": "향후 1~2분기", "expected_condition": "하이닉스·마이크론 체인에서 공급 완화 신호가 나오지 않아야 합니다.", "status": "positive", "detail": "HBM이 부족해야 NVDA가 ASP와 납기 우위를 유지합니다.", "importance": 90},
        {"title": "블랙웰 램프업 정상화", "window": "향후 1~2분기", "expected_condition": "TSMC 패키징 병목과 납품 지연 이슈가 재부각되지 않아야 합니다.", "status": "positive", "detail": "차세대 제품 램프업이 늦으면 실적이 아니라 기대부터 훼손됩니다.", "importance": 88},
        {"title": "고객사 커스텀칩 내재화 압력", "window": "향후 2~4분기", "expected_condition": "구글·AWS 자체칩 확대가 NVDA 성장률 둔화보다 빠르지 않아야 합니다.", "status": "negative", "detail": "독점 프리미엄을 잠식하는 장기 리스크입니다.", "importance": 82},
        {"title": "중국 규제 재강화 리스크", "window": "상시", "expected_condition": "추가 수출 규제 헤드라인이 나오지 않아야 합니다.", "status": "negative", "detail": "정책 리스크는 실적보다 먼저 멀티플을 압박합니다.", "importance": 80},
    ],
    "000660.KS": [
        {"title": "DRAM 업황 선반영", "window": "향후 1~3개월", "expected_condition": "MU/메모리 프록시가 꺾이지 않고 유지돼야 합니다.", "status": "positive", "detail": "메모리주는 업황 기대가 실적보다 먼저 주가에 반영됩니다.", "importance": 94},
        {"title": "엔비디아향 HBM 점유율 유지", "window": "향후 1~2분기", "expected_condition": "엔비디아 공급 승인/점유율 관련 부정 기사보다 증산·확대 기사가 우세해야 합니다.", "status": "positive", "detail": "하이닉스 프리미엄은 단순 HBM 수요보다 NVDA향 파이 유지가 더 중요합니다.", "importance": 96},
        {"title": "HBM 믹스 확대", "window": "향후 1~2분기", "expected_condition": "영업이익률이 두 자릿수 이상 유지돼야 합니다.", "status": "positive", "detail": "HBM 비중이 올라가도 마진으로 안 찍히면 기대감이 빠르게 꺾입니다.", "importance": 90},
        {"title": "삼성 추격 속도 관리", "window": "향후 1~2분기", "expected_condition": "삼성 HBM 인증 가속 뉴스가 하이닉스 수급을 압도하지 않아야 합니다.", "status": "negative", "detail": "경쟁사 인증 속도는 하이닉스 초과 프리미엄을 깎을 수 있습니다.", "importance": 78},
        {"title": "메모리 가격 피크아웃", "window": "향후 1~2개월", "expected_condition": "현물/계약가격 상승세가 완만해져도 하락 전환은 아니어야 합니다.", "status": "negative", "detail": "가격이 아직 높아도 하락 추세 전환만 확인되면 주가는 먼저 반응합니다.", "importance": 96},
    ],
    "005930.KS": [
        {"title": "HBM 고객 인증 가속", "window": "향후 1~3분기", "expected_condition": "엔비디아·빅테크향 HBM 인증 확대 뉴스가 실제 공급 확대로 이어져야 합니다.", "status": "positive", "detail": "삼성 반도체 재평가는 HBM 인증이 가장 큰 옵션 가치입니다.", "importance": 92},
        {"title": "파운드리 수율/가동률 개선", "window": "향후 1~3분기", "expected_condition": "첨단 공정 수율 개선과 대형 고객 복귀 기대가 후퇴하지 않아야 합니다.", "status": "positive", "detail": "삼성은 메모리뿐 아니라 파운드리 적자 축소가 멀티플 재평가의 핵심입니다.", "importance": 88},
        {"title": "메모리 업황 바닥 통과", "window": "향후 1~3개월", "expected_condition": "메모리 프록시와 SOXX 흐름이 동반 약세로 돌아서지 않아야 합니다.", "status": "positive", "detail": "업황 반등 기대가 깨지면 대형주의 방어력도 약해집니다.", "importance": 84},
        {"title": "HBM 기대만 앞서는 구간 경계", "window": "향후 1~2개월", "expected_condition": "인증 기사 대비 실제 출하·마진 개선의 간극이 벌어지지 않아야 합니다.", "status": "negative", "detail": "삼성은 기대는 빠르게 선반영되지만 실적이 늦으면 조정도 빠르게 옵니다.", "importance": 82},
    ],
    "TSM": [
        {"title": "CoWoS/첨단 패키징 병목 완화", "window": "향후 1~2분기", "expected_condition": "AI 고객 출하 지연 없이 패키징 증설이 이어져야 합니다.", "status": "positive", "detail": "TSMC는 첨단 패키징이 AI 매출 인식의 핵심 병목입니다.", "importance": 90},
        {"title": "2nm 수율 안정화", "window": "향후 2~4분기", "expected_condition": "차세대 공정 수율 이슈가 확대되지 않아야 합니다.", "status": "positive", "detail": "차세대 공정 수율은 장기 멀티플의 핵심입니다.", "importance": 84},
        {"title": "미국 투자비용 부담", "window": "향후 1~3분기", "expected_condition": "해외 공장 비용 상승이 마진 훼손으로 번지지 않아야 합니다.", "status": "negative", "detail": "글로벌 분산 투자 확대는 마진 압박 요소입니다.", "importance": 74},
    ],
    "AVGO": [
        {"title": "커스텀 AI칩 수요 확대", "window": "향후 1~3분기", "expected_condition": "대형 클라우드 고객의 ASIC 채택이 둔화되지 않아야 합니다.", "status": "positive", "detail": "커스텀칩은 AVGO AI 프리미엄의 핵심입니다.", "importance": 88},
        {"title": "VMware 시너지 가시화", "window": "향후 1~2분기", "expected_condition": "통합 효과가 영업이익률 개선으로 이어져야 합니다.", "status": "positive", "detail": "인수 프리미엄은 실제 시너지로 검증돼야 합니다.", "importance": 82},
        {"title": "빅테크 CAPEX 둔화", "window": "향후 1~2분기", "expected_condition": "AI 네트워킹 투자 둔화 신호가 급격히 나오지 않아야 합니다.", "status": "negative", "detail": "대형 고객 CAPEX 둔화는 네트워킹 기대를 먼저 누릅니다.", "importance": 78},
    ],
    "TSLA": [
        {"title": "자동차 마진 회복", "window": "향후 1~2분기", "expected_condition": "프로모션 확대 없이도 이익률이 회복되는 흐름이 보여야 합니다.", "status": "positive", "detail": "TSLA는 매출보다 마진 방향이 훨씬 중요합니다.", "importance": 94},
        {"title": "Optimus/FSD 기대 유지", "window": "향후 2~4분기", "expected_condition": "관련 출시 일정이 뒤로 밀리지 않아야 합니다.", "status": "positive", "detail": "장기 프리미엄의 상당 부분이 로봇/자율주행 기대에서 나옵니다.", "importance": 82},
        {"title": "EV 가격 경쟁 심화", "window": "향후 1~2분기", "expected_condition": "판가 인하 재개 없이 인도량이 유지돼야 합니다.", "status": "negative", "detail": "수요는 살아 있어도 가격을 깎아야 하면 주가는 먼저 할인합니다.", "importance": 90},
    ],
    "ISRG": [
        {"title": "수술 건수/설치대수 유지", "window": "향후 1~2분기", "expected_condition": "프로시저 성장과 신규 설치 증가가 동반돼야 합니다.", "status": "positive", "detail": "ISRG 밸류는 반복 수익형 수술 건수에 민감합니다.", "importance": 86},
        {"title": "병원 CAPEX 회복", "window": "향후 1~3분기", "expected_condition": "대형 병원 장비 투자 지연이 심해지지 않아야 합니다.", "status": "positive", "detail": "고가 장비 도입 속도가 멀티플 유지의 핵심입니다.", "importance": 72},
        {"title": "경쟁 심화 제한적", "window": "상시", "expected_condition": "경쟁사 침투 기사보다 점유율 유지 신호가 우세해야 합니다.", "status": "negative", "detail": "독점 프리미엄이 약해지면 밸류 압축이 빠릅니다.", "importance": 64},
    ],
    "454910.KS": [
        {"title": "협동로봇 설치 확대", "window": "향후 1~2분기", "expected_condition": "대기업 자동화 도입 사례가 늘어나야 합니다.", "status": "positive", "detail": "설치 레퍼런스 확대가 멀티플을 끌어올립니다.", "importance": 82},
        {"title": "흑자전환 신뢰 형성", "window": "향후 1~2분기", "expected_condition": "외형 성장뿐 아니라 적자 축소/흑자전환 흐름이 보여야 합니다.", "status": "positive", "detail": "국내 로봇주는 손익 개선이 핵심 전환점입니다.", "importance": 88},
        {"title": "로봇 기대 선반영 과열", "window": "향후 1~2개월", "expected_condition": "수주 뉴스 없이 기대감만 과열되지 않아야 합니다.", "status": "negative", "detail": "실적보다 테마 과열이 먼저 꺾일 수 있습니다.", "importance": 70},
    ],
    "FANUY": [
        {"title": "중국/미국 제조업 자동화 회복", "window": "향후 1~3분기", "expected_condition": "제조업 PMI와 자동화 투자 심리가 동반 회복돼야 합니다.", "status": "positive", "detail": "FANUC은 제조업 설비투자 사이클 민감주입니다.", "importance": 82},
        {"title": "엔화 약세 지속", "window": "향후 1~2개월", "expected_condition": "엔화 강세 전환이 급격히 오지 않아야 합니다.", "status": "positive", "detail": "수출 경쟁력 유지에 우호적입니다.", "importance": 66},
        {"title": "산업 경기 재둔화", "window": "향후 1~2분기", "expected_condition": "글로벌 설비투자 위축이 심해지지 않아야 합니다.", "status": "negative", "detail": "산업 경기 둔화는 주문 감소로 곧장 연결됩니다.", "importance": 74},
    ],
    "267250.KS": [
        {"title": "현대차 그룹 자동화 확대", "window": "향후 1~3분기", "expected_condition": "그룹 스마트팩토리/물류 자동화 투자가 유지돼야 합니다.", "status": "positive", "detail": "그룹 CAPEX가 가장 직접적인 수혜 변수입니다.", "importance": 84},
        {"title": "국내 산업용 로봇 흑자전환", "window": "향후 1~2분기", "expected_condition": "손익 개선 속도가 예상보다 느려지지 않아야 합니다.", "status": "positive", "detail": "손익 개선이 밸류 재평가의 트리거입니다.", "importance": 80},
        {"title": "외부 고객 확장 지연", "window": "향후 1~2분기", "expected_condition": "그룹 외 고객 확대가 정체되지 않아야 합니다.", "status": "negative", "detail": "그룹 내부 의존이 지속되면 프리미엄이 제한됩니다.", "importance": 68},
    ],
    "CEG": [
        {"title": "AI 데이터센터 전력 수요", "window": "향후 2~4분기", "expected_condition": "전력 수요 프록시와 유틸리티 흐름이 유지돼야 합니다.", "status": "positive", "detail": "원전주는 전력 수요 증가 기대가 식으면 프리미엄이 약해집니다.", "importance": 90},
        {"title": "원전 장기계약 재평가", "window": "향후 1~3분기", "expected_condition": "전력 가격과 장기 계약 기대가 꺾이지 않아야 합니다.", "status": "positive", "detail": "장기 현금흐름 재평가가 CEG 핵심 스토리입니다.", "importance": 80},
        {"title": "정책/규제 역풍", "window": "상시", "expected_condition": "원전 정책 후퇴 또는 규제 악화 헤드라인이 없어야 합니다.", "status": "negative", "detail": "정책 변화는 실적보다 먼저 섹터 밸류에이션을 누릅니다.", "importance": 74},
    ],
    "CCJ": [
        {"title": "우라늄 가격 상승 지속", "window": "향후 1~3개월", "expected_condition": "URA와 우라늄 가격이 동반 약세로 전환되지 않아야 합니다.", "status": "positive", "detail": "CCJ는 우라늄 가격 기대를 가장 직접적으로 반영합니다.", "importance": 95},
        {"title": "공급 부족 심화 기대", "window": "향후 1~2분기", "expected_condition": "장기 계약 가격 기대가 낮아지지 않아야 합니다.", "status": "positive", "detail": "현물보다 장기 공급 부족 기대가 더 중요합니다.", "importance": 82},
        {"title": "우라늄 가격 피크아웃", "window": "향후 1~2개월", "expected_condition": "우라늄 가격이 급등 후 하락 추세로 꺾이지 않아야 합니다.", "status": "negative", "detail": "원자재주는 아직 가격이 높아도 추세 전환에 먼저 맞습니다.", "importance": 88},
    ],
    "BWXT": [
        {"title": "해군 원자로/원전 부품 수주 확대", "window": "향후 1~3분기", "expected_condition": "방산 및 원전 관련 신규 수주가 유지돼야 합니다.", "status": "positive", "detail": "BWXT는 안정적 장기 수주의 질이 핵심입니다.", "importance": 82},
        {"title": "SMR 기대 보조 강화", "window": "향후 2~4분기", "expected_condition": "SMR 관련 정책/프로젝트 지연이 심화되지 않아야 합니다.", "status": "positive", "detail": "SMR 옵션 가치가 추가 프리미엄을 만듭니다.", "importance": 70},
        {"title": "정부 예산 지연", "window": "향후 1~2분기", "expected_condition": "연방 예산 불확실성이 수주 공백으로 이어지지 않아야 합니다.", "status": "negative", "detail": "정책 지연은 수주형 업체에 직접적입니다.", "importance": 68},
    ],
    "034020.KS": [
        {"title": "체코·중동 원전 수주 가시화", "window": "향후 1~3분기", "expected_condition": "해외 원전 수주 기대가 계약 진전으로 이어져야 합니다.", "status": "positive", "detail": "두산에너빌리티 재평가의 핵심입니다.", "importance": 86},
        {"title": "국내 원전 정책 지속", "window": "향후 1~3분기", "expected_condition": "탈원전 회귀 우려보다 원전 확대 신호가 우세해야 합니다.", "status": "positive", "detail": "정책 방향이 밸류에 큰 영향을 줍니다.", "importance": 76},
        {"title": "수주 대비 마진 미흡", "window": "향후 1~2분기", "expected_condition": "수주만 늘고 손익 개선이 지연되지 않아야 합니다.", "status": "negative", "detail": "주가는 수주보다 이익 체력에 더 민감합니다.", "importance": 70},
    ],
    "015760.KS": [
        {"title": "전기요금 정상화", "window": "향후 1~2분기", "expected_condition": "요금 인상 또는 연료비 부담 완화가 지속돼야 합니다.", "status": "positive", "detail": "한전은 정책 요인이 손익을 좌우합니다.", "importance": 92},
        {"title": "연료비 부담 완화", "window": "향후 1~2개월", "expected_condition": "천연가스 등 연료비가 다시 급등하지 않아야 합니다.", "status": "positive", "detail": "연료비 안정이 흑자 지속성의 핵심입니다.", "importance": 84},
        {"title": "정책 불확실성 재확대", "window": "상시", "expected_condition": "요금 동결·정책 개입이 다시 확대되지 않아야 합니다.", "status": "negative", "detail": "정책 개입은 주가 할인 요인입니다.", "importance": 78},
    ],
    "CRWD": [
        {"title": "ARR 성장 유지", "window": "향후 1~2분기", "expected_condition": "20%대 이상의 성장률이 유지돼야 합니다.", "status": "positive", "detail": "고밸류 보안주는 성장률 둔화가 바로 멀티플 압축으로 연결됩니다.", "importance": 92},
        {"title": "플랫폼 확장 모멘텀", "window": "향후 1~3분기", "expected_condition": "고객당 모듈 수와 대형 계약 증가세가 꺾이지 않아야 합니다.", "status": "positive", "detail": "단일 제품 스토리에서 플랫폼 스토리로 가야 프리미엄이 유지됩니다.", "importance": 76},
        {"title": "운영 리스크 재발", "window": "상시", "expected_condition": "대형 장애/보안사고 재발이 없어야 합니다.", "status": "negative", "detail": "운영 신뢰를 잃으면 성장률과 무관하게 재평가가 발생합니다.", "importance": 84},
    ],
    "PANW": [
        {"title": "플랫폼 통합 확장", "window": "향후 1~3분기", "expected_condition": "차세대 보안 플랫폼 매출 믹스가 계속 확대돼야 합니다.", "status": "positive", "detail": "PANW는 통합 플랫폼 스토리가 핵심입니다.", "importance": 88},
        {"title": "성장 둔화 리스크", "window": "향후 1~2분기", "expected_condition": "매출 성장률이 급격히 낮아지지 않아야 합니다.", "status": "negative", "detail": "플랫폼 프리미엄은 성장률 둔화에 민감합니다.", "importance": 80},
    ],
    "FTNT": [
        {"title": "방화벽/OT 보안 수요 유지", "window": "향후 1~3분기", "expected_condition": "기업 보안 CAPEX가 급격히 위축되지 않아야 합니다.", "status": "positive", "detail": "FTNT는 수익성 좋은 네트워크 보안 수요가 핵심입니다.", "importance": 78},
        {"title": "매출 성장 재가속 필요", "window": "향후 1~2분기", "expected_condition": "두 자릿수 매출 성장률을 유지해야 합니다.", "status": "negative", "detail": "성장 둔화가 길어지면 저평가 논리도 약해집니다.", "importance": 72},
    ],
    "ZS": [
        {"title": "제로트러스트 확산", "window": "향후 1~3분기", "expected_condition": "고성장 SaaS 보안 수요가 둔화되지 않아야 합니다.", "status": "positive", "detail": "ZS는 제로트러스트 전환 속도에 가장 민감합니다.", "importance": 86},
        {"title": "흑자전환 확인", "window": "향후 1~2분기", "expected_condition": "수익성 개선 흐름이 유지돼야 합니다.", "status": "positive", "detail": "고성장과 수익성 동시 달성이 필요합니다.", "importance": 82},
    ],
    "S": [
        {"title": "초고성장 유지", "window": "향후 1~2분기", "expected_condition": "성장률 둔화 없이 매출 확대가 이어져야 합니다.", "status": "positive", "detail": "SentinelOne은 성장 모멘텀이 거의 전부입니다.", "importance": 84},
        {"title": "적자 확대 리스크", "window": "향후 1~2분기", "expected_condition": "적자 폭이 다시 커지지 않아야 합니다.", "status": "negative", "detail": "고금리 환경에서 적자 성장주는 더 민감합니다.", "importance": 88},
    ],
    "LLY": [
        {"title": "GLP-1 처방 모멘텀", "window": "향후 1~2분기", "expected_condition": "매출 성장률과 공급 확장 기대가 동시에 유지돼야 합니다.", "status": "positive", "detail": "LLY는 비만약 성장 기대가 핵심 프리미엄입니다.", "importance": 95},
        {"title": "경쟁사 점유율 압박", "window": "향후 1~3개월", "expected_condition": "NVO 상대 강세가 과도하게 벌어지지 않아야 합니다.", "status": "negative", "detail": "경쟁 구도 변화는 실적 수치보다 먼저 주가에 반영됩니다.", "importance": 78},
    ],
    "CRSP": [
        {"title": "임상/승인 기대 유지", "window": "향후 2~4분기", "expected_condition": "임상 일정 지연이나 안전성 우려가 부각되지 않아야 합니다.", "status": "positive", "detail": "CRSP는 임상 성공 기대가 실적보다 훨씬 중요합니다.", "importance": 94},
        {"title": "현금 소진 통제", "window": "향후 1~2분기", "expected_condition": "현금 런웨이 우려가 커지지 않아야 합니다.", "status": "negative", "detail": "바이오 성장주는 자금조달 우려가 생기면 먼저 할인됩니다.", "importance": 84},
    ],
    "ILMN": [
        {"title": "유전체 장비 수요 회복", "window": "향후 1~3분기", "expected_condition": "매출 성장률이 재가속돼야 합니다.", "status": "positive", "detail": "ILMN은 장비 교체와 시퀀싱 수요 회복이 핵심입니다.", "importance": 82},
        {"title": "바이오 CAPEX 위축", "window": "향후 1~2분기", "expected_condition": "연구개발/장비 투자 심리가 급격히 약해지지 않아야 합니다.", "status": "negative", "detail": "장비주는 CAPEX 둔화에 먼저 영향을 받습니다.", "importance": 70},
    ],
    "207940.KS": [
        {"title": "CDMO 수주잔고 확대", "window": "향후 1~3분기", "expected_condition": "대형 고객 수주와 증설 기대가 유지돼야 합니다.", "status": "positive", "detail": "삼성바이오는 수주잔고가 가장 중요한 선행 변수입니다.", "importance": 94},
        {"title": "고마진 유지", "window": "향후 1~2분기", "expected_condition": "이익률이 재차 둔화되지 않아야 합니다.", "status": "positive", "detail": "증설만으로는 부족하고 마진 유지가 같이 확인돼야 합니다.", "importance": 80},
    ],
    "068270.KS": [
        {"title": "미국 판매 모멘텀", "window": "향후 1~3분기", "expected_condition": "주요 제품 미국 매출 기대가 꺾이지 않아야 합니다.", "status": "positive", "detail": "셀트리온은 미국 판매와 제품 믹스가 핵심입니다.", "importance": 82},
        {"title": "가격 경쟁 심화", "window": "향후 1~2분기", "expected_condition": "바이오시밀러 가격 경쟁이 과도하게 심해지지 않아야 합니다.", "status": "negative", "detail": "매출 성장보다 마진 압박 리스크가 먼저 반영될 수 있습니다.", "importance": 74},
    ],
    "IONQ": [
        {"title": "기술 마일스톤 기대", "window": "향후 2~4분기", "expected_condition": "로드맵 지연 없이 기술 진척 헤드라인이 이어져야 합니다.", "status": "positive", "detail": "양자주는 실적보다 로드맵 신뢰가 더 중요합니다.", "importance": 88},
        {"title": "현금 소진 리스크", "window": "향후 1~2분기", "expected_condition": "적자 폭이 다시 크게 악화되지 않아야 합니다.", "status": "negative", "detail": "자금조달 우려가 부각되면 기대감은 바로 할인됩니다.", "importance": 93},
    ],
    "GOOG": [
        {"title": "클라우드/광고 현금창출 유지", "window": "향후 1~2분기", "expected_condition": "핵심 본업 성장 둔화가 크지 않아야 합니다.", "status": "positive", "detail": "양자 투자도 결국 본업 현금창출이 받쳐줘야 합니다.", "importance": 72},
        {"title": "양자 장기옵션 유지", "window": "향후 2~6분기", "expected_condition": "관련 연구 진척과 투자 스토리가 유지돼야 합니다.", "status": "positive", "detail": "GOOG의 양자 스토리는 장기 옵션 가치입니다.", "importance": 54},
    ],
    "IBM": [
        {"title": "엔터프라이즈 양자 신뢰", "window": "향후 2~4분기", "expected_condition": "기업용 양자 로드맵 진척이 이어져야 합니다.", "status": "positive", "detail": "IBM은 상용화 신뢰도가 핵심입니다.", "importance": 70},
        {"title": "본업 성장 정체", "window": "향후 1~2분기", "expected_condition": "기존 IT 서비스/소프트웨어 실적이 크게 흔들리지 않아야 합니다.", "status": "negative", "detail": "본업 약세는 양자 프리미엄을 덮을 수 있습니다.", "importance": 62},
    ],
    "RGTI": [
        {"title": "기술 검증 기대", "window": "향후 2~4분기", "expected_condition": "큐비트 로드맵과 기술 데모 기대가 유지돼야 합니다.", "status": "positive", "detail": "Rigetti는 로드맵 신뢰도가 사실상 전부입니다.", "importance": 86},
        {"title": "자금조달 압박", "window": "향후 1~2분기", "expected_condition": "추가 증자 우려가 크게 부각되지 않아야 합니다.", "status": "negative", "detail": "초기 기술주는 자금조달 이슈에 즉각 반응합니다.", "importance": 92},
    ],
    "MSFT": [
        {"title": "클라우드/AI CAPEX 유지", "window": "향후 1~3분기", "expected_condition": "Azure 성장 둔화 없이 AI 투자 기대가 유지돼야 합니다.", "status": "positive", "detail": "MSFT는 AI 투자 확장의 중심축입니다.", "importance": 86},
        {"title": "양자 옵션 유지", "window": "향후 2~6분기", "expected_condition": "관련 연구와 Azure Quantum 스토리가 유지돼야 합니다.", "status": "positive", "detail": "양자 스토리는 본업 위에 얹힌 옵션 가치입니다.", "importance": 50},
    ],
    "RKLB": [
        {"title": "발사/우주시스템 수주 가속", "window": "향후 1~3분기", "expected_condition": "매출 성장과 backlog 기대가 같이 유지돼야 합니다.", "status": "positive", "detail": "우주주는 단순 기대보다 실제 수주 모멘텀이 중요합니다.", "importance": 90},
        {"title": "프로그램 지연 리스크", "window": "상시", "expected_condition": "Neutron 일정 지연이 커지지 않아야 합니다.", "status": "negative", "detail": "일정 지연은 장기 기대 밸류를 빠르게 깎습니다.", "importance": 84},
    ],
    "LMT": [
        {"title": "방산/우주 예산 안정", "window": "향후 2~4분기", "expected_condition": "방산 예산과 우주 계약 기대가 흔들리지 않아야 합니다.", "status": "positive", "detail": "LMT는 안정적 수주와 우주 옵션을 같이 봐야 합니다.", "importance": 76},
        {"title": "미사일 방어/우주 계약 유지", "window": "향후 1~3분기", "expected_condition": "우주·미사일 방어 관련 수주 공백이 생기지 않아야 합니다.", "status": "positive", "detail": "전통 방산 외 우주 옵션 가치가 중요합니다.", "importance": 72},
        {"title": "예산 협상 지연", "window": "향후 1~2분기", "expected_condition": "미국 예산 협상 지연이 대형 프로그램 차질로 번지지 않아야 합니다.", "status": "negative", "detail": "예산 지연은 방산 멀티플에 부담입니다.", "importance": 64},
    ],
    "LHX": [
        {"title": "우주/센서 계약 흐름", "window": "향후 2~4분기", "expected_condition": "정부 수주와 우주통신 기대가 유지돼야 합니다.", "status": "positive", "detail": "LHX는 방산 안정성 위에 우주 옵션이 얹혀 있습니다.", "importance": 70},
    ],
    "047810.KS": [
        {"title": "KF-21/수출 계약 진전", "window": "향후 1~3분기", "expected_condition": "양산 일정과 수출 계약 뉴스가 끊기지 않아야 합니다.", "status": "positive", "detail": "한국항공우주는 완제기 수출 기대가 핵심입니다.", "importance": 88},
        {"title": "방산 수출 모멘텀 유지", "window": "향후 1~2분기", "expected_condition": "국내 방산 전반의 수출 뉴스 흐름이 꺾이지 않아야 합니다.", "status": "positive", "detail": "국내 방산 체인 심리와 함께 움직입니다.", "importance": 72},
        {"title": "양산 마진 지연", "window": "향후 1~2분기", "expected_condition": "수주 증가 대비 수익성 개선이 늦어지지 않아야 합니다.", "status": "negative", "detail": "매출보다 이익률 검증이 늦으면 조정이 나옵니다.", "importance": 68},
    ],
    "BA": [
        {"title": "턴어라운드 신뢰 회복", "window": "향후 1~3분기", "expected_condition": "생산 차질과 품질 이슈 재발이 없어야 합니다.", "status": "positive", "detail": "Boeing은 실적보다 신뢰 회복이 먼저입니다.", "importance": 82},
        {"title": "품질/규제 리스크", "window": "상시", "expected_condition": "추가 규제 조사나 품질 이슈가 발생하지 않아야 합니다.", "status": "negative", "detail": "악재 재발은 회복 기대를 빠르게 무너뜨립니다.", "importance": 88},
    ],
    "BE": [
        {"title": "데이터센터 전력 수요 반영", "window": "향후 2~4분기", "expected_condition": "수주 기대가 매출 성장으로 연결돼야 합니다.", "status": "positive", "detail": "스토리만 있고 실적 전환이 없으면 프리미엄이 유지되기 어렵습니다.", "importance": 82},
        {"title": "흑자전환 검증", "window": "향후 1~2분기", "expected_condition": "영업이익률이 0% 이상으로 안착해야 합니다.", "status": "positive", "detail": "흑자전환은 밸류 체질 개선의 핵심 검증 포인트입니다.", "importance": 95},
    ],
    "PLUG": [
        {"title": "정책/보조금 기대", "window": "향후 1~3분기", "expected_condition": "미국 청정에너지 지원 기대가 꺾이지 않아야 합니다.", "status": "positive", "detail": "PLUG는 정책 모멘텀 의존도가 높습니다.", "importance": 78},
        {"title": "현금 소진 리스크", "window": "향후 1~2분기", "expected_condition": "적자와 자금조달 우려가 추가로 커지지 않아야 합니다.", "status": "negative", "detail": "수소주는 자금조달 리스크가 주가에 먼저 반영됩니다.", "importance": 96},
    ],
    "ENPH": [
        {"title": "태양광/가정용 에너지 회복", "window": "향후 1~3분기", "expected_condition": "태양광 ETF와 설치 수요 기대가 회복돼야 합니다.", "status": "positive", "detail": "ENPH는 금리와 주택경기 민감도가 큽니다.", "importance": 84},
        {"title": "금리 부담 완화 필요", "window": "향후 1~2분기", "expected_condition": "고금리 압박이 더 심해지지 않아야 합니다.", "status": "negative", "detail": "태양광 수요는 금융비용에 크게 영향을 받습니다.", "importance": 72},
    ],
    "005380.KS": [
        {"title": "친환경차 믹스 확대", "window": "향후 1~3분기", "expected_condition": "EV/친환경차 수요와 수익성이 같이 유지돼야 합니다.", "status": "positive", "detail": "현대차는 믹스 개선이 핵심입니다.", "importance": 82},
        {"title": "환율/판가 방어", "window": "향후 1~2분기", "expected_condition": "원화 강세와 판가 인하가 동시에 오지 않아야 합니다.", "status": "negative", "detail": "완성차는 환율과 판가 두 축에 민감합니다.", "importance": 70},
    ],
    "336260.KS": [
        {"title": "수소발전 정책 수혜", "window": "향후 2~4분기", "expected_condition": "국내 수소 발전 정책 기대가 유지돼야 합니다.", "status": "positive", "detail": "정책과 프로젝트 발주가 핵심입니다.", "importance": 80},
        {"title": "흑자전환 확인", "window": "향후 1~2분기", "expected_condition": "이익률이 다시 적자로 밀리지 않아야 합니다.", "status": "negative", "detail": "적자 회귀는 기대를 크게 훼손합니다.", "importance": 78},
    ],
}

SECTOR_PULSE_SOURCES: dict[str, list[dict]] = {
    "ai-semi": [
        {"name": "AI 반도체 업황 (SOXX)", "symbol": "SOXX", "positive_if": "up", "weight": 90, "thesis": "AI 반도체 업황이 꺾이면 섹터 전체 기대가 먼저 흔들립니다.", "window": "향후 1~3개월"},
        {"name": "메모리 사이클 (MU)", "symbol": "MU", "positive_if": "up", "weight": 88, "thesis": "메모리 업황 기대는 삼성전자와 하이닉스 주가에 가장 빠르게 반영됩니다.", "window": "향후 1~3개월"},
        {"name": "AI 수요 핵심 고객 (NVDA)", "symbol": "NVDA", "positive_if": "up", "weight": 82, "thesis": "NVDA 기대감은 AI 인프라 수요 지속 여부를 가장 직접적으로 보여줍니다.", "window": "향후 1~2개월"},
        {"name": "공급망/산업수요 (구리)", "symbol": "HG=F", "positive_if": "stable", "weight": 45, "thesis": "구리 급등은 공급망 비용 부담, 급락은 수요 둔화 우려로 해석될 수 있습니다.", "window": "향후 1~2개월"},
    ],
    "robotics": [
        {"name": "로봇/자동화 심리 (ROBO)", "symbol": "ROBO", "positive_if": "up", "weight": 86, "thesis": "로봇 섹터 위험선호가 식으면 개별 종목 기대도 빠르게 낮아집니다.", "window": "향후 1~3개월"},
        {"name": "산업 경기 (구리)", "symbol": "HG=F", "positive_if": "up", "weight": 58, "thesis": "산업 자동화 수요는 제조업 경기와 같이 움직이는 경우가 많습니다.", "window": "향후 1~2개월"},
        {"name": "핵심 대장주 기대 (TSLA)", "symbol": "TSLA", "positive_if": "up", "weight": 75, "thesis": "Optimus와 자율주행 기대가 꺾이면 로봇 테마 심리도 약해질 수 있습니다.", "window": "향후 1~2개월"},
    ],
    "smr-nuclear": [
        {"name": "우라늄 가격 (URA)", "symbol": "URA", "positive_if": "up", "weight": 92, "thesis": "우라늄 가격과 관련 ETF 흐름은 원전 기대를 가장 먼저 반영합니다.", "window": "향후 1~3개월"},
        {"name": "전력 수요 (XLU)", "symbol": "XLU", "positive_if": "up", "weight": 68, "thesis": "전력 수요 기대가 살아야 원전 가치가 강화됩니다.", "window": "향후 1~3개월"},
        {"name": "천연가스 가격", "symbol": "NG=F", "positive_if": "up", "weight": 54, "thesis": "가스 가격 강세는 원전의 상대적 경제성을 높이는 경우가 많습니다.", "window": "향후 1~2개월"},
    ],
    "cybersec": [
        {"name": "사이버보안 섹터 (BUG)", "symbol": "BUG", "positive_if": "up", "weight": 90, "thesis": "섹터 ETF는 보안주 멀티플 선호도를 가장 잘 보여줍니다.", "window": "향후 1~3개월"},
        {"name": "핵심 리더십 (CRWD)", "symbol": "CRWD", "positive_if": "up", "weight": 78, "thesis": "리더 종목 성장 기대가 꺾이면 섹터 전체 프리미엄이 압축됩니다.", "window": "향후 1~2개월"},
        {"name": "기술주 위험선호 (QQQ)", "symbol": "QQQ", "positive_if": "up", "weight": 55, "thesis": "보안주는 성장주 멀티플 영향을 강하게 받습니다.", "window": "향후 1~2개월"},
    ],
    "space": [
        {"name": "우주산업 심리 (UFO)", "symbol": "UFO", "positive_if": "up", "weight": 88, "thesis": "우주 테마 전반의 위험선호를 빠르게 보여주는 프록시입니다.", "window": "향후 1~3개월"},
        {"name": "방산/정부 수요 (ITA)", "symbol": "ITA", "positive_if": "up", "weight": 72, "thesis": "정부 예산과 방산 흐름은 우주 인프라 투자 기대를 보조합니다.", "window": "향후 1~3개월"},
        {"name": "핵심 성장주 (RKLB)", "symbol": "RKLB", "positive_if": "up", "weight": 76, "thesis": "Rocket Lab 기대가 꺾이면 우주 성장 섹터의 심리도 빠르게 식습니다.", "window": "향후 1~2개월"},
    ],
    "biotech": [
        {"name": "바이오텍 심리 (XBI)", "symbol": "XBI", "positive_if": "up", "weight": 88, "thesis": "적자/고성장 바이오의 위험선호를 가장 잘 반영합니다.", "window": "향후 1~3개월"},
        {"name": "대형 바이오 (IBB)", "symbol": "IBB", "positive_if": "up", "weight": 72, "thesis": "대형 바이오 강세는 섹터 전체 신뢰 회복과 연결됩니다.", "window": "향후 1~3개월"},
        {"name": "비만약 리더십 (LLY)", "symbol": "LLY", "positive_if": "up", "weight": 68, "thesis": "LLY 흐름은 바이오 섹터 내 성장 프리미엄 지속 여부를 보여줍니다.", "window": "향후 1~2개월"},
    ],
    "quantum": [
        {"name": "양자컴퓨팅 심리 (QTUM)", "symbol": "QTUM", "positive_if": "up", "weight": 92, "thesis": "양자 섹터는 기술 기대감 중심이라 ETF 흐름이 특히 중요합니다.", "window": "향후 1~3개월"},
        {"name": "고위험 성장주 (IONQ)", "symbol": "IONQ", "positive_if": "up", "weight": 78, "thesis": "IONQ 흐름은 양자 섹터 리스크온/리스크오프를 빠르게 보여줍니다.", "window": "향후 1~2개월"},
        {"name": "빅테크 지원 (GOOG)", "symbol": "GOOG", "positive_if": "up", "weight": 56, "thesis": "대형 플랫폼의 양자 투자 기대가 살아야 장기 스토리가 유지됩니다.", "window": "향후 1~3개월"},
    ],
    "hydrogen": [
        {"name": "클린에너지 심리 (ICLN)", "symbol": "ICLN", "positive_if": "up", "weight": 88, "thesis": "수소 섹터는 클린에너지 위험선호와 정책 기대에 크게 좌우됩니다.", "window": "향후 1~3개월"},
        {"name": "촉매/원가 (백금)", "symbol": "PL=F", "positive_if": "up", "weight": 44, "thesis": "백금은 수소 밸류체인 기대와 비용 구조를 동시에 보여주는 참고 지표입니다.", "window": "향후 1~2개월"},
        {"name": "대표 성장주 (BE)", "symbol": "BE", "positive_if": "up", "weight": 72, "thesis": "대표 종목 기대가 꺾이면 수소 섹터 전반의 신뢰도 같이 낮아집니다.", "window": "향후 1~2개월"},
    ],
}


def _merge_catalysts(ticker: str, summary: dict) -> dict:
    catalysts = STOCK_CATALYSTS.get(ticker, STOCK_CATALYSTS.get(ticker.replace(".KS", "").replace(".KQ", ""), []))
    if catalysts:
        summary["momentum_notes"] = sorted(catalysts, key=lambda note: note.get("importance", 0), reverse=True)[:4]
    else:
        summary["momentum_notes"] = list(summary.get("momentum_notes", []))[:3]
    summary["leading_risks"] = [note for note in summary["momentum_notes"] if note.get("status") == "negative"][:4]
    summary["leading_supports"] = [note for note in summary["momentum_notes"] if note.get("status") == "positive"][:4]
    return summary


def _compute_symbol_trend_snapshot(symbol: str, positive_if: str) -> dict:
    hist = StockDataService.get_stock_history(symbol, period="6mo")
    if hist.empty or len(hist) < 20:
        return {
            "symbol": symbol,
            "status": "neutral",
            "detail": "데이터 부족",
            "current": None,
            "change_pct": 0.0,
            "trend_pct": 0.0,
            "threshold": None,
        }

    closes = hist["Close"].dropna().astype(float).values
    current = float(closes[-1])
    first = float(closes[0])
    ma20 = float(np.mean(closes[-20:]))
    ma5 = float(np.mean(closes[-5:]))
    change_pct = (current - first) / first * 100 if first else 0.0
    trend_pct = (ma5 - ma20) / ma20 * 100 if ma20 else 0.0

    if positive_if == "up":
        status = "positive" if trend_pct > 1.0 else ("negative" if trend_pct < -1.0 else "neutral")
        threshold = round(ma20, 2)
        detail = f"{current:.2f} · 5일선이 20일선 대비 {trend_pct:+.1f}%"
    elif positive_if == "down":
        status = "positive" if trend_pct < -1.0 else ("negative" if trend_pct > 1.0 else "neutral")
        threshold = round(ma20, 2)
        detail = f"{current:.2f} · 최근 추세 {trend_pct:+.1f}%"
    else:
        status = "positive" if abs(trend_pct) < 1.5 else "negative"
        threshold = round(ma20, 2)
        detail = f"{current:.2f} · 변동 {trend_pct:+.1f}%"

    return {
        "symbol": symbol,
        "status": status,
        "detail": detail,
        "current": round(current, 2),
        "change_pct": round(change_pct, 1),
        "trend_pct": round(trend_pct, 1),
        "threshold": threshold,
    }


@router.get("/analysis/{ticker}")
async def get_analysis(ticker: str) -> AnalysisResult:
    """Full technical analysis with buy/sell signal for a ticker."""
    df = StockDataService.get_stock_history(ticker, period="6mo")

    rsi = TechnicalAnalysisService.calculate_rsi(df)
    macd_val, macd_signal, _ = TechnicalAnalysisService.calculate_macd(df)
    bb_upper, bb_middle, bb_lower = TechnicalAnalysisService.calculate_bollinger_bands(df)
    smas = TechnicalAnalysisService.calculate_sma(df)
    recommendation, confidence = TechnicalAnalysisService.generate_buy_sell_signal(df)

    signal_str = recommendation

    indicators = TechnicalIndicators(
        rsi=rsi,
        macd=macd_val,
        macd_signal=macd_signal,
        bollinger_upper=bb_upper,
        bollinger_middle=bb_middle,
        bollinger_lower=bb_lower,
        sma_20=smas.get(20),
        sma_50=smas.get(50),
        sma_200=smas.get(200),
        buy_sell_signal=signal_str,
    )

    return AnalysisResult(
        ticker=ticker.upper(),
        indicators=indicators,
        recommendation=recommendation,
        confidence_score=confidence,
    )


@router.get("/analysis/{ticker}/chart-data")
async def get_chart_data(ticker: str, period: str = "3mo") -> dict:
    """OHLCV data with ALL indicator overlays inlined per data point."""
    df = StockDataService.get_stock_history(ticker, period=period)

    if df.empty:
        return {"ticker": ticker, "data": []}

    close = df["Close"]

    # SMA overlays
    sma_20 = close.rolling(window=20).mean()
    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()

    # Bollinger Bands
    bb_middle = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_middle + (bb_std * 2)
    bb_lower = bb_middle - (bb_std * 2)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_histogram = macd_line - macd_signal

    # Build inline data
    data = []
    for i, (idx, row) in enumerate(df.iterrows()):
        point = {
            "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        # Inline indicators (None if not enough data)
        for name, series in [
            ("sma_20", sma_20), ("sma_50", sma_50), ("sma_200", sma_200),
            ("bollinger_upper", bb_upper), ("bollinger_middle", bb_middle), ("bollinger_lower", bb_lower),
            ("rsi", rsi), ("macd", macd_line), ("macd_signal", macd_signal), ("macd_histogram", macd_histogram),
        ]:
            v = series.iloc[i]
            point[name] = round(float(v), 2) if not pd.isna(v) else None
        data.append(point)

    return {"ticker": ticker.upper(), "data": data}


@router.get("/analysis/{ticker}/earnings")
async def get_earnings(ticker: str) -> dict:
    """Get earnings data (quarterly EPS, revenue) from yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Quarterly earnings
        quarterly_earnings = []
        try:
            qe = stock.quarterly_earnings
            if qe is not None and not qe.empty:
                for idx, row in qe.iterrows():
                    quarterly_earnings.append({
                        "date": str(idx),
                        "revenue": float(row.get("Revenue", 0)) if not pd.isna(row.get("Revenue", None)) else None,
                        "earnings": float(row.get("Earnings", 0)) if not pd.isna(row.get("Earnings", None)) else None,
                    })
        except Exception:
            pass

        # Quarterly financials
        quarterly_revenue = []
        try:
            qf = stock.quarterly_financials
            if qf is not None and not qf.empty:
                for col in qf.columns:
                    rev = qf.loc["Total Revenue", col] if "Total Revenue" in qf.index else None
                    net = qf.loc["Net Income", col] if "Net Income" in qf.index else None
                    quarterly_revenue.append({
                        "date": str(col.date()) if hasattr(col, "date") else str(col),
                        "revenue": float(rev) if rev is not None and not pd.isna(rev) else None,
                        "net_income": float(net) if net is not None and not pd.isna(net) else None,
                    })
        except Exception:
            pass

        return {
            "ticker": ticker.upper(),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "quarterly_earnings": quarterly_earnings,
            "quarterly_revenue": quarterly_revenue,
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


@router.get("/analysis/{ticker}/pattern")
async def get_pattern_analysis(ticker: str) -> dict:
    """
    Historical pattern analysis:
    - Find significant price moves in history
    - Analyze what indicators looked like before each major move
    - Compare current setup to historical patterns
    - Return pattern matches with similarity scores
    """
    try:
        # Get 2 years of data for pattern analysis
        df = StockDataService.get_stock_history(ticker, period="2y")
        if df.empty or len(df) < 60:
            return {"ticker": ticker.upper(), "patterns": [], "current_setup": {}, "events": []}

        close = df["Close"]
        dates = df.index

        # Calculate all indicators for the full history
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))

        sma_20 = close.rolling(window=20).mean()
        sma_50 = close.rolling(window=50).mean()

        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()

        bb_middle = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)

        # Find significant price moves (>5% in 10 trading days)
        events = []
        for i in range(50, len(df) - 10):
            future_return = (float(close.iloc[i + 10]) - float(close.iloc[i])) / float(close.iloc[i]) * 100
            if abs(future_return) >= 5:
                date_str = str(dates[i].date()) if hasattr(dates[i], "date") else str(dates[i])

                # Capture indicator snapshot before the move
                rsi_val = float(rsi_series.iloc[i]) if not pd.isna(rsi_series.iloc[i]) else None
                macd_val = float(macd_line.iloc[i]) if not pd.isna(macd_line.iloc[i]) else None
                macd_sig = float(macd_signal.iloc[i]) if not pd.isna(macd_signal.iloc[i]) else None
                sma20_val = float(sma_20.iloc[i]) if not pd.isna(sma_20.iloc[i]) else None
                sma50_val = float(sma_50.iloc[i]) if not pd.isna(sma_50.iloc[i]) else None
                price_val = float(close.iloc[i])
                bb_pos = None
                if not pd.isna(bb_upper.iloc[i]) and not pd.isna(bb_lower.iloc[i]):
                    bb_range = float(bb_upper.iloc[i]) - float(bb_lower.iloc[i])
                    if bb_range > 0:
                        bb_pos = round((price_val - float(bb_lower.iloc[i])) / bb_range, 2)

                events.append({
                    "date": date_str,
                    "price": round(price_val, 2),
                    "return_10d": round(future_return, 2),
                    "direction": "up" if future_return > 0 else "down",
                    "indicators": {
                        "rsi": round(rsi_val, 1) if rsi_val else None,
                        "macd_above_signal": (macd_val > macd_sig) if macd_val and macd_sig else None,
                        "price_above_sma20": (price_val > sma20_val) if sma20_val else None,
                        "price_above_sma50": (price_val > sma50_val) if sma50_val else None,
                        "bb_position": bb_pos,
                    },
                })

        # Deduplicate events (keep max abs return within 10-day windows)
        filtered_events = []
        used_dates = set()
        sorted_events = sorted(events, key=lambda e: abs(e["return_10d"]), reverse=True)
        for ev in sorted_events:
            date_val = pd.Timestamp(ev["date"])
            too_close = False
            for used in used_dates:
                if abs((date_val - used).days) < 10:
                    too_close = True
                    break
            if not too_close:
                used_dates.add(date_val)
                filtered_events.append(ev)
            if len(filtered_events) >= 20:
                break

        filtered_events.sort(key=lambda e: e["date"])

        # Current setup
        current_rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None
        current_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None
        current_macd_sig = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None
        current_sma20 = float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None
        current_sma50 = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else None
        current_price = float(close.iloc[-1])
        current_bb_pos = None
        if not pd.isna(bb_upper.iloc[-1]) and not pd.isna(bb_lower.iloc[-1]):
            bb_range = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
            if bb_range > 0:
                current_bb_pos = round((current_price - float(bb_lower.iloc[-1])) / bb_range, 2)

        current_setup = {
            "price": round(current_price, 2),
            "rsi": round(current_rsi, 1) if current_rsi else None,
            "macd_above_signal": (current_macd > current_macd_sig) if current_macd and current_macd_sig else None,
            "price_above_sma20": (current_price > current_sma20) if current_sma20 else None,
            "price_above_sma50": (current_price > current_sma50) if current_sma50 else None,
            "bb_position": current_bb_pos,
        }

        # Find similar historical setups (pattern matching)
        patterns = []
        for ev in filtered_events:
            ind = ev["indicators"]
            similarity = 0
            checks = 0

            if current_rsi and ind["rsi"]:
                checks += 1
                if abs(current_rsi - ind["rsi"]) < 10:
                    similarity += 1
                elif abs(current_rsi - ind["rsi"]) < 20:
                    similarity += 0.5

            if ind["macd_above_signal"] is not None and current_setup["macd_above_signal"] is not None:
                checks += 1
                if ind["macd_above_signal"] == current_setup["macd_above_signal"]:
                    similarity += 1

            if ind["price_above_sma20"] is not None and current_setup["price_above_sma20"] is not None:
                checks += 1
                if ind["price_above_sma20"] == current_setup["price_above_sma20"]:
                    similarity += 1

            if ind["price_above_sma50"] is not None and current_setup["price_above_sma50"] is not None:
                checks += 1
                if ind["price_above_sma50"] == current_setup["price_above_sma50"]:
                    similarity += 1

            if ind["bb_position"] is not None and current_bb_pos is not None:
                checks += 1
                if abs(ind["bb_position"] - current_bb_pos) < 0.15:
                    similarity += 1
                elif abs(ind["bb_position"] - current_bb_pos) < 0.3:
                    similarity += 0.5

            score = (similarity / checks * 100) if checks > 0 else 0
            if score >= 40:
                patterns.append({
                    **ev,
                    "similarity": round(score, 0),
                })

        patterns.sort(key=lambda p: p["similarity"], reverse=True)

        # Summary stats from similar patterns
        if patterns:
            similar_ups = [p for p in patterns if p["direction"] == "up"]
            similar_downs = [p for p in patterns if p["direction"] == "down"]
            avg_up = sum(p["return_10d"] for p in similar_ups) / len(similar_ups) if similar_ups else 0
            avg_down = sum(p["return_10d"] for p in similar_downs) / len(similar_downs) if similar_downs else 0
            up_probability = len(similar_ups) / len(patterns) * 100
        else:
            avg_up = 0
            avg_down = 0
            up_probability = 50

        return {
            "ticker": ticker.upper(),
            "current_setup": current_setup,
            "patterns": patterns[:10],
            "events": filtered_events,
            "summary": {
                "total_similar_patterns": len(patterns),
                "up_probability": round(up_probability, 1),
                "avg_up_return": round(avg_up, 2),
                "avg_down_return": round(avg_down, 2),
            },
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "patterns": [], "current_setup": {}, "events": [], "error": str(e)}


@router.get("/analysis/{ticker}/prediction")
async def get_prediction(ticker: str) -> dict:
    """
    Comprehensive 50+ technical indicator analysis with future price prediction.
    Analyses: trend, momentum, volatility, volume, oscillators, pattern, support/resistance.
    Returns aggregated scores per category and an overall prediction.
    """
    try:
        df = StockDataService.get_stock_history(ticker, period="1y")
        if df.empty or len(df) < 60:
            return {"ticker": ticker.upper(), "error": "Insufficient data"}

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        price = float(close.iloc[-1])

        indicators = {}
        scores = {}  # each indicator → score -1 to +1

        # ═══ TREND INDICATORS ═══

        # 1-8: SMA family
        for p in [5, 10, 20, 50, 100, 200]:
            sma = close.rolling(window=p).mean()
            if not pd.isna(sma.iloc[-1]):
                val = float(sma.iloc[-1])
                indicators[f"sma_{p}"] = round(val, 2)
                scores[f"sma_{p}"] = 1.0 if price > val else -1.0

        # 9-14: EMA family
        for p in [5, 10, 12, 20, 26, 50]:
            ema = close.ewm(span=p, adjust=False).mean()
            if not pd.isna(ema.iloc[-1]):
                val = float(ema.iloc[-1])
                indicators[f"ema_{p}"] = round(val, 2)
                scores[f"ema_{p}"] = 1.0 if price > val else -1.0

        # 15: SMA 20/50 cross
        if "sma_20" in indicators and "sma_50" in indicators:
            indicators["sma_20_50_cross"] = "golden" if indicators["sma_20"] > indicators["sma_50"] else "dead"
            scores["sma_20_50_cross"] = 1.0 if indicators["sma_20"] > indicators["sma_50"] else -1.0

        # 16: SMA 50/200 cross
        if "sma_50" in indicators and "sma_200" in indicators:
            indicators["sma_50_200_cross"] = "golden" if indicators["sma_50"] > indicators["sma_200"] else "dead"
            scores["sma_50_200_cross"] = 1.0 if indicators["sma_50"] > indicators["sma_200"] else -1.0

        # 17: Price vs SMA200 distance
        if "sma_200" in indicators:
            dist = (price - indicators["sma_200"]) / indicators["sma_200"] * 100
            indicators["sma200_distance_pct"] = round(dist, 2)
            scores["sma200_distance"] = max(-1, min(1, -dist / 20))  # far above = bearish, far below = bullish

        # 18-19: DEMA, TEMA
        ema1 = close.ewm(span=20, adjust=False).mean()
        ema2 = ema1.ewm(span=20, adjust=False).mean()
        dema = 2 * ema1 - ema2
        if not pd.isna(dema.iloc[-1]):
            indicators["dema_20"] = round(float(dema.iloc[-1]), 2)
            scores["dema_20"] = 1.0 if price > float(dema.iloc[-1]) else -1.0
        ema3 = ema2.ewm(span=20, adjust=False).mean()
        tema = 3 * ema1 - 3 * ema2 + ema3
        if not pd.isna(tema.iloc[-1]):
            indicators["tema_20"] = round(float(tema.iloc[-1]), 2)
            scores["tema_20"] = 1.0 if price > float(tema.iloc[-1]) else -1.0

        # 20: Ichimoku
        nine_high = high.rolling(window=9).max()
        nine_low = low.rolling(window=9).min()
        tenkan = (nine_high + nine_low) / 2
        twentysix_high = high.rolling(window=26).max()
        twentysix_low = low.rolling(window=26).min()
        kijun = (twentysix_high + twentysix_low) / 2
        if not pd.isna(tenkan.iloc[-1]) and not pd.isna(kijun.iloc[-1]):
            indicators["ichimoku_tenkan"] = round(float(tenkan.iloc[-1]), 2)
            indicators["ichimoku_kijun"] = round(float(kijun.iloc[-1]), 2)
            scores["ichimoku_tk_cross"] = 1.0 if float(tenkan.iloc[-1]) > float(kijun.iloc[-1]) else -1.0
            scores["ichimoku_price_kijun"] = 1.0 if price > float(kijun.iloc[-1]) else -1.0

        # 22: VWAP (approximated from daily data)
        cum_vol = volume.cumsum()
        cum_pv = (close * volume).cumsum()
        vwap = cum_pv / cum_vol
        if not pd.isna(vwap.iloc[-1]) and float(cum_vol.iloc[-1]) > 0:
            indicators["vwap"] = round(float(vwap.iloc[-1]), 2)
            scores["vwap"] = 1.0 if price > float(vwap.iloc[-1]) else -1.0

        # 23: Parabolic SAR (simplified)
        psar_val = float(close.rolling(5).min().iloc[-1]) if not pd.isna(close.rolling(5).min().iloc[-1]) else None
        if psar_val:
            indicators["psar_approx"] = round(psar_val, 2)
            scores["psar"] = 1.0 if price > psar_val else -1.0

        # ═══ MOMENTUM INDICATORS ═══

        # 24-26: RSI family
        for period in [7, 14, 21]:
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss_s = (-delta.where(delta < 0, 0.0))
            avg_g = gain.rolling(window=period, min_periods=period).mean()
            avg_l = loss_s.rolling(window=period, min_periods=period).mean()
            rs = avg_g / avg_l
            rsi = 100 - (100 / (1 + rs))
            if not pd.isna(rsi.iloc[-1]):
                val = float(rsi.iloc[-1])
                indicators[f"rsi_{period}"] = round(val, 1)
                if val < 30: scores[f"rsi_{period}"] = 1.0
                elif val < 40: scores[f"rsi_{period}"] = 0.5
                elif val > 70: scores[f"rsi_{period}"] = -1.0
                elif val > 60: scores[f"rsi_{period}"] = -0.5
                else: scores[f"rsi_{period}"] = 0.0

        # 27-28: Stochastic %K, %D
        low_14 = low.rolling(window=14).min()
        high_14 = high.rolling(window=14).max()
        stoch_k = 100 * (close - low_14) / (high_14 - low_14)
        stoch_d = stoch_k.rolling(window=3).mean()
        if not pd.isna(stoch_k.iloc[-1]):
            indicators["stoch_k"] = round(float(stoch_k.iloc[-1]), 1)
            indicators["stoch_d"] = round(float(stoch_d.iloc[-1]), 1) if not pd.isna(stoch_d.iloc[-1]) else None
            sk = float(stoch_k.iloc[-1])
            if sk < 20: scores["stoch_k"] = 1.0
            elif sk > 80: scores["stoch_k"] = -1.0
            else: scores["stoch_k"] = 0.0
            # K/D cross
            if indicators["stoch_d"] is not None:
                scores["stoch_kd_cross"] = 1.0 if sk > indicators["stoch_d"] else -1.0

        # 29: Williams %R
        wr = -100 * (high_14 - close) / (high_14 - low_14)
        if not pd.isna(wr.iloc[-1]):
            val = float(wr.iloc[-1])
            indicators["williams_r"] = round(val, 1)
            if val < -80: scores["williams_r"] = 1.0
            elif val > -20: scores["williams_r"] = -1.0
            else: scores["williams_r"] = 0.0

        # 30: MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - macd_signal
        if not pd.isna(macd_line.iloc[-1]):
            indicators["macd"] = round(float(macd_line.iloc[-1]), 4)
            indicators["macd_signal"] = round(float(macd_signal.iloc[-1]), 4)
            indicators["macd_histogram"] = round(float(macd_hist.iloc[-1]), 4)
            scores["macd_cross"] = 1.0 if float(macd_line.iloc[-1]) > float(macd_signal.iloc[-1]) else -1.0
            # 31: MACD histogram trend
            hist_3 = macd_hist.iloc[-3:]
            if len(hist_3) == 3 and all(not pd.isna(v) for v in hist_3):
                if float(hist_3.iloc[2]) > float(hist_3.iloc[1]) > float(hist_3.iloc[0]):
                    scores["macd_hist_trend"] = 1.0
                elif float(hist_3.iloc[2]) < float(hist_3.iloc[1]) < float(hist_3.iloc[0]):
                    scores["macd_hist_trend"] = -1.0
                else:
                    scores["macd_hist_trend"] = 0.0

        # 32: CCI (Commodity Channel Index)
        tp = (high + low + close) / 3
        cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
        if not pd.isna(cci.iloc[-1]):
            val = float(cci.iloc[-1])
            indicators["cci"] = round(val, 1)
            if val < -100: scores["cci"] = 1.0
            elif val > 100: scores["cci"] = -1.0
            else: scores["cci"] = val / 200  # mild signal

        # 33: MFI (Money Flow Index)
        tp_s = (high + low + close) / 3
        raw_mf = tp_s * volume
        mf_sign = tp_s.diff().apply(lambda x: 1 if x > 0 else -1)
        pos_mf = (raw_mf * (mf_sign == 1)).rolling(14).sum()
        neg_mf = (raw_mf * (mf_sign == -1)).rolling(14).sum()
        mfi = 100 - (100 / (1 + pos_mf / neg_mf.replace(0, 1)))
        if not pd.isna(mfi.iloc[-1]):
            val = float(mfi.iloc[-1])
            indicators["mfi"] = round(val, 1)
            if val < 20: scores["mfi"] = 1.0
            elif val > 80: scores["mfi"] = -1.0
            else: scores["mfi"] = 0.0

        # 34-36: Rate of Change
        for p in [5, 10, 20]:
            if len(close) > p:
                roc = (float(close.iloc[-1]) - float(close.iloc[-1-p])) / float(close.iloc[-1-p]) * 100
                indicators[f"roc_{p}"] = round(roc, 2)
                scores[f"roc_{p}"] = max(-1, min(1, roc / 10))

        # 37: Momentum (10-period)
        if len(close) > 10:
            mom = float(close.iloc[-1]) - float(close.iloc[-11])
            indicators["momentum_10"] = round(mom, 2)
            scores["momentum_10"] = 1.0 if mom > 0 else -1.0

        # 38: Ultimate Oscillator
        bp = close - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        tr_uo = pd.concat([high, close.shift(1)], axis=1).max(axis=1) - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        avg7 = bp.rolling(7).sum() / tr_uo.rolling(7).sum()
        avg14 = bp.rolling(14).sum() / tr_uo.rolling(14).sum()
        avg28 = bp.rolling(28).sum() / tr_uo.rolling(28).sum()
        uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
        if not pd.isna(uo.iloc[-1]):
            val = float(uo.iloc[-1])
            indicators["ultimate_oscillator"] = round(val, 1)
            if val < 30: scores["ultimate_osc"] = 1.0
            elif val > 70: scores["ultimate_osc"] = -1.0
            else: scores["ultimate_osc"] = 0.0

        # ═══ VOLATILITY INDICATORS ═══

        # 39-40: Bollinger Bands
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        if not pd.isna(bb_upper.iloc[-1]):
            bb_range = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
            if bb_range > 0:
                bb_pos = (price - float(bb_lower.iloc[-1])) / bb_range
                indicators["bb_position"] = round(bb_pos, 2)
                indicators["bb_width"] = round(bb_range / float(bb_mid.iloc[-1]) * 100, 2)
                if bb_pos < 0.2: scores["bb_position"] = 1.0
                elif bb_pos < 0.35: scores["bb_position"] = 0.5
                elif bb_pos > 0.8: scores["bb_position"] = -1.0
                elif bb_pos > 0.65: scores["bb_position"] = -0.5
                else: scores["bb_position"] = 0.0

        # 41: ATR (Average True Range)
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        if not pd.isna(atr.iloc[-1]):
            indicators["atr"] = round(float(atr.iloc[-1]), 2)
            indicators["atr_pct"] = round(float(atr.iloc[-1]) / price * 100, 2)

        # 42: Keltner Channel
        kc_mid = close.ewm(span=20, adjust=False).mean()
        kc_upper = kc_mid + 2 * atr
        kc_lower = kc_mid - 2 * atr
        if not pd.isna(kc_upper.iloc[-1]):
            indicators["kc_upper"] = round(float(kc_upper.iloc[-1]), 2)
            indicators["kc_lower"] = round(float(kc_lower.iloc[-1]), 2)
            scores["keltner"] = 1.0 if price < float(kc_lower.iloc[-1]) else (-1.0 if price > float(kc_upper.iloc[-1]) else 0.0)

        # 43: Donchian Channel
        dc_high = high.rolling(20).max()
        dc_low = low.rolling(20).min()
        if not pd.isna(dc_high.iloc[-1]):
            indicators["donchian_high"] = round(float(dc_high.iloc[-1]), 2)
            indicators["donchian_low"] = round(float(dc_low.iloc[-1]), 2)
            dc_mid = (float(dc_high.iloc[-1]) + float(dc_low.iloc[-1])) / 2
            scores["donchian"] = 1.0 if price > dc_mid else -1.0

        # ═══ VOLUME INDICATORS ═══

        # 44: OBV trend
        obv = (volume * close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()
        obv_sma = obv.rolling(20).mean()
        if not pd.isna(obv_sma.iloc[-1]):
            scores["obv_trend"] = 1.0 if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]) else -1.0

        # 45: Volume SMA ratio
        vol_sma = volume.rolling(20).mean()
        if not pd.isna(vol_sma.iloc[-1]) and float(vol_sma.iloc[-1]) > 0:
            vol_ratio = float(volume.iloc[-1]) / float(vol_sma.iloc[-1])
            indicators["volume_ratio"] = round(vol_ratio, 2)
            price_up = float(close.iloc[-1]) > float(close.iloc[-2]) if len(close) > 1 else True
            if vol_ratio > 1.5 and price_up: scores["volume_confirm"] = 1.0
            elif vol_ratio > 1.5 and not price_up: scores["volume_confirm"] = -1.0
            else: scores["volume_confirm"] = 0.0

        # 46: Chaikin Money Flow
        mfv = ((close - low) - (high - close)) / (high - low + 1e-10) * volume
        cmf = mfv.rolling(20).sum() / volume.rolling(20).sum()
        if not pd.isna(cmf.iloc[-1]):
            val = float(cmf.iloc[-1])
            indicators["cmf"] = round(val, 4)
            scores["cmf"] = max(-1, min(1, val * 5))

        # 47: A/D line trend
        ad = ((close - low) - (high - close)) / (high - low + 1e-10) * volume
        ad_cum = ad.cumsum()
        ad_sma = ad_cum.rolling(20).mean()
        if not pd.isna(ad_sma.iloc[-1]):
            scores["ad_line"] = 1.0 if float(ad_cum.iloc[-1]) > float(ad_sma.iloc[-1]) else -1.0

        # ═══ PATTERN/STRUCTURE ═══

        # 48: 52-week high/low position
        if len(close) >= 252:
            yr_high = float(high.iloc[-252:].max())
            yr_low = float(low.iloc[-252:].min())
        else:
            yr_high = float(high.max())
            yr_low = float(low.min())
        yr_range = yr_high - yr_low
        if yr_range > 0:
            yr_pos = (price - yr_low) / yr_range
            indicators["52w_position"] = round(yr_pos * 100, 1)
            if yr_pos < 0.2: scores["52w_position"] = 1.0
            elif yr_pos < 0.35: scores["52w_position"] = 0.5
            elif yr_pos > 0.9: scores["52w_position"] = -0.5
            else: scores["52w_position"] = 0.0

        # 49: ADX (trend strength)
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        atr14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / (atr14 + 1e-10))
        minus_di = 100 * (minus_dm.rolling(14).mean() / (atr14 + 1e-10))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
        adx = dx.rolling(14).mean()
        if not pd.isna(adx.iloc[-1]):
            indicators["adx"] = round(float(adx.iloc[-1]), 1)
            indicators["plus_di"] = round(float(plus_di.iloc[-1]), 1)
            indicators["minus_di"] = round(float(minus_di.iloc[-1]), 1)
            # ADX > 25 = strong trend, direction from DI
            if float(adx.iloc[-1]) > 25:
                scores["adx"] = 1.0 if float(plus_di.iloc[-1]) > float(minus_di.iloc[-1]) else -1.0
            else:
                scores["adx"] = 0.0

        # 50: Fibonacci retracement (from recent swing)
        lookback = min(60, len(close))
        swing_high = float(high.iloc[-lookback:].max())
        swing_low = float(low.iloc[-lookback:].min())
        fib_range = swing_high - swing_low
        if fib_range > 0:
            fib_382 = swing_high - fib_range * 0.382
            fib_500 = swing_high - fib_range * 0.500
            fib_618 = swing_high - fib_range * 0.618
            indicators["fib_382"] = round(fib_382, 2)
            indicators["fib_500"] = round(fib_500, 2)
            indicators["fib_618"] = round(fib_618, 2)
            # Near support levels = bullish
            for lvl in [fib_618, fib_500, fib_382]:
                if abs(price - lvl) / price < 0.02:
                    scores["fibonacci"] = 0.5 if price >= lvl else -0.5
                    break
            else:
                scores["fibonacci"] = 0.0

        # 51: Linear regression slope (20-day)
        if len(close) >= 20:
            x = np.arange(20)
            y = close.iloc[-20:].values.astype(float)
            slope = np.polyfit(x, y, 1)[0]
            indicators["lr_slope_20"] = round(slope, 4)
            scores["lr_slope"] = max(-1, min(1, slope / (price * 0.01)))

        # 52: Standard deviation position
        std_20 = float(close.rolling(20).std().iloc[-1]) if not pd.isna(close.rolling(20).std().iloc[-1]) else None
        if std_20 and std_20 > 0:
            mean_20 = float(close.rolling(20).mean().iloc[-1])
            z_score = (price - mean_20) / std_20
            indicators["z_score"] = round(z_score, 2)
            if z_score < -2: scores["z_score"] = 1.0
            elif z_score < -1: scores["z_score"] = 0.5
            elif z_score > 2: scores["z_score"] = -1.0
            elif z_score > 1: scores["z_score"] = -0.5
            else: scores["z_score"] = 0.0

        # ═══ AGGREGATE SCORES ═══
        total_indicators = len(scores)
        if total_indicators == 0:
            return {"ticker": ticker.upper(), "error": "No indicators computed"}

        bullish = sum(1 for v in scores.values() if v > 0)
        bearish = sum(1 for v in scores.values() if v < 0)
        neutral = sum(1 for v in scores.values() if v == 0)
        avg_score = sum(scores.values()) / total_indicators

        # Category breakdowns
        categories = {
            "trend": ["sma_", "ema_", "dema", "tema", "ichimoku", "vwap", "psar", "lr_slope"],
            "momentum": ["rsi_", "stoch_", "williams", "macd", "cci", "mfi", "roc_", "momentum", "ultimate"],
            "volatility": ["bb_", "keltner", "donchian", "z_score", "atr"],
            "volume": ["obv", "volume_", "cmf", "ad_line"],
            "structure": ["52w_", "fibonacci", "adx", "sma200_distance"],
        }

        category_scores = {}
        for cat, prefixes in categories.items():
            cat_scores = []
            for k, v in scores.items():
                if any(k.startswith(p) or p in k for p in prefixes):
                    cat_scores.append(v)
            if cat_scores:
                category_scores[cat] = {
                    "score": round(sum(cat_scores) / len(cat_scores) * 100, 1),
                    "bullish": sum(1 for v in cat_scores if v > 0),
                    "bearish": sum(1 for v in cat_scores if v < 0),
                    "neutral": sum(1 for v in cat_scores if v == 0),
                    "total": len(cat_scores),
                }

        # Overall prediction
        overall_score = round(avg_score * 100, 1)  # -100 to +100
        if overall_score >= 40: prediction = "strong_buy"
        elif overall_score >= 15: prediction = "buy"
        elif overall_score <= -40: prediction = "strong_sell"
        elif overall_score <= -15: prediction = "sell"
        else: prediction = "neutral"

        # Confidence based on agreement
        agreement = max(bullish, bearish) / total_indicators * 100
        confidence = round(agreement, 1)

        # Price targets (simple projection based on ATR and score direction)
        atr_val = indicators.get("atr", price * 0.02)
        if avg_score > 0:
            target_1w = round(price + atr_val * avg_score * 3, 2)
            target_1m = round(price + atr_val * avg_score * 8, 2)
        else:
            target_1w = round(price + atr_val * avg_score * 3, 2)
            target_1m = round(price + atr_val * avg_score * 8, 2)
        stop_loss = round(price - atr_val * 2, 2)

        return {
            "ticker": ticker.upper(),
            "price": round(price, 2),
            "prediction": prediction,
            "overall_score": overall_score,
            "confidence": confidence,
            "total_indicators": total_indicators,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "categories": category_scores,
            "targets": {
                "target_1w": target_1w,
                "target_1m": target_1m,
                "stop_loss": stop_loss,
            },
            "key_indicators": indicators,
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


@router.get("/analysis/{ticker}/move-reasons")
async def get_move_reasons(ticker: str, period: str = "3mo") -> dict:
    """
    Find significant price moves and attempt to find news/reasons for each.
    Returns big moves with potential catalysts from news search.
    """
    cache_key = f"move-reasons:{ticker}:{period}"
    cached = _get_cached_ttl(cache_key, 300)
    if cached is not None:
        return cached

    try:
        df = StockDataService.get_stock_history(ticker, period=period)
        if df.empty or len(df) < 5:
            return {"ticker": ticker.upper(), "moves": []}

        close = df["Close"]
        volume_s = df["Volume"]
        vol_sma = volume_s.rolling(10).mean()

        # Pre-fetch ticker info and news ONCE (not per-move)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            name = info.get("shortName", ticker).split(" ")[0]
        except Exception:
            name = ticker

        all_articles = []
        try:
            all_articles = NewsCrawlerService.get_sector_news(name)
        except Exception:
            pass

        moves = []
        for i in range(1, len(df)):
            pct = (float(close.iloc[i]) - float(close.iloc[i-1])) / float(close.iloc[i-1]) * 100
            if abs(pct) < 2.5:
                continue
            date_str = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            vol_ratio = float(volume_s.iloc[i]) / float(vol_sma.iloc[i]) if not pd.isna(vol_sma.iloc[i]) and float(vol_sma.iloc[i]) > 0 else 1.0

            # Match pre-fetched news to this date
            reasons = []
            for art in all_articles:
                if art.published_at and date_str[:7] in art.published_at:
                    reasons.append(art.title)

            issue_category, issue_summary = _summarize_move_issue(reasons, pct, vol_ratio)

            # Classify the move type
            if pct > 5:
                move_type = "급등"
                reason_guess = issue_summary if reasons else "단기 실적/수급 기대가 강하게 반영된 구간"
            elif pct > 2.5:
                move_type = "상승"
                reason_guess = issue_summary if reasons else "섹터 모멘텀 또는 수급 개선이 반영된 구간"
            elif pct < -5:
                move_type = "급락"
                reason_guess = issue_summary if reasons else "실적/가이던스 실망 또는 악재가 반영된 구간"
            else:
                move_type = "하락"
                reason_guess = issue_summary if reasons else "차익실현 또는 업황 조정이 반영된 구간"

            # Add context about volume
            vol_note = ""
            if vol_ratio > 2.0:
                vol_note = "거래량 폭증"
            elif vol_ratio > 1.5:
                vol_note = "거래량 증가"

            moves.append({
                "date": date_str,
                "change_pct": round(pct, 2),
                "price": round(float(close.iloc[i]), 2),
                "volume_ratio": round(vol_ratio, 2),
                "move_type": move_type,
                "reason": reason_guess,
                "issue_category": issue_category,
                "issue_summary": issue_summary,
                "vol_note": vol_note,
                "news": reasons[:3],
            })

        # Keep top moves by magnitude — more for longer periods
        moves.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
        limit = 25 if period in ("1y", "2y", "5y", "max") else 15
        response = {"ticker": ticker.upper(), "moves": moves[:limit]}
        _set_cached(cache_key, response)
        return response

    except Exception as e:
        return {"ticker": ticker.upper(), "moves": [], "error": str(e)}


# ── Static checklist data sources per ticker ──

def ck(
    item: str,
    typ: str,
    *,
    metric: str | None = None,
    symbol: str | None = None,
    positive_if: str,
    threshold: float | None = None,
    weight: int = 60,
    thesis: str = "",
    window: str = "향후 1~3개월",
) -> dict:
    result = {
        "item": item,
        "type": typ,
        "positive_if": positive_if,
        "weight": weight,
        "thesis": thesis,
        "window": window,
    }
    if metric is not None:
        result["metric"] = metric
    if symbol is not None:
        result["symbol"] = symbol
    if threshold is not None:
        result["threshold"] = threshold
    return result

CHECKLIST_SOURCES = {
    "NVDA": [
        ck("데이터센터 매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=95, thesis="NVDA는 데이터센터 매출 성장률이 둔화되면 멀티플이 가장 먼저 눌리는 구조라서 최우선 선행 변수입니다.", window="향후 1~2분기"),
        ck("HBM/AI 반도체 업황 (SOXX)", "commodity", symbol="SOXX", positive_if="up", weight=85, thesis="GPU 수요와 메모리 업황 기대는 SOXX 추세에 선반영되는 경우가 많습니다.", window="향후 1~3개월"),
        ck("하이퍼스케일러 AI 캡엑스 (MSFT)", "commodity", symbol="MSFT", positive_if="up", weight=90, thesis="MSFT 같은 대형 고객 캡엑스 기대가 꺾이면 NVDA 수주 기대도 바로 약해집니다.", window="향후 1~2분기"),
        ck("빅테크 위험선호 (QQQ)", "commodity", symbol="QQQ", positive_if="up", weight=58, thesis="AI 대장주 프리미엄은 빅테크 위험선호가 꺾일 때 먼저 압박받습니다.", window="향후 1~2개월"),
        ck("경쟁사 상대강도 (AMD)", "commodity", symbol="AMD", positive_if="down", weight=70, thesis="AMD가 빠르게 강해지면 NVDA 독점 프리미엄이 약해질 수 있어 상대 강도를 같이 봐야 합니다.", window="향후 1~3개월"),
        ck("공급망 병목/원가 (구리)", "commodity", symbol="HG=F", positive_if="stable", weight=45, thesis="구리 급등은 AI 인프라 확장 비용을 높이고 공급망 긴장을 키울 수 있습니다.", window="향후 1~2개월"),
        ck("영업이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.28, weight=88, thesis="고마진 유지 여부가 NVDA의 초과 프리미엄 지속성을 결정합니다.", window="향후 1~2분기"),
        ck("밸류 부담 점검 (Forward P/E 프록시 P/B)", "earnings_metric", metric="price_to_book", positive_if="below", threshold=55.0, weight=42, thesis="실적 성장보다 밸류가 너무 앞서가면 좋은 업황에서도 조정 폭이 커질 수 있습니다.", window="향후 1~2개월"),
    ],
    "TSM": [
        ck("웨이퍼/파운드리 수요 (SOXX)", "commodity", symbol="SOXX", positive_if="up", weight=85, thesis="TSMC는 최상단 AI 수요가 계속 강해야 가동률과 ASP를 유지할 수 있습니다.", window="향후 1~3개월"),
        ck("핵심 고객 수요 (NVDA)", "commodity", symbol="NVDA", positive_if="up", weight=82, thesis="주요 팹리스 고객의 주가와 기대감은 TSM 수요 선행지표 역할을 합니다.", window="향후 1~3개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.08, weight=90, thesis="월별 매출과 분기 성장률 둔화는 파운드리 밸류에이션 조정으로 바로 이어집니다.", window="향후 1~2분기"),
        ck("원가 안정성 (구리)", "commodity", symbol="HG=F", positive_if="stable", weight=40, thesis="원재료 급등은 첨단 공정 확장 비용을 높여 마진 압박 요인이 됩니다.", window="향후 1~2개월"),
        ck("TWD 환율", "commodity", symbol="TWD=X", positive_if="down", weight=60, thesis="대만달러 강세가 심해지면 수출 경쟁력과 마진 기대가 일부 훼손될 수 있습니다.", window="향후 1~3개월"),
        ck("영업이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.35, weight=88, thesis="TSMC 프리미엄은 높은 수율과 마진에서 나오므로 영업이익률 유지가 핵심입니다.", window="향후 1~2분기"),
    ],
    "AVGO": [
        ck("AI 네트워킹 수요 (SOXX)", "commodity", symbol="SOXX", positive_if="up", weight=78, thesis="AVGO는 AI 네트워킹과 커스텀칩 모멘텀이 꺾이면 성장 기대가 빠르게 낮아집니다.", window="향후 1~3개월"),
        ck("빅테크 고객 기대 (GOOG)", "commodity", symbol="GOOG", positive_if="up", weight=66, thesis="커스텀 AI칩 기대는 대형 고객 투자 심리와 맞물려 선반영됩니다.", window="향후 1~3개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=82, thesis="매출 성장률이 두 자릿수를 유지해야 AI 프리미엄과 VMware 재평가가 유지됩니다.", window="향후 1~2분기"),
        ck("배당수익률", "earnings_metric", metric="dividend_yield", positive_if="above", threshold=0.01, weight=35, thesis="AVGO는 성장주이면서 배당주의 성격도 있어 배당 매력 약화 여부를 봐야 합니다.", window="향후 2~4분기"),
        ck("VMware 통합 시너지 (영업이익률)", "earnings_metric", metric="operating_margin", positive_if="above", threshold=0.32, weight=88, thesis="통합 시너지가 실제 이익률로 나타나지 않으면 인수 프리미엄이 빠르게 사라집니다.", window="향후 1~3분기"),
    ],
    "000660.KS": [
        ck("메모리 사이클 프록시 (MU)", "commodity", symbol="MU", positive_if="up", weight=92, thesis="하이닉스는 DRAM 업황 기대가 실적보다 먼저 주가에 반영되므로 메모리 피어 추세가 매우 중요합니다.", window="향후 1~3개월"),
        ck("HBM/AI 반도체 업황 (SOXX)", "commodity", symbol="SOXX", positive_if="up", weight=80, thesis="HBM 수요 강도와 AI 서버 사이클이 유지돼야 HBM 프리미엄이 유지됩니다.", window="향후 1~3개월"),
        ck("핵심 고객 기대 (NVDA)", "commodity", symbol="NVDA", positive_if="up", weight=84, thesis="NVDA 기대가 꺾이면 하이닉스 HBM 공급 프리미엄도 먼저 흔들립니다.", window="향후 1~2개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.12, weight=88, thesis="메모리 업황 턴어라운드가 실제 매출 성장으로 이어지는지 확인하는 핵심 항목입니다.", window="향후 1~2분기"),
        ck("영업이익률 추이", "earnings_metric", metric="operating_margin", positive_if="above", threshold=0.12, weight=95, thesis="메모리주는 이익률 피크아웃 신호가 나오면 주가가 가장 먼저 꺾이는 경향이 있습니다.", window="향후 1~2분기"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=55, thesis="원화 약세는 수출주인 하이닉스의 원화 환산 실적에 우호적입니다.", window="향후 1~3개월"),
        ck("구리 가격", "commodity", symbol="HG=F", positive_if="up", weight=40, thesis="산업 전반의 AI 서버/전자 수요가 강하면 구리도 같이 강해지는 경우가 많습니다.", window="향후 1~2개월"),
        ck("밸류 부담 점검 (P/B)", "earnings_metric", metric="price_to_book", positive_if="below", threshold=3.0, weight=38, thesis="업황은 좋아도 밸류가 너무 앞서가면 메모리주는 변동성이 커질 수 있습니다.", window="향후 1~2개월"),
    ],
    "005930.KS": [
        ck("메모리 업황 프록시 (MU)", "commodity", symbol="MU", positive_if="up", weight=88, thesis="삼성전자도 메모리 업황 기대가 주가를 먼저 움직이는 비중이 높습니다.", window="향후 1~3개월"),
        ck("반도체/AI 업황 (SOXX)", "commodity", symbol="SOXX", positive_if="up", weight=76, thesis="HBM, 파운드리, 모바일 반도체 심리 전반을 같이 확인해야 합니다.", window="향후 1~3개월"),
        ck("핵심 고객/AI 체인 (NVDA)", "commodity", symbol="NVDA", positive_if="up", weight=62, thesis="삼성 HBM 기대 역시 AI 체인 전체 심리와 함께 움직이는 비중이 큽니다.", window="향후 1~2개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.06, weight=75, thesis="메모리 업황 회복이 실제 외형 성장으로 전환되는지 확인하는 기본 축입니다.", window="향후 1~2분기"),
        ck("영업이익률", "earnings_metric", metric="operating_margin", positive_if="above", threshold=0.1, weight=92, thesis="삼성은 HBM/파운드리 개선 기대가 이익률로 나타나야 주가가 유지됩니다.", window="향후 1~2분기"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=50, thesis="원화 약세는 삼성전자 수출 채산성에 우호적입니다.", window="향후 1~3개월"),
        ck("밸류 부담 점검 (P/B)", "earnings_metric", metric="price_to_book", positive_if="below", threshold=2.2, weight=35, thesis="대형주는 업황 회복 기대가 커도 밸류 부담이 커지면 상단이 제한될 수 있습니다.", window="향후 1~2개월"),
    ],
    "TSLA": [
        ck("차량 인도/매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.08, weight=88, thesis="TSLA는 인도량과 매출 성장 둔화가 확인되면 기대감이 먼저 무너집니다.", window="향후 1~2분기"),
        ck("배터리 원가 (리튬 ETF)", "commodity", symbol="LIT", positive_if="down", weight=72, thesis="리튬 및 배터리 체인 부담이 커지면 마진 회복 기대가 약해집니다.", window="향후 1~3개월"),
        ck("이익률 추이", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.07, weight=95, thesis="TSLA는 매출보다 자동차/에너지 마진 방향이 주가를 더 크게 좌우합니다.", window="향후 1~2분기"),
        ck("EV 섹터 심리 (DRIV)", "commodity", symbol="DRIV", positive_if="up", weight=70, thesis="EV 밸류체인 심리가 꺾이면 TSLA의 프리미엄도 같이 압축됩니다.", window="향후 1~3개월"),
        ck("에너지 저장 기대 (ICLN)", "commodity", symbol="ICLN", positive_if="up", weight=55, thesis="에너지저장 사업이 TSLA 밸류 재평가의 보조축이기 때문에 클린에너지 흐름도 봐야 합니다.", window="향후 1~3개월"),
    ],
    "ISRG": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=80, thesis="수술 건수와 시스템 설치가 유지돼야 프리미엄이 유지됩니다.", window="향후 1~2분기"),
        ck("이익률 추이", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.18, weight=86, thesis="ISRG는 고품질 장비주라 이익률 유지가 특히 중요합니다.", window="향후 1~2분기"),
        ck("헬스케어 섹터 (XLV)", "commodity", symbol="XLV", positive_if="up", weight=42, thesis="방어적 대형 헬스케어 심리는 장비주에도 보조적으로 작용합니다.", window="향후 1~3개월"),
        ck("ROE", "earnings_metric", metric="roe", positive_if="above", threshold=0.15, weight=58, thesis="자본 효율이 흔들리면 장기 프리미엄이 약해집니다.", window="향후 2~4분기"),
    ],
    "CEG": [
        ck("우라늄 가격 (URA)", "commodity", symbol="URA", positive_if="up", weight=70, thesis="원전 체인 기대는 우라늄 가격 흐름과 같이 움직이는 비중이 큽니다.", window="향후 1~3개월"),
        ck("천연가스 가격", "commodity", symbol="NG=F", positive_if="up", weight=54, thesis="가스 가격 강세는 원전의 상대 경제성을 높입니다.", window="향후 1~2개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=76, thesis="전력 계약과 수요 확대가 실제 외형 성장으로 이어져야 합니다.", window="향후 1~2분기"),
        ck("전력수요 (유틸리티 XLU)", "commodity", symbol="XLU", positive_if="up", weight=78, thesis="유틸리티 수요 기대가 살아야 전력 공급 가치가 더 부각됩니다.", window="향후 1~3개월"),
    ],
    "CCJ": [
        ck("우라늄 가격 (URA)", "commodity", symbol="URA", positive_if="up", weight=96, thesis="CCJ는 우라늄 가격 기대를 가장 직접적으로 반영합니다.", window="향후 1~3개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=72, thesis="가격 상승 기대가 매출로 확인돼야 랠리가 유지됩니다.", window="향후 1~2분기"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.08, weight=78, thesis="원자재 랠리에서 중요한 것은 가격보다 이익률 확장입니다.", window="향후 1~2분기"),
    ],
    "CRWD": [
        ck("ARR/매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.2, weight=90, thesis="CRWD는 ARR 성장 둔화가 보이면 고밸류가 빠르게 압축될 수 있습니다.", window="향후 1~2분기"),
        ck("사이버보안 섹터 (BUG)", "commodity", symbol="BUG", positive_if="up", weight=72, thesis="섹터 전체 심리 둔화는 개별 기업 실적과 무관하게 멀티플 압박을 만듭니다.", window="향후 1~3개월"),
        ck("이익률 추이", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.05, weight=82, thesis="성장주에서 이익률까지 개선돼야 플랫폼 프리미엄이 유지됩니다.", window="향후 1~2분기"),
    ],
    "CRSP": [
        ck("바이오텍 섹터 (XBI)", "commodity", symbol="XBI", positive_if="up", weight=76, thesis="CRSP는 바이오 위험선호가 꺼지면 임상 기대도 빠르게 할인됩니다.", window="향후 1~3개월"),
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.0, weight=62, thesis="상업화 초기 바이오는 매출 인식이 시작되는지 자체가 중요합니다.", window="향후 1~2분기"),
        ck("현금 보유 (P/B)", "earnings_metric", metric="price_to_book", positive_if="below", threshold=10.0, weight=84, thesis="현금 런웨이 우려가 커지면 임상 기대보다 자금조달 이슈가 먼저 부각됩니다.", window="향후 1~2분기"),
    ],
    "LLY": [
        ck("GLP-1 매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=92, thesis="LLY는 비만약 성장 기대가 멀티플 핵심이라 매출 성장 둔화가 가장 치명적입니다.", window="향후 1~2분기"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.18, weight=80, thesis="수요 확대가 실제 이익률로 이어져야 비만약 프리미엄이 유지됩니다.", window="향후 1~2분기"),
        ck("바이오 섹터 심리 (IBB)", "commodity", symbol="IBB", positive_if="up", weight=45, thesis="대형 바이오 전반의 선호가 꺾이면 LLY도 일부 밸류 부담이 커집니다.", window="향후 1~3개월"),
        ck("경쟁사 상대강도 (NVO)", "commodity", symbol="NVO", positive_if="down", weight=68, thesis="NVO 강세가 계속되면 GLP-1 경쟁 구도에서 LLY 기대가 상대적으로 약해질 수 있습니다.", window="향후 1~3개월"),
    ],
    "IONQ": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.25, weight=86, thesis="IONQ는 실적 절대값보다 성장률 유지 여부가 기대감 유지의 핵심입니다.", window="향후 1~2분기"),
        ck("양자컴퓨팅 심리 (QTUM)", "commodity", symbol="QTUM", positive_if="up", weight=74, thesis="양자 섹터는 기대감 장세 비중이 커서 ETF 흐름이 개별주에 직접 반영됩니다.", window="향후 1~3개월"),
        ck("현금 소진/수익성", "earnings_metric", metric="profit_margin", positive_if="above", threshold=-0.5, weight=92, thesis="적자 폭이 다시 확대되면 기술 기대보다 자금 조달 우려가 먼저 커집니다.", window="향후 1~2분기"),
    ],
    "RKLB": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.2, weight=88, thesis="우주주는 수주와 시스템 매출 성장 둔화가 확인되면 스토리가 쉽게 꺾입니다.", window="향후 1~2분기"),
        ck("우주산업 심리 (UFO)", "commodity", symbol="UFO", positive_if="up", weight=75, thesis="우주 섹터 위험 선호가 줄면 RKLB 같은 성장주는 가장 먼저 조정받기 쉽습니다.", window="향후 1~3개월"),
        ck("방산/정부 수요 (ITA)", "commodity", symbol="ITA", positive_if="up", weight=55, thesis="정부 및 국방 수요 기대가 우주 인프라 투자 심리를 보조합니다.", window="향후 1~3개월"),
    ],
    "BE": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.12, weight=78, thesis="BE는 데이터센터/분산전원 수주가 실제 매출로 이어지는지 확인이 필요합니다.", window="향후 1~2분기"),
        ck("클린에너지 심리 (ICLN)", "commodity", symbol="ICLN", positive_if="up", weight=60, thesis="클린에너지 기대감이 꺾이면 수익성 개선 전 단계 기업들은 더 민감하게 흔들립니다.", window="향후 1~3개월"),
        ck("이익률 (흑자전환)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=94, thesis="BE는 흑자전환이 확인돼야 장기 스토리가 아닌 실제 사업 전환으로 인정받습니다.", window="향후 1~2분기"),
        ck("촉매/원가 (백금)", "commodity", symbol="PL=F", positive_if="up", weight=35, thesis="수소/연료전지 체인 기대감과 원가 구조를 동시에 보여주는 참고 지표입니다.", window="향후 1~3개월"),
    ],
    # ── 로봇 섹터 추가 ──
    "454910.KS": [
        ck("협동로봇 매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=84, thesis="두산로보틱스는 설치 대수 확대가 실제 매출 성장으로 이어지는지가 핵심입니다.", window="향후 1~2분기"),
        ck("로봇 자동화 심리 (ROBO)", "commodity", symbol="ROBO", positive_if="up", weight=70, thesis="글로벌 로봇 자동화 멀티플이 살아 있어야 고성장 프리미엄이 유지됩니다.", window="향후 1~3개월"),
        ck("수주잔고의 매출화 (이익률)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=90, thesis="협동로봇주는 흑자전환 신뢰가 생겨야 주가가 한 단계 올라갑니다.", window="향후 1~2분기"),
        ck("현대차/대기업 도입 확산", "commodity", symbol="005380.KS", positive_if="up", weight=62, thesis="국내 대기업 자동화 투자 확대가 두산로보틱스 기대를 직접 자극합니다.", window="향후 1~3개월"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=42, thesis="해외 매출 확대 구간에서는 원화 약세가 채산성에 우호적입니다.", window="향후 1~2개월"),
    ],
    "FANUY": [
        ck("산업용 로봇 주문 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=76, thesis="FANUC은 공장 자동화 CAPEX 회복이 수주로 먼저 보입니다.", window="향후 1~2분기"),
        ck("글로벌 자동화 심리 (ROBO)", "commodity", symbol="ROBO", positive_if="up", weight=66, thesis="중국·미국 제조업 자동화 사이클이 살아야 멀티플이 유지됩니다.", window="향후 1~3개월"),
        ck("고이익률 유지", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=82, thesis="FANUC의 프리미엄은 높은 마진과 현금창출력에서 나옵니다.", window="향후 1~2분기"),
        ck("엔화 약세", "commodity", symbol="JPY=X", positive_if="down", weight=58, thesis="엔화 약세는 수출형 일본 자동화 업체의 가격 경쟁력을 높입니다.", window="향후 1~3개월"),
        ck("산업재 수요 (XLI)", "commodity", symbol="XLI", positive_if="up", weight=48, thesis="글로벌 산업재 CAPEX 흐름을 함께 봐야 합니다.", window="향후 1~3개월"),
    ],
    "267250.KS": [
        ck("산업용 로봇 매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=78, thesis="현대로보틱스는 그룹 CAPEX와 외부 고객 확대가 동시에 필요합니다.", window="향후 1~2분기"),
        ck("현대차 그룹 자동화 수혜", "commodity", symbol="005380.KS", positive_if="up", weight=74, thesis="현대차 설비 투자와 스마트팩토리 확대가 직접 수혜 변수입니다.", window="향후 1~3개월"),
        ck("흑자전환/이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=88, thesis="국내 로봇주는 적자 축소보다 흑자전환 확인이 더 중요합니다.", window="향후 1~2분기"),
        ck("로봇 자동화 심리 (ROBO)", "commodity", symbol="ROBO", positive_if="up", weight=52, thesis="국내 종목이라도 글로벌 자동화 멀티플 흐름을 무시하기 어렵습니다.", window="향후 1~3개월"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=40, thesis="수출 프로젝트 확대 구간에서 원화 약세가 우호적입니다.", window="향후 1~2개월"),
    ],
    # ── 원자력 섹터 추가 ──
    "BWXT": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=70, thesis="원전/방산 수주가 실제 외형 성장으로 이어지는지 확인해야 합니다.", window="향후 1~2분기"),
        ck("우라늄 (URA ETF)", "commodity", symbol="URA", positive_if="up", weight=60, thesis="원전 체인 심리가 BWXT에도 보조적으로 반영됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=74, thesis="안정적 방산형 비즈니스는 이익률 유지가 중요합니다.", window="향후 1~2분기"),
        ck("방산 (ITA ETF)", "commodity", symbol="ITA", positive_if="up", weight=72, thesis="방산 수요와 정부 예산 기대가 유지돼야 합니다.", window="향후 1~3개월"),
    ],
    "034020.KS": [
        ck("원전 기자재 매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=74, thesis="두산에너빌리티는 체코·중동 원전 수주가 매출로 전환되는지가 핵심입니다.", window="향후 1~2분기"),
        ck("K-원전 수출 기대 (URA)", "commodity", symbol="URA", positive_if="up", weight=54, thesis="글로벌 원전 심리가 살아야 국내 원전 기자재 프리미엄도 유지됩니다.", window="향후 1~3개월"),
        ck("흑자 체력/이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=82, thesis="수주만 많고 이익률이 약하면 밸류에이션이 버티기 어렵습니다.", window="향후 1~2분기"),
        ck("한전 정상화 기대", "commodity", symbol="015760.KS", positive_if="up", weight=68, thesis="국내 원전 밸류체인의 정책/발주 기대는 한전 정상화와 맞물립니다.", window="향후 1~3개월"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=44, thesis="원전 수출 프로젝트 확대 시 원화 약세가 채산성에 유리합니다.", window="향후 1~2개월"),
    ],
    "015760.KS": [
        ck("전기요금/매출 회복", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.0, weight=70, thesis="한전은 판매량보다 요금 체계 정상화가 주가에 더 중요합니다.", window="향후 1~2분기"),
        ck("유틸리티 멀티플 (XLU)", "commodity", symbol="XLU", positive_if="up", weight=52, thesis="금리와 방어주 선호가 유틸리티 밸류를 좌우합니다.", window="향후 1~3개월"),
        ck("흑자전환/이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=92, thesis="한전은 적자 축소보다 흑자전환 지속성이 가장 중요합니다.", window="향후 1~2분기"),
        ck("연료비 부담 (천연가스)", "commodity", symbol="NG=F", positive_if="down", weight=86, thesis="천연가스 하락은 한전 연료비 부담 완화에 직접적입니다.", window="향후 1~2개월"),
        ck("원전 체인 심리 (URA)", "commodity", symbol="URA", positive_if="up", weight=38, thesis="원전 정상화 정책 기대를 보조적으로 확인합니다.", window="향후 1~3개월"),
    ],
    # ── 사이버보안 섹터 추가 ──
    "PANW": [
        ck("매출 성장률 (ARR)", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=86, thesis="PANW도 플랫폼 성장률 둔화가 멀티플에 직접 반영됩니다.", window="향후 1~2분기"),
        ck("사이버보안 (BUG ETF)", "commodity", symbol="BUG", positive_if="up", weight=70, thesis="섹터 심리가 살아야 대형 보안주 프리미엄도 유지됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=76, thesis="플랫폼 확장과 수익성 개선이 동시에 필요합니다.", window="향후 1~2분기"),
        ck("경쟁사 CRWD 추이", "commodity", symbol="CRWD", positive_if="down", weight=62, thesis="리더십이 CRWD로 쏠리면 상대적 매력이 낮아질 수 있습니다.", window="향후 1~2개월"),
    ],
    "FTNT": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=72, thesis="FTNT는 수익성뿐 아니라 최소한의 성장 유지가 필요합니다.", window="향후 1~2분기"),
        ck("사이버보안 (BUG ETF)", "commodity", symbol="BUG", positive_if="up", weight=66, thesis="섹터 위험선호가 식으면 가치매력만으로 버티기 어렵습니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.15, weight=80, thesis="FTNT는 고이익률 유지가 차별점입니다.", window="향후 1~2분기"),
    ],
    "ZS": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.25, weight=90, thesis="ZS는 초고성장 스토리가 유지돼야 합니다.", window="향후 1~2분기"),
        ck("사이버보안 (BUG ETF)", "commodity", symbol="BUG", positive_if="up", weight=65, thesis="고성장 보안주 선호가 식으면 ZS가 더 민감합니다.", window="향후 1~3개월"),
        ck("이익률 (흑자전환)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=82, thesis="성장만이 아니라 흑자전환 신뢰가 필요합니다.", window="향후 1~2분기"),
    ],
    "S": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.3, weight=92, thesis="SentinelOne은 고성장 스토리가 핵심입니다.", window="향후 1~2분기"),
        ck("사이버보안 (BUG ETF)", "commodity", symbol="BUG", positive_if="up", weight=62, thesis="고위험 성장주라 섹터 심리 영향을 크게 받습니다.", window="향후 1~3개월"),
        ck("이익률 (적자폭)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=-0.2, weight=88, thesis="적자 축소가 멈추면 자금조달 우려가 먼저 커질 수 있습니다.", window="향후 1~2분기"),
    ],
    # ── 우주항공 섹터 추가 ──
    "LMT": [
        ck("방산/우주 매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.03, weight=68, thesis="Lockheed는 대형 프로그램 매출 인식이 안정적으로 이어져야 합니다.", window="향후 1~2분기"),
        ck("방산 예산 심리 (ITA)", "commodity", symbol="ITA", positive_if="up", weight=74, thesis="방산 예산과 업종 멀티플이 안정적이어야 합니다.", window="향후 1~3개월"),
        ck("고이익률 유지", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=76, thesis="대형 방산주는 마진 안정성이 핵심입니다.", window="향후 1~2분기"),
        ck("배당 매력", "earnings_metric", metric="dividend_yield", positive_if="above", threshold=0.02, weight=40, thesis="LMT는 배당 방어력도 중요한 투자 포인트입니다.", window="향후 2~4분기"),
        ck("우주 옵션 (UFO)", "commodity", symbol="UFO", positive_if="up", weight=34, thesis="우주 계약 기대를 보조적으로 확인합니다.", window="향후 1~3개월"),
    ],
    "LHX": [
        ck("국방/우주 센서 매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.03, weight=68, thesis="LHX는 방산 안정성과 우주 센서 성장의 결합이 중요합니다.", window="향후 1~2분기"),
        ck("방산 예산 심리 (ITA)", "commodity", symbol="ITA", positive_if="up", weight=72, thesis="방산 예산 기대가 유지돼야 우주/국방 프리미엄도 유지됩니다.", window="향후 1~3개월"),
        ck("고이익률 유지", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.08, weight=74, thesis="LHX는 안정적 고마진 체력이 핵심입니다.", window="향후 1~2분기"),
        ck("우주산업 기대 (UFO)", "commodity", symbol="UFO", positive_if="up", weight=58, thesis="순수 우주 테마 심리 회복이 옵션 가치를 키웁니다.", window="향후 1~3개월"),
    ],
    "047810.KS": [
        ck("KF-21/완제기 매출 성장", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=84, thesis="한국항공우주는 완제기 수출과 양산 일정이 매출 성장의 핵심입니다.", window="향후 1~2분기"),
        ck("방산 수출 심리 (ITA)", "commodity", symbol="ITA", positive_if="up", weight=62, thesis="글로벌 방산 체인 강세가 국내 항공우주 프리미엄도 밀어줍니다.", window="향후 1~3개월"),
        ck("이익률 유지", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.05, weight=78, thesis="수주 증가보다 중요한 것은 양산 구간의 마진 안정화입니다.", window="향후 1~2분기"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=56, thesis="수출 비중이 높은 방산주는 원화 약세가 실적 기대를 자극합니다.", window="향후 1~2개월"),
        ck("국내 방산 체인 (LMT)", "commodity", symbol="LMT", positive_if="up", weight=40, thesis="대형 방산 심리와 정부 예산 기대를 보조적으로 확인합니다.", window="향후 1~3개월"),
    ],
    "BA": [
        ck("인도량/매출 회복", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=78, thesis="보잉은 생산 정상화와 인도량 회복이 핵심입니다.", window="향후 1~2분기"),
        ck("항공 수요 심리 (JETS)", "commodity", symbol="JETS", positive_if="up", weight=54, thesis="상업용 항공 수요 회복 기대가 유지돼야 합니다.", window="향후 1~3개월"),
        ck("흑자전환", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=92, thesis="보잉은 흑자전환 신뢰 회복이 가장 중요합니다.", window="향후 1~2분기"),
        ck("방산/우주 옵션 (ITA)", "commodity", symbol="ITA", positive_if="up", weight=50, thesis="방산·우주 사업이 상업용 항공 부진을 보완하는지 봐야 합니다.", window="향후 1~3개월"),
        ck("우주 테마 보조 심리 (UFO)", "commodity", symbol="UFO", positive_if="up", weight=30, thesis="우주 기대는 보조적이며 핵심은 규제 리스크 완화입니다.", window="향후 1~2개월"),
    ],
    # ── 바이오 섹터 추가 ──
    "ILMN": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=78, thesis="장비·서비스 수요 회복이 먼저 확인돼야 합니다.", window="향후 1~2분기"),
        ck("유전체/바이오 (XBI)", "commodity", symbol="XBI", positive_if="up", weight=54, thesis="바이오 위험선호가 회복돼야 장비주도 재평가됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=76, thesis="시퀀싱 장비주는 이익률 방어가 중요합니다.", window="향후 1~2분기"),
    ],
    "207940.KS": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=84, thesis="삼성바이오는 대형 수주가 매출로 전환되는지 확인해야 합니다.", window="향후 1~2분기"),
        ck("바이오 (IBB ETF)", "commodity", symbol="IBB", positive_if="up", weight=42, thesis="대형 바이오 심리 회복은 밸류에 보조적으로 작용합니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.15, weight=80, thesis="증설보다 중요한 것은 고마진 유지입니다.", window="향후 1~2분기"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=48, thesis="수출형 바이오 CDMO에는 환율이 유의미합니다.", window="향후 1~2개월"),
    ],
    "068270.KS": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=78, thesis="미국/유럽 판매 확대가 유지돼야 합니다.", window="향후 1~2분기"),
        ck("바이오시밀러 (IBB)", "commodity", symbol="IBB", positive_if="up", weight=40, thesis="대형 바이오 심리는 셀트리온에도 간접적으로 반영됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=82, thesis="가격 경쟁이 심한 업종이라 이익률 방어가 더 중요합니다.", window="향후 1~2분기"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=48, thesis="환율은 수출 채산성에 직접적 영향을 줍니다.", window="향후 1~2개월"),
    ],
    # ── 양자컴퓨팅 섹터 추가 ──
    "GOOG": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=74, thesis="양자 옵션 가치도 본업 성장 위에서만 의미가 있습니다.", window="향후 1~2분기"),
        ck("양자컴퓨팅 (QTUM)", "commodity", symbol="QTUM", positive_if="up", weight=38, thesis="GOOG의 양자 스토리를 보조적으로 점검합니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.2, weight=72, thesis="광고/클라우드 고마진이 AI와 양자 투자 여력을 떠받칩니다.", window="향후 1~2분기"),
        ck("빅테크 (QQQ)", "commodity", symbol="QQQ", positive_if="up", weight=58, thesis="빅테크 위험선호는 GOOG 밸류에 직접 반영됩니다.", window="향후 1~2개월"),
    ],
    "IBM": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.03, weight=62, thesis="IBM은 본업 성장의 바닥이 중요합니다.", window="향후 1~2분기"),
        ck("양자컴퓨팅 (QTUM)", "commodity", symbol="QTUM", positive_if="up", weight=42, thesis="양자 스토리의 시장 기대를 간접적으로 확인합니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.1, weight=66, thesis="현금창출력 유지가 중요합니다.", window="향후 1~2분기"),
        ck("배당수익률", "earnings_metric", metric="dividend_yield", positive_if="above", threshold=0.03, weight=38, thesis="IBM은 배당 매력도 여전히 중요한 요소입니다.", window="향후 2~4분기"),
    ],
    "RGTI": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.2, weight=70, thesis="초기 양자주는 작은 매출도 성장률이 유지되는지가 중요합니다.", window="향후 1~2분기"),
        ck("양자컴퓨팅 (QTUM)", "commodity", symbol="QTUM", positive_if="up", weight=78, thesis="Rigetti는 섹터 심리 영향을 강하게 받습니다.", window="향후 1~3개월"),
        ck("현금소진율 (이익률)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=-0.5, weight=94, thesis="자금소진 속도는 생존 가능성을 좌우합니다.", window="향후 1~2분기"),
    ],
    "MSFT": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=78, thesis="Azure와 AI 매출 기대가 핵심입니다.", window="향후 1~2분기"),
        ck("클라우드 (SKYY ETF)", "commodity", symbol="SKYY", positive_if="up", weight=64, thesis="클라우드 심리가 꺾이면 MSFT AI 프리미엄도 일부 압박받습니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.3, weight=76, thesis="대형 CAPEX 확대에도 이익률이 유지돼야 합니다.", window="향후 1~2분기"),
        ck("빅테크 (QQQ)", "commodity", symbol="QQQ", positive_if="up", weight=56, thesis="대형 기술주 위험선호는 MSFT 밸류를 좌우합니다.", window="향후 1~2개월"),
    ],
    # ── 수소 섹터 추가 ──
    "PLUG": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=72, thesis="수소 프로젝트 기대가 실제 매출 증가로 이어져야 합니다.", window="향후 1~2분기"),
        ck("클린에너지 (ICLN)", "commodity", symbol="ICLN", positive_if="up", weight=70, thesis="PLUG는 클린에너지 리스크온 장세에 강하게 연동됩니다.", window="향후 1~3개월"),
        ck("이익률 (적자폭)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=-0.3, weight=96, thesis="적자 폭 축소가 실패하면 자금조달 우려가 먼저 커집니다.", window="향후 1~2분기"),
        ck("수소 관련 (백금)", "commodity", symbol="PL=F", positive_if="up", weight=36, thesis="수소 밸류체인 기대를 보조적으로 확인합니다.", window="향후 1~2개월"),
    ],
    "ENPH": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=78, thesis="설치 수요 회복이 실적에 반영돼야 합니다.", window="향후 1~2분기"),
        ck("태양광 (TAN ETF)", "commodity", symbol="TAN", positive_if="up", weight=82, thesis="태양광 섹터 심리는 ENPH에 직접적입니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.2, weight=80, thesis="고마진 유지가 핵심 경쟁력입니다.", window="향후 1~2분기"),
        ck("클린에너지 (ICLN)", "commodity", symbol="ICLN", positive_if="up", weight=44, thesis="클린에너지 전반의 위험선호를 보조 확인합니다.", window="향후 1~3개월"),
    ],
    "005380.KS": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=72, thesis="판매량과 믹스 개선이 동시에 필요합니다.", window="향후 1~2분기"),
        ck("EV/자동차 (DRIV)", "commodity", symbol="DRIV", positive_if="up", weight=66, thesis="자동차/EV 심리 흐름이 현대차에도 빠르게 반영됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.05, weight=82, thesis="환율보다 중요한 것은 고수익 모델 믹스 유지입니다.", window="향후 1~2분기"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=54, thesis="완성차 수출주에는 환율이 중요합니다.", window="향후 1~2개월"),
    ],
    "336260.KS": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=72, thesis="프로젝트 수주가 매출로 이어져야 합니다.", window="향후 1~2분기"),
        ck("클린에너지 (ICLN)", "commodity", symbol="ICLN", positive_if="up", weight=60, thesis="수소 관련주는 클린에너지 위험선호 영향을 크게 받습니다.", window="향후 1~3개월"),
        ck("이익률 (흑자전환)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=90, thesis="흑자전환 여부가 핵심입니다.", window="향후 1~2분기"),
        ck("수소 관련 (백금)", "commodity", symbol="PL=F", positive_if="up", weight=34, thesis="수소 밸류체인 기대를 보조적으로 확인합니다.", window="향후 1~2개월"),
    ],
}


@router.get("/analysis/{ticker}/checklist-live")
async def get_checklist_live(ticker: str) -> dict:
    """
    Return live checklist data with:
    - Real price data & sparklines for each item
    - Stock price overlay for correlation visualization
    - Correlation coefficient (how much this item affects the stock)
    - Danger/safety threshold lines
    - Items sorted by importance (correlation strength)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    cache_key = f"checklist-live:{ticker}"
    cached = _get_cached_ttl(cache_key, 240)
    if cached is not None:
        return cached

    try:
        sources = CHECKLIST_SOURCES.get(ticker, CHECKLIST_SOURCES.get(ticker.replace(".KS", "").replace(".KQ", ""), []))

        # Fetch earnings data once
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        sector_id = _infer_sector_id_from_profile(ticker, info=info)
        if not sources:
            sources = _build_dynamic_checklist_sources(ticker, info=info)
        earnings_fallback = _derive_earnings_fallbacks(stock)
        earnings_data = {
            "revenue_growth": info.get("revenueGrowth") if info.get("revenueGrowth") is not None else earnings_fallback.get("revenue_growth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins") if info.get("profitMargins") is not None else earnings_fallback.get("profit_margin"),
            "operating_margin": info.get("operatingMargins") if info.get("operatingMargins") is not None else earnings_fallback.get("operating_margin"),
            "roe": info.get("returnOnEquity") if info.get("returnOnEquity") is not None else earnings_fallback.get("roe"),
            "dividend_yield": info.get("dividendYield"),
            "price_to_book": info.get("priceToBook"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
        }

        # Fetch stock's own 1-year price history for correlation analysis
        stock_hist = pd.DataFrame()
        try:
            stock_hist = stock.history(period="1y")
        except Exception:
            pass

        # Pre-fetch all commodity data in parallel (1 year for correlation)
        commodity_symbols = list(set(s["symbol"] for s in sources if s["type"] == "commodity"))
        commodity_cache = {}

        def fetch_commodity(sym):
            try:
                hist = StockDataService.get_stock_history(sym, period="1y")
                return sym, hist
            except Exception:
                return sym, pd.DataFrame()

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_commodity, sym): sym for sym in commodity_symbols}
            for future in as_completed(futures, timeout=20):
                try:
                    sym, hist = future.result(timeout=12)
                    commodity_cache[sym] = hist
                except Exception:
                    pass

        # Pre-crawl preliminary earnings from news (once per request)
        company_name = info.get("shortName") or info.get("longName") or ticker
        preliminary_earnings = {}
        try:
            preliminary_earnings = NewsCrawlerService.crawl_preliminary_earnings(company_name, ticker)
        except Exception:
            pass

        # Normalize stock price to 0-100 scale for overlay on each chart
        stock_overlay = []
        if not stock_hist.empty and len(stock_hist) > 5:
            s_min = float(stock_hist["Close"].min())
            s_max = float(stock_hist["Close"].max())
            s_range = s_max - s_min if s_max > s_min else 1.0
            step_s = max(1, len(stock_hist) // 60)
            for idx, row in stock_hist.iloc[::step_s].iterrows():
                d = str(idx.date()) if hasattr(idx, "date") else str(idx)
                stock_overlay.append({
                    "date": d,
                    "stock_price": round(float(row["Close"]), 2),
                    "stock_norm": round((float(row["Close"]) - s_min) / s_range * 100, 1),
                })

        def compute_correlation(commodity_hist: pd.DataFrame) -> float:
            """Compute Pearson correlation between commodity and stock price."""
            if stock_hist.empty or commodity_hist.empty:
                return 0.0
            try:
                # Align dates
                merged = pd.DataFrame({
                    "stock": stock_hist["Close"],
                    "commodity": commodity_hist["Close"],
                }).dropna()
                if len(merged) < 20:
                    return 0.0
                corr = float(np.corrcoef(merged["stock"].values, merged["commodity"].values)[0, 1])
                return round(corr, 3) if not np.isnan(corr) else 0.0
            except Exception:
                return 0.0

        def compute_thresholds(hist: pd.DataFrame, positive_if: str) -> dict:
            """Compute danger/safety threshold lines — tighter thresholds to catch early warning."""
            if hist.empty or len(hist) < 20:
                return {}
            try:
                closes = hist["Close"].dropna().values.astype(float)
                mean_val = float(np.mean(closes))
                std_val = float(np.std(closes))
                p25 = float(np.percentile(closes, 25))
                p75 = float(np.percentile(closes, 75))
                current = float(closes[-1])

                # Recent trend: compare last 20 days avg vs full avg
                recent_avg = float(np.mean(closes[-20:])) if len(closes) >= 20 else current
                trend_declining = recent_avg < mean_val  # recent trend is below average

                if positive_if == "up":
                    # Danger = 25th percentile (tighter than mean-std)
                    # If recent trend is already declining, raise the danger line to recent support
                    danger_line = round(max(p25, recent_avg * 0.95) if trend_declining else p25, 2)
                    safe_line = round(p75, 2)
                    danger_label = f"${danger_line} 이하 → 매도 신호"
                    safe_label = f"${safe_line} 이상 → 매수 신호"
                elif positive_if == "down":
                    # For "down is good" (e.g., competitor price, cost items)
                    danger_line = round(min(p75, recent_avg * 1.05) if not trend_declining else p75, 2)
                    safe_line = round(p25, 2)
                    danger_label = f"${danger_line} 이상 → 매도 신호"
                    safe_label = f"${safe_line} 이하 → 매수 신호"
                else:  # stable
                    danger_line = round(mean_val + std_val, 2)
                    safe_line = round(mean_val, 2)
                    danger_label = f"${danger_line} 이상 → 불안정"
                    safe_label = f"${safe_line} 부근 → 안정"

                # Trend warning
                trend_warn = ""
                if positive_if == "up" and len(closes) >= 10:
                    last5 = float(np.mean(closes[-5:]))
                    last20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else mean_val
                    if last5 < last20 * 0.97:
                        trend_warn = "최근 하락 추세 — 주의 필요"
                elif positive_if == "down" and len(closes) >= 10:
                    last5 = float(np.mean(closes[-5:]))
                    last20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else mean_val
                    if last5 > last20 * 1.03:
                        trend_warn = "최근 상승 추세 — 비용 압박"

                return {
                    "danger_line": danger_line,
                    "safe_line": safe_line,
                    "danger_label": danger_label,
                    "safe_label": safe_label,
                    "danger_dir": "below" if positive_if == "up" else "above",
                    "mean": round(mean_val, 2),
                    "current": round(current, 2),
                    "p25": round(p25, 2),
                    "p75": round(p75, 2),
                    "trend_warn": trend_warn,
                }
            except Exception:
                return {}

        results = []
        for src in sources:
            metadata = _infer_item_metadata(src)
            item = {
                "name": src["item"],
                "status": "neutral",
                "value": None,
                "detail": "",
                "trend_data": [],
                "stock_overlay": [],
                "correlation": 0.0,
                "corr_label": "",
                "thresholds": {},
                "source": "",
                "importance": 0,
                "window": metadata["window"],
                "why_it_matters": metadata["thesis"],
                "expected_condition": "",
            }

            if src["type"] == "earnings_metric":
                metric = src["metric"]
                val = earnings_data.get(metric)
                if val is not None:
                    threshold = src.get("threshold", 0)
                    positive_if = src.get("positive_if", "above")
                    # Build quarterly chart data
                    quarterly_trend = ""
                    quarterly_chart = []  # [{quarter: "2024Q3", value: 66.1}, ...]
                    try:
                        financials = stock.quarterly_financials
                        if financials is not None and not financials.empty:
                            if metric == "revenue_growth":
                                rev = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else None
                                if rev is not None and len(rev.dropna()) >= 2:
                                    vals = rev.dropna()
                                    # Build chart: QoQ growth for each quarter
                                    rev_vals = [(str(idx.date()) if hasattr(idx, "date") else str(idx), float(v)) for idx, v in vals.items()]
                                    rev_vals.reverse()  # oldest first
                                    for qi in range(1, len(rev_vals)):
                                        prev_v = rev_vals[qi - 1][1]
                                        cur_v = rev_vals[qi][1]
                                        if prev_v != 0:
                                            growth = (cur_v - prev_v) / abs(prev_v) * 100
                                            dt = rev_vals[qi][0]
                                            quarterly_chart.append({"quarter": dt[:7], "value": round(growth, 1)})
                                    # QoQ text
                                    if len(rev_vals) >= 2:
                                        latest_g = (rev_vals[-1][1] - rev_vals[-2][1]) / abs(rev_vals[-2][1]) * 100
                                        quarterly_trend = f"QoQ {'+'  if latest_g > 0 else ''}{latest_g:.1f}%"
                            elif "margin" in metric:
                                inc = financials
                                rev_row = "Total Revenue"
                                # Determine numerator row based on metric
                                if metric == "operating_margin" and "Operating Income" in inc.index:
                                    num_row = "Operating Income"
                                elif "Gross Profit" in inc.index and metric == "profit_margin":
                                    num_row = "Net Income" if "Net Income" in inc.index else "Gross Profit"
                                else:
                                    num_row = "Net Income" if "Net Income" in inc.index else None

                                if num_row and rev_row in inc.index and num_row in inc.index:
                                    rev_q = inc.loc[rev_row].dropna()
                                    num_q = inc.loc[num_row].dropna()
                                    # Build chart: margin % for each quarter
                                    common_cols = [c for c in rev_q.index if c in num_q.index]
                                    margin_pts = []
                                    for c in common_cols:
                                        r = float(rev_q[c])
                                        n = float(num_q[c])
                                        if r != 0:
                                            margin_pts.append((str(c.date()) if hasattr(c, "date") else str(c), round(n / r * 100, 1)))
                                    margin_pts.reverse()  # oldest first
                                    for mp in margin_pts:
                                        quarterly_chart.append({"quarter": mp[0][:7], "value": mp[1]})
                                    # QoQ delta text
                                    if len(margin_pts) >= 2:
                                        margin_delta = margin_pts[-1][1] - margin_pts[-2][1]
                                        quarterly_trend = f"전분기 대비 {'+'  if margin_delta > 0 else ''}{margin_delta:.1f}%p"
                    except Exception:
                        pass

                    if positive_if == "above":
                        item["status"] = "positive" if val > threshold else ("negative" if val < 0 else "neutral")
                    elif positive_if == "below":
                        item["status"] = "positive" if val < threshold else "negative"
                    if "margin" in metric or "growth" in metric or metric == "roe" or metric == "dividend_yield":
                        item["value"] = round(val * 100, 1)
                        pct_str = f"{round(val * 100, 1)}%"
                        item["detail"] = f"{pct_str} {quarterly_trend}" if quarterly_trend else pct_str
                        item["thresholds"] = {
                            "danger_line": round(threshold * 100 * 0.5, 1) if positive_if == "above" else round(threshold * 100 * 1.5, 1),
                            "safe_line": round(threshold * 100, 1),
                            "danger_label": f"{round(threshold * 100 * 0.5, 1)}% 이하 → 매도 신호" if positive_if == "above" else f"{round(threshold * 100 * 1.5, 1)}% 이상 → 매도 신호",
                            "safe_label": f"{round(threshold * 100, 1)}% 이상 → 긍정" if positive_if == "above" else f"{round(threshold * 100, 1)}% 이하 → 긍정",
                            "danger_dir": "below" if positive_if == "above" else "above",
                            "current": round(val * 100, 1),
                            "trend_warn": quarterly_trend if ("−" in quarterly_trend or "-" in quarterly_trend) and positive_if == "above" else "",
                        }
                    else:
                        item["value"] = round(val, 2)
                        item["detail"] = f"{round(val, 2)}"
                    # ── Inject preliminary earnings from news if available ──
                    if preliminary_earnings.get("found") and quarterly_chart:
                        pe_data = preliminary_earnings["data"]
                        last_q = quarterly_chart[-1] if quarterly_chart else {}
                        last_q_date = last_q.get("quarter", "2025-04")
                        # Compute next quarter date
                        try:
                            lq_parts = last_q_date.split("-")
                            lq_y, lq_m = int(lq_parts[0]), int(lq_parts[1])
                            nq_m = lq_m + 3
                            nq_y = lq_y + (1 if nq_m > 12 else 0)
                            nq_m = ((nq_m - 1) % 12) + 1
                            next_q = f"{nq_y}-{nq_m:02d}"
                        except Exception:
                            next_q = "잠정"

                        # For revenue_growth: compute growth from preliminary revenue
                        if metric == "revenue_growth" and "revenue_억" in pe_data:
                            # We have revenue in 억원, compare to last quarter's absolute revenue
                            try:
                                rev_row = stock.quarterly_financials.loc["Total Revenue"] if "Total Revenue" in stock.quarterly_financials.index else None
                                if rev_row is not None and len(rev_row.dropna()) >= 1:
                                    last_rev = float(rev_row.dropna().values[0])
                                    # Convert 억원 to same unit (yfinance uses raw currency)
                                    # Samsung: yfinance in KRW, 1억 = 100,000,000
                                    prelim_rev = pe_data["revenue_억"] * 1e8
                                    if last_rev > 0:
                                        prelim_growth = (prelim_rev - last_rev) / abs(last_rev) * 100
                                        quarterly_chart.append({
                                            "quarter": next_q,
                                            "value": round(prelim_growth, 1),
                                            "preliminary": True,
                                        })
                                        quarterly_trend = f"잠정 QoQ {'+'  if prelim_growth > 0 else ''}{prelim_growth:.1f}%"
                                        item["detail"] = f"{item.get('detail', '')} → 잠정 {'+' if prelim_growth > 0 else ''}{prelim_growth:.1f}%"
                            except Exception:
                                pass

                        # For margin metrics: compute from preliminary op_profit / revenue
                        elif "margin" in metric and "operating_profit_억" in pe_data and "revenue_억" in pe_data:
                            try:
                                prelim_margin = pe_data["operating_profit_억"] / pe_data["revenue_억"] * 100
                                quarterly_chart.append({
                                    "quarter": next_q,
                                    "value": round(prelim_margin, 1),
                                    "preliminary": True,
                                })
                                item["detail"] = f"{item.get('detail', '')} → 잠정 {prelim_margin:.1f}%"
                            except Exception:
                                pass

                    item["quarterly_chart"] = quarterly_chart
                    item["preliminary_data"] = preliminary_earnings.get("data", {}) if preliminary_earnings.get("found") else {}
                    item["source"] = f"Yahoo Finance ({ticker})" + (" + 뉴스 잠정실적" if preliminary_earnings.get("found") else "")
                    item["importance"] = src.get("weight", metadata["weight"])
                else:
                    item["detail"] = "데이터 없음"

            elif src["type"] == "commodity":
                try:
                    sym = src["symbol"]
                    positive_if = src.get("positive_if", "up")
                    hist = commodity_cache.get(sym, pd.DataFrame())
                    if not hist.empty and len(hist) > 20:
                        closes = hist["Close"].values.astype(float)
                        last_price = float(closes[-1])
                        first_price = float(closes[0])
                        change_pct = (last_price - first_price) / first_price * 100

                        # ── TREND DETECTION — this is the key metric ──
                        ma5 = float(np.mean(closes[-5:])) if len(closes) >= 5 else last_price
                        ma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else last_price
                        ma50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else ma20
                        # Recent momentum: 5-day vs 20-day
                        short_trend = (ma5 - ma20) / ma20 * 100
                        # Medium momentum: 20-day vs 50-day
                        mid_trend = (ma20 - ma50) / ma50 * 100 if len(closes) >= 50 else short_trend
                        # 1-month change
                        month_ago = float(closes[-22]) if len(closes) >= 22 else first_price
                        month_change = (last_price - month_ago) / month_ago * 100

                        # Trend direction label
                        if short_trend > 2:
                            trend_dir = "급상승"
                            trend_emoji = "up_fast"
                        elif short_trend > 0.5:
                            trend_dir = "상승중"
                            trend_emoji = "up"
                        elif short_trend < -2:
                            trend_dir = "급하락"
                            trend_emoji = "down_fast"
                        elif short_trend < -0.5:
                            trend_dir = "하락중"
                            trend_emoji = "down"
                        else:
                            trend_dir = "보합"
                            trend_emoji = "flat"

                        # STATUS based on TREND DIRECTION (not just absolute level)
                        if positive_if == "up":
                            # "up is good" — declining trend = danger even if price is still high
                            if trend_emoji in ("down_fast", "down"):
                                item["status"] = "negative"  # 하락 추세 = 위험
                            elif trend_emoji in ("up_fast", "up"):
                                item["status"] = "positive"
                            else:
                                item["status"] = "neutral"
                        elif positive_if == "down":
                            # "down is good" — rising trend = danger
                            if trend_emoji in ("up_fast", "up"):
                                item["status"] = "negative"
                            elif trend_emoji in ("down_fast", "down"):
                                item["status"] = "positive"
                            else:
                                item["status"] = "neutral"
                        elif positive_if == "stable":
                            item["status"] = "positive" if abs(short_trend) < 2 else "negative"

                        item["value"] = round(change_pct, 1)
                        item["detail"] = f"${round(last_price, 2)} | {trend_dir} (1개월 {'+' if month_change > 0 else ''}{round(month_change, 1)}%)"
                        item["trend_dir"] = trend_dir
                        item["trend_emoji"] = trend_emoji
                        item["short_trend"] = round(short_trend, 2)

                        # Trend data
                        c_min = float(hist["Close"].min())
                        c_max = float(hist["Close"].max())
                        c_range = c_max - c_min if c_max > c_min else 1.0
                        step = max(1, len(hist) // 60)
                        item["trend_data"] = [
                            {
                                "date": str(idx.date()),
                                "close": round(float(row["Close"]), 2),
                                "norm": round((float(row["Close"]) - c_min) / c_range * 100, 1),
                            }
                            for idx, row in hist.iloc[::step].iterrows()
                        ]

                        # Correlation with stock price: same-day + lead-lag
                        corr, lead_corr_5d, lead_corr_10d = _compute_return_correlation(stock_hist, hist)
                        item["correlation"] = corr
                        item["lead_corr_5d"] = lead_corr_5d
                        item["lead_corr_10d"] = lead_corr_10d
                        abs_corr = max(abs(corr), abs(lead_corr_5d), abs(lead_corr_10d))
                        if positive_if == "down":
                            # For "down is good", negative correlation with stock = positive influence
                            effective_corr = -max([corr, lead_corr_5d, lead_corr_10d], key=lambda value: abs(value))
                        else:
                            effective_corr = max([corr, lead_corr_5d, lead_corr_10d], key=lambda value: abs(value))
                        if abs_corr >= 0.7:
                            item["corr_label"] = "매우 강한 연관" if effective_corr > 0 else "매우 강한 역연관"
                        elif abs_corr >= 0.4:
                            item["corr_label"] = "강한 연관" if effective_corr > 0 else "강한 역연관"
                        elif abs_corr >= 0.2:
                            item["corr_label"] = "약한 연관" if effective_corr > 0 else "약한 역연관"
                        else:
                            item["corr_label"] = "연관 약함"
                        item["importance"] = max(item["importance"], round(abs_corr * 100))

                        # Threshold / danger lines
                        item["thresholds"] = compute_thresholds(hist, positive_if)

                        # Stock overlay data (merged by nearest date)
                        item["stock_overlay"] = stock_overlay

                        item["source"] = f"Yahoo Finance ({sym})"
                        item["importance"] = max(item["importance"], src.get("weight", metadata["weight"]))
                except Exception:
                    item["detail"] = "조회 실패"

            item["expected_condition"] = _format_expected_condition(item, src)
            item["lead_signal"] = "선행 개선" if item["status"] == "positive" else ("선행 악화" if item["status"] == "negative" else "중립")

            results.append(item)

        # Sort by importance (highest correlation first)
        results.sort(key=lambda r: r.get("importance", 0), reverse=True)
        summary = _build_checklist_summary(results)
        summary["sector_id"] = sector_id
        summary["analysis_mode"] = "prebuilt_top_pick" if _ticker_key(ticker) in TOP_PICK_SECTOR_MAP else "dynamic_live"
        summary["reference_candidates"] = _discover_reference_candidates(ticker, stock_hist, sector_id, sources, commodity_cache)
        summary["live_impact_news"] = _extract_live_impact_news(ticker, info=info, sector_id=sector_id)
        summary = _merge_catalysts(ticker, summary)
        response = {
            "ticker": ticker.upper(),
            "checklist": results,
            "summary": summary,
        }
        _set_cached(cache_key, response)
        return response

    except Exception as e:
        return {"ticker": ticker.upper(), "checklist": [], "error": str(e)}


@router.get("/analysis/stock-search/{query}")
async def search_stocks(query: str) -> dict:
    cache_key = f"stock-search:{query.strip().lower()}"
    cached = _get_cached_ttl(cache_key, 600)
    if cached is not None:
        return cached

    normalized_query = query.strip()
    if not normalized_query:
        return {"query": query, "results": []}

    results: list[dict] = []
    seen = set()
    try:
        lookup = yf.Search(normalized_query, max_results=12)
        quotes = getattr(lookup, "quotes", []) or []
        for quote in quotes:
            if str(quote.get("quoteType") or quote.get("typeDisp") or "").upper() != "EQUITY":
                continue
            symbol = _ticker_key(str(quote.get("symbol") or ""))
            if not symbol or symbol in seen:
                continue
            exchange = str(quote.get("exchange") or "")
            if exchange and exchange not in {"NMS", "NGM", "NYQ", "ASE", "PCX", "OQX", "KSC", "KOE", "KOS", "NCM"}:
                continue
            seen.add(symbol)
            sector_id = _infer_sector_id_from_profile(symbol, quote=quote)
            results.append({
                "ticker": symbol,
                "name": quote.get("shortname") or quote.get("longname") or symbol,
                "exchange": exchange,
                "flag": "KR" if symbol.endswith(".KS") or symbol.endswith(".KQ") else "US",
                "sector_id": sector_id,
                "sector_name": SECTOR_NAME_MAP.get(sector_id or "", "실시간 분석"),
                "is_top_pick": symbol in TOP_PICK_SECTOR_MAP,
                "analysis_mode": "prebuilt_top_pick" if symbol in TOP_PICK_SECTOR_MAP else "dynamic_live",
            })
            if len(results) >= 8:
                break
    except Exception:
        pass

    # Korean stock fallback: yfinance search is weak for Korean names, so use cached KRX listing.
    if len(results) < 8 and any("\uac00" <= ch <= "\ud7a3" for ch in normalized_query):
        query_kr = normalized_query.replace(" ", "")
        matched_rows = []
        for row in _get_krx_listing():
            compact_name = str(row["name"]).replace(" ", "")
            is_subsequence = False
            if query_kr and query_kr not in compact_name:
                idx = 0
                for ch in compact_name:
                    if idx < len(query_kr) and ch == query_kr[idx]:
                        idx += 1
                is_subsequence = idx == len(query_kr)
            if query_kr not in compact_name and not is_subsequence:
                continue
            if compact_name == query_kr:
                rank = 0
            elif compact_name.startswith(query_kr):
                rank = 1
            elif is_subsequence:
                rank = 2
            else:
                rank = 3
            matched_rows.append((rank, len(compact_name), row))

        matched_rows.sort(key=lambda item: (item[0], item[1]))
        for _, _, row in matched_rows:
            symbol = row["ticker"]
            if symbol in seen:
                continue
            seen.add(symbol)
            sector_id = _infer_sector_id_from_profile(symbol, info={"industry": row.get("industry", ""), "shortName": row["name"]})
            results.append({
                "ticker": symbol,
                "name": row["name"],
                "exchange": row.get("market", "KRX"),
                "flag": "KR",
                "sector_id": sector_id,
                "sector_name": SECTOR_NAME_MAP.get(sector_id or "", "실시간 분석"),
                "is_top_pick": symbol in TOP_PICK_SECTOR_MAP,
                "analysis_mode": "prebuilt_top_pick" if symbol in TOP_PICK_SECTOR_MAP else "dynamic_live",
            })
            if len(results) >= 8:
                break

    response = {"query": query, "results": results}
    _set_cached(cache_key, response)
    return response


@router.get("/analysis/sector/{sector_id}/pulse")
async def get_sector_pulse(sector_id: str) -> dict:
    cache_key = f"sector-pulse:{sector_id}"
    cached = _get_cached_ttl(cache_key, 240)
    if cached is not None:
        return cached

    try:
        sources = SECTOR_PULSE_SOURCES.get(sector_id, [])
        if not sources:
            return {"sector_id": sector_id, "checklist": [], "summary": {"score": 50}}

        items = []
        for source in sources:
            snap = _compute_symbol_trend_snapshot(source["symbol"], source["positive_if"])
            items.append({
                "name": source["name"],
                "symbol": source["symbol"],
                "status": snap["status"],
                "detail": snap["detail"],
                "current": snap["current"],
                "change_pct": snap["change_pct"],
                "trend_pct": snap["trend_pct"],
                "threshold": snap["threshold"],
                "weight": source["weight"],
                "why_it_matters": source["thesis"],
                "window": source["window"],
                "expected_condition": (
                    f"{snap['threshold']} 부근 위에서 추세가 유지돼야 합니다." if source["positive_if"] == "up" and snap["threshold"] is not None
                    else f"{snap['threshold']} 부근 아래로 내려와야 부담이 줄어듭니다." if source["positive_if"] == "down" and snap["threshold"] is not None
                    else "변동성이 진정되고 안정 구간을 유지해야 합니다."
                ),
            })

        weighted_total = sum(item["weight"] for item in items) or 1
        weighted_score = sum(
            (1 if item["status"] == "positive" else -1 if item["status"] == "negative" else 0) * item["weight"]
            for item in items
        )
        score = round(max(0, min(100, 50 + (weighted_score / weighted_total) * 50)))
        positives = sum(1 for item in items if item["status"] == "positive")
        negatives = sum(1 for item in items if item["status"] == "negative")

        items.sort(key=lambda item: item["weight"], reverse=True)
        response = {
            "sector_id": sector_id,
            "checklist": items,
            "summary": {
                "score": score,
                "positives": positives,
                "negatives": negatives,
                "signal": "positive" if score >= 60 else "negative" if score <= 40 else "neutral",
                "top_supports": [item for item in items if item["status"] == "positive"][:3],
                "top_risks": [item for item in items if item["status"] == "negative"][:3],
            },
        }
        _set_cached(cache_key, response)
        return response
    except Exception as e:
        return {"sector_id": sector_id, "checklist": [], "error": str(e)}


@router.get("/commodities/history/{symbol}")
async def get_commodity_history(symbol: str, period: str = "6mo") -> dict:
    """Get commodity price history for charting."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            return {"symbol": symbol, "data": []}

        data = []
        for idx, row in hist.iterrows():
            data.append({
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
            })
        return {"symbol": symbol, "data": data}
    except Exception:
        return {"symbol": symbol, "data": []}


@router.get("/commodities")
async def get_commodities() -> list[CommodityPrice]:
    """Get all tracked commodity prices."""
    return CommodityDataService.get_commodity_prices()


@router.get("/commodities/{sector_name}")
async def get_sector_commodities(sector_name: str) -> list[CommodityPrice]:
    """Get commodities related to a specific sector."""
    return CommodityDataService.get_related_commodities(sector_name)
