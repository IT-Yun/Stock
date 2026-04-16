import pandas as pd
import numpy as np
import re
import time
import json
import hashlib
import threading
import requests
import yfinance as yf
from fastapi import APIRouter
from bs4 import BeautifulSoup
from pathlib import Path
from models.schemas import AnalysisResult, TechnicalIndicators, CommodityPrice
from services.stock_data import StockDataService, get_yf_info, get_yf_financials
from services.technical_analysis import TechnicalAnalysisService
from services.commodity_data import CommodityDataService
from services.news_crawler import NewsCrawlerService
from services.fundamentals import fetch_fundamentals
from services.research import fetch_all_research, fetch_naver_analyst_reports, fetch_sec_filings
from services.runtime_controls import limit_http, limit_yfinance
from config import settings

try:
    from curl_cffi.requests import Session as _CffiSessionCheck
    _cffi_available = True
except ImportError:
    _cffi_available = False

router = APIRouter(prefix="/api", tags=["analysis"])


_ANALYSIS_CACHE: dict[str, tuple[float, object]] = {}
ANALYSIS_CACHE_TTL = 1800  # 30 min cache — minimize yfinance API calls to avoid rate limiting
_default_analysis_cache_dir = Path(__file__).resolve().parent.parent.parent / ".cache" / "analysis"
_render_analysis_cache_root = Path("/var/data/stock-cache/analysis")
_ANALYSIS_CACHE_DIR = Path(settings.CACHE_DIR) / "analysis" if settings.CACHE_DIR else (_render_analysis_cache_root if _render_analysis_cache_root.parent.exists() else _default_analysis_cache_dir)
_ANALYSIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_SINGLEFLIGHT_LOCK = threading.Lock()
_SINGLEFLIGHT_EVENTS: dict[str, threading.Event] = {}


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


def _strip_news_from_checklist(response: dict) -> dict:
    """Remove legacy news items from checklist responses (cached data may still contain them)."""
    if not isinstance(response, dict) or "checklist" not in response:
        return response
    items = response.get("checklist")
    if not isinstance(items, list):
        return response
    filtered = [
        item for item in items
        if not item.get("is_news_item")
        and not str(item.get("name", "")).startswith("뉴스:")
        and not str(item.get("name", "")).startswith("이슈 모니터링:")
    ]
    if len(filtered) == len(items):
        return response  # nothing changed
    result = {**response, "checklist": filtered}
    return result


def _analysis_cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return _ANALYSIS_CACHE_DIR / f"{digest}.json"


def _jsonable(value: object):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _restore_cached(value: object, model_cls=None):
    if model_cls and isinstance(value, dict):
        return model_cls(**value)
    return value


def _load_disk_cached(key: str, ttl: int, *, allow_stale: bool = False, model_cls=None):
    path = _analysis_cache_path(key)
    if not path.exists():
        return None
    if not allow_stale and time.time() - path.stat().st_mtime > ttl:
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return _restore_cached(payload, model_cls=model_cls)
    except Exception:
        return None


def _save_disk_cached(key: str, value: object):
    path = _analysis_cache_path(key)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(_jsonable(value), f, ensure_ascii=False)
    except Exception:
        pass


def _get_best_cached(key: str, ttl: int, *, model_cls=None):
    cached = _get_cached_ttl(key, ttl)
    if cached is not None:
        return cached
    disk = _load_disk_cached(key, ttl, model_cls=model_cls)
    if disk is not None:
        _set_cached(key, disk)
        return disk
    return None


def _run_singleflight(key: str, producer, *, ttl: int, model_cls=None):
    cached = _get_best_cached(key, ttl, model_cls=model_cls)
    if cached is not None:
        return cached

    with _SINGLEFLIGHT_LOCK:
        event = _SINGLEFLIGHT_EVENTS.get(key)
        if event is None:
            event = threading.Event()
            _SINGLEFLIGHT_EVENTS[key] = event
            owner = True
        else:
            owner = False

    if not owner:
        event.wait(timeout=30)
        cached = _get_best_cached(key, ttl, model_cls=model_cls)
        if cached is not None:
            return cached
        stale = _load_disk_cached(key, ttl, allow_stale=True, model_cls=model_cls)
        if stale is not None:
            _set_cached(key, stale)
            return stale
        return producer()

    try:
        value = producer()
        _set_cached(key, value)
        _save_disk_cached(key, value)
        return value
    except Exception:
        stale = _load_disk_cached(key, ttl, allow_stale=True, model_cls=model_cls)
        if stale is not None:
            _set_cached(key, stale)
            return stale
        raise
    finally:
        with _SINGLEFLIGHT_LOCK:
            current = _SINGLEFLIGHT_EVENTS.pop(key, None)
            if current is not None:
                current.set()


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

    # Per-stock enriched news queries — covers all sector top picks
    _STOCK_NEWS_QUERIES = {
        "005930.KS": ["삼성전자 HBM", "삼성전자 파운드리 수율", "Samsung Electronics HBM", "삼성전자 갤럭시"],
        "005930": ["삼성전자 HBM", "삼성전자 파운드리 수율", "Samsung Electronics HBM", "삼성전자 갤럭시"],
        "000660.KS": ["SK하이닉스 HBM", "SK hynix NVIDIA HBM4", "SK하이닉스 DRAM 가격"],
        "000660": ["SK하이닉스 HBM", "SK hynix NVIDIA HBM4", "SK하이닉스 DRAM 가격"],
        "NVDA": ["NVIDIA Blackwell GPU", "NVIDIA AI capex", "엔비디아 HBM 공급", "NVIDIA China export"],
        "TSM": ["TSMC 2nm 양산", "TSMC CoWoS", "TSMC Arizona fab", "TSMC AI demand"],
        "AVGO": ["Broadcom custom AI chip", "Broadcom VMware synergy", "Broadcom TPU"],
        "TSLA": ["Tesla deliveries", "Tesla FSD robotaxi", "Tesla Optimus robot", "테슬라 인도량"],
        "ISRG": ["Intuitive da Vinci 5", "da Vinci surgical procedures", "수술로봇 다빈치"],
        "CEG": ["Constellation Energy nuclear", "data center power PPA", "원전 전력계약"],
        "CCJ": ["Cameco uranium supply", "uranium price spot", "우라늄 공급 부족"],
        "CRWD": ["CrowdStrike ARR", "CrowdStrike platform modules", "사이버보안 수요"],
        "CRSP": ["CRISPR Therapeutics FDA", "유전자편집 임상", "Casgevy"],
        "LLY": ["Eli Lilly GLP-1 Mounjaro", "비만약 처방 데이터", "Lilly Alzheimer donanemab"],
        "IONQ": ["IonQ quantum computer", "양자컴퓨터 큐비트", "quantum computing contract"],
        "RKLB": ["Rocket Lab Neutron", "Rocket Lab launch", "로켓랩 발사"],
        "BE": ["Bloom Energy data center", "SOFC fuel cell", "블룸에너지 수주"],
        # Korean stocks
        "086520.KS": ["에코프로 리튬", "에코프로 양극재", "에코프로 인도네시아"],
        "247540.KS": ["에코프로비엠 양극재", "에코프로비엠 수주"],
        "373220.KS": ["LG에너지솔루션 배터리", "LGES battery supply"],
        "006400.KS": ["삼성SDI 전고체 배터리", "Samsung SDI battery"],
        "047810.KS": ["한국항공우주 KF-21", "KAI 수주"],
        "012450.KS": ["한화에어로스페이스 방산", "한화에어로 수출"],
    }
    stock_queries = _STOCK_NEWS_QUERIES.get(normalized, [])
    queries.extend(stock_queries)

    # For KRX stocks: auto-add Korean name from _KRX_INDUSTRY_MAP if available
    if not stock_queries and (normalized.endswith(".KS") or normalized.endswith(".KQ")):
        code = normalized.split(".")[0]
        krx_info = _KRX_INDUSTRY_MAP.get(code)
        if krx_info:
            queries.append(f"{krx_info['name']} {krx_info['industry']}")
            queries.append(f"{krx_info['name']} 실적")

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
    cached = _get_cached_ttl(cache_key, 180)  # 3분 — 뉴스는 실시간
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


SPAM_KEYWORDS = [
    "축제", "festival", "관광", "tourism", "날씨", "weather", "맛집", "restaurant",
    "부동산", "아파트", "분양", "결혼", "wedding", "여행", "travel", "스포츠", "sports",
    "연예", "celebrity", "드라마", "drama", "게임", "gaming", "recipe", "요리",
    "lottery", "로또", "점술", "운세", "horoscope", "사건사고", "crime",
    # Extended spam topics
    "인테리어", "interior", "이사", "moving", "보험", "insurance", "대출", "loan",
    "다이어트", "diet", "건강식품", "supplement", "광고", "모집", "채용공고",
    "무료체험", "free trial", "할인쿠폰", "coupon", "event", "이벤트 당첨",
    "crypto airdrop", "에어드롭", "meme coin", "밈코인",
]

# Auto-generated spam sources and patterns — block entirely
SPAM_SOURCES = [
    "tradingkey", "stockanalysis.com/quote", "simplywall", "smartkarma",
    "wallstreetzen", "marketscreener", "trendlyne",
    # Additional spam sources
    "tipranks.com/news", "ainvest", "stocktitan", "accesswire", "prnewswire",
    "businesswire",  # PR wires are often self-promotional
    "insidermonkey", "247wallst", "investorplace",
]
SPAM_TITLE_PATTERNS = [
    "주식 움직였습니다",
    "주식이 움직였습니다",
    "변동을 뒷받침하는 사실",
    "핵심 원인 공개",
    "투자자가 알아야 할 정보",
    "what you need to know",
    "stock moved",
    "here's what happened",
    "here is what happened",
    "why it moved",
    "what drove",
    # Extended auto-generated patterns
    "top stocks to buy",
    "best stocks to",
    "should you buy",
    "is it time to buy",
    "millionaire maker",
    "배당금 지급일",
    "주식 추천",
    "급등주 추천",
    "무료 종목 추천",
    "긴급 매수",
    "지금 사야 할",
    "10배 수익",
    "대박 종목",
    "stocks to watch this week",
    "wall street predicts",
    "analyst says buy",
    "cathie wood",
    "주식리딩",
    "주식방송",
    "stock alert",
]

# ── Comprehensive News Relevance & Quality Algorithm ──

# Company-specific name aliases for matching (handles English/Korean variants)
_COMPANY_ALIASES: dict[str, list[str]] = {
    "005930.KS": ["삼성전자", "samsung", "samsung electronics", "samsungelec"],
    "000660.KS": ["sk하이닉스", "sk hynix", "hynix"],
    "NVDA": ["nvidia", "엔비디아"],
    "TSM": ["tsmc", "taiwan semiconductor", "대만반도체"],
    "AVGO": ["broadcom", "브로드컴"],
    "TSLA": ["tesla", "테슬라"],
    "ISRG": ["intuitive", "intuitive surgical", "da vinci", "다빈치"],
    "CEG": ["constellation", "constellation energy"],
    "CCJ": ["cameco", "카메코"],
    "CRWD": ["crowdstrike", "크라우드스트라이크"],
    "CRSP": ["crispr", "크리스퍼"],
    "LLY": ["eli lilly", "lilly", "릴리"],
    "IONQ": ["ionq", "아이온큐"],
    "RKLB": ["rocket lab", "로켓랩"],
    "BE": ["bloom energy", "블룸에너지"],
    "LMT": ["lockheed", "lockheed martin", "록히드"],
    "RTX": ["raytheon", "rtx corp", "레이시온"],
    "GD": ["general dynamics", "제너럴다이나믹스"],
    "086520.KS": ["에코프로", "ecopro"],
    "247540.KS": ["에코프로비엠", "ecoprobm"],
    "373220.KS": ["lg에너지솔루션", "lg energy solution", "lges"],
    "006400.KS": ["삼성sdi", "samsung sdi"],
    "047810.KS": ["한국항공우주", "한국항공", "kai", "korea aerospace"],
    "012450.KS": ["한화에어로스페이스", "한화에어로", "hanwha aerospace"],
}


def _build_name_variants(ticker: str, company_name: str) -> list[str]:
    """Build all name variants for a ticker to check article relevance."""
    normalized = _ticker_key(ticker)
    variants = set()

    # Ticker itself
    ticker_base = normalized.replace(".KS", "").replace(".KQ", "").lower()
    if ticker_base and len(ticker_base) >= 2:
        variants.add(ticker_base)

    # Company name variants
    company_lower = (company_name or "").lower().strip()
    if company_lower:
        variants.add(company_lower)
        for part in company_lower.split():
            if len(part) >= 2:
                variants.add(part)

    # Aliases from our map
    aliases = _COMPANY_ALIASES.get(normalized, [])
    for alias in aliases:
        variants.add(alias.lower())

    # KRX name from industry map
    if normalized.endswith(".KS") or normalized.endswith(".KQ"):
        code = normalized.split(".")[0]
        krx_info = _KRX_INDUSTRY_MAP.get(code)
        if krx_info and krx_info.get("name"):
            variants.add(krx_info["name"].lower())

    return [v for v in variants if v and len(v) >= 2]


def _is_article_relevant(title: str, source: str, name_variants: list[str]) -> tuple[bool, float]:
    """
    Multi-stage relevance check. Returns (is_relevant, relevance_score).

    Stage 1: Spam keyword/source/pattern rejection (score = 0)
    Stage 2: Company mention check (must pass to score > 0)
    Stage 3: Content quality scoring (higher = more actionable/specific)
    Stage 4: Freshness/specificity bonus
    """
    text = (title or "").lower()
    combined = (text + " " + (source or "").lower())

    # ── Stage 1: Hard reject spam ──
    if any(spam in combined for spam in SPAM_KEYWORDS):
        return False, 0.0
    if any(pattern in combined for pattern in SPAM_TITLE_PATTERNS):
        return False, 0.0
    if any(src in combined for src in SPAM_SOURCES):
        return False, 0.0

    # Reject very short titles (likely auto-generated)
    if len(title.strip()) < 10:
        return False, 0.0

    # Reject listicle / clickbait patterns
    if re.match(r"^\d+\s*(best|top|가지|선|개)\b", text):
        return False, 0.0
    if "..." in title and len(title) < 25:
        return False, 0.0  # Likely truncated clickbait

    # ── Stage 2: Company/ticker mention check ──
    mention_score = 0.0
    for variant in name_variants:
        if variant in text:
            # Longer match = more specific = higher score
            mention_score = max(mention_score, min(len(variant) / 5, 5.0))

    if mention_score == 0:
        return False, 0.0  # Must mention the company

    score = mention_score

    # ── Stage 3: Content quality scoring ──
    # Specific financial data = high quality
    if any(kw in text for kw in ["실적", "매출", "영업이익", "순이익", "earnings", "revenue", "profit", "eps"]):
        score += 4.0
    if any(kw in text for kw in ["가이던스", "guidance", "outlook", "전망치"]):
        score += 3.5
    if any(kw in text for kw in ["승인", "approval", "fda", "수주", "contract", "계약", "납품"]):
        score += 3.5
    if any(kw in text for kw in ["목표가", "목표주가", "target price", "tp ", "투자의견", "rating"]):
        score += 3.0
    if any(kw in text for kw in ["인수", "합병", "m&a", "acquisition", "지분", "stake"]):
        score += 3.0
    if any(kw in text for kw in ["규제", "regulation", "소송", "lawsuit", "조사", "probe", "관세", "tariff"]):
        score += 2.5
    if any(kw in text for kw in ["신제품", "출시", "launch", "발표", "공개", "신기술"]):
        score += 2.5

    # Numbers = specificity (articles with actual numbers are more informative)
    number_matches = re.findall(r'\d+[.,%조억만원달러$B]', text)
    if number_matches:
        score += min(len(number_matches) * 0.5, 2.0)

    # Named sources boost (analyst, broker name = credible)
    if any(kw in text for kw in ["증권", "애널리스트", "analyst", "리서치", "모건스탠리", "morgan stanley",
                                  "골드만", "goldman", "jp모건", "ubs", "citigroup", "바클레이즈"]):
        score += 1.5

    # ── Stage 4: Penalty for generic/low-value content ──
    # Penalize vague/generic articles
    if any(kw in text for kw in ["동향", "전반적", "overall", "overview", "summary", "요약"]):
        score -= 1.0
    # Penalize opinion pieces without data
    if any(kw in text for kw in ["칼럼", "column", "사설", "editorial", "의견", "opinion piece"]):
        score -= 1.5
    # Penalize promotional content
    if any(kw in text for kw in ["무료", "이벤트", "특가", "할인", "프로모션"]):
        score -= 3.0

    return score > 2.0, max(score, 0.0)


def _score_live_article_impact(title: str, ticker: str, company_name: str, sector_id: str | None) -> int:
    """Score article relevance. Uses the comprehensive _is_article_relevant algorithm."""
    name_variants = _build_name_variants(ticker, company_name)
    is_relevant, score = _is_article_relevant(title, "", name_variants)
    if not is_relevant:
        return 0
    return int(score)


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


def _search_stock_latest_news(queries: list[str], max_per_query: int = 8, ticker: str = "", company_name: str = "") -> list[dict]:
    """
    Directly search Naver + Google RSS for latest stock news.
    Returns list of {title, source, url, published_at, relevance_score} dicts.
    Uses comprehensive multi-stage filtering to reject spam and irrelevant articles.
    """
    from urllib.parse import quote
    import feedparser

    raw_articles = []
    seen = set()

    # Build name variants for relevance scoring
    name_variants = _build_name_variants(ticker, company_name) if ticker else []

    # Date filter: only last 7 days
    from datetime import datetime, timedelta
    _now = datetime.now()
    _week_ago = _now - timedelta(days=7)
    ds = _week_ago.strftime("%Y.%m.%d")
    de = _now.strftime("%Y.%m.%d")

    for query in queries:
        # Naver News — sorted by latest, filtered to last 7 days
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={quote(query)}&sm=tab_opt&sort=1&ds={ds}&de={de}&nso=so:dd,p:from{_week_ago.strftime('%Y%m%d')}to{_now.strftime('%Y%m%d')}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            with limit_http():
                r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for item in soup.select("div.news_area")[:max_per_query]:
                    title_tag = item.select_one("a.news_tit")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    if title in seen:
                        continue
                    seen.add(title)
                    source_tag = item.select_one("a.info.press")
                    source = source_tag.get_text(strip=True) if source_tag else ""
                    link = title_tag.get("href", "")
                    date_tag = item.select_one("span.info")
                    pub = date_tag.get_text(strip=True) if date_tag else None
                    raw_articles.append({"title": title, "source": source, "url": link, "published_at": pub})
        except Exception:
            pass

        # Google News RSS — latest, filtered to last 7 days via 'when:7d'
        try:
            encoded = quote(query)
            for lang, hl, gl, ceid in [("ko", "ko", "KR", "KR:ko"), ("en", "en", "US", "US:en")]:
                feed_url = f"https://news.google.com/rss/search?q={encoded}+when:7d&hl={hl}&gl={gl}&ceid={ceid}"
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:max_per_query]:
                    title = entry.get("title", "")
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    src = entry.get("source", {}).get("title", "Google News") if hasattr(entry, "source") else "Google News"
                    raw_articles.append({
                        "title": title,
                        "source": src,
                        "url": entry.get("link", ""),
                        "published_at": entry.get("published", None),
                    })
        except Exception:
            pass

    # ── Filter out old articles (>7 days) based on published_at ──
    def _is_recent(pub: str | None) -> bool:
        if not pub:
            return True  # keep if unknown date
        pub_lower = pub.lower().strip()
        # Naver relative dates: "X시간 전", "X분 전", "X일 전"
        if "전" in pub_lower:
            day_match = re.search(r"(\d+)일\s*전", pub_lower)
            if day_match and int(day_match.group(1)) > 7:
                return False
            return True  # hours/minutes ago = recent
        # RFC 2822 dates from Google RSS (e.g. "Tue, 15 Apr 2026 08:30:00 GMT")
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub)
            if (_now - dt.replace(tzinfo=None)).days > 7:
                return False
        except Exception:
            pass
        # Korean date (2026.01.15)
        date_match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", pub_lower)
        if date_match:
            try:
                dt = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                if (_now - dt).days > 7:
                    return False
            except Exception:
                pass
        return True

    def _normalize_date(pub: str | None) -> str:
        """Convert published_at to human-readable Korean format."""
        if not pub:
            return ""
        pub_lower = pub.strip()
        # Already Korean relative ("3시간 전", "1일 전")
        if "전" in pub_lower:
            return pub_lower
        # RFC 2822
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub)
            delta = _now - dt.replace(tzinfo=None)
            if delta.days == 0:
                hours = delta.seconds // 3600
                if hours == 0:
                    return f"{delta.seconds // 60}분 전"
                return f"{hours}시간 전"
            elif delta.days == 1:
                return "어제"
            elif delta.days <= 7:
                return f"{delta.days}일 전"
            return dt.strftime("%m/%d")
        except Exception:
            pass
        return pub_lower

    raw_articles = [a for a in raw_articles if _is_recent(a.get("published_at"))]
    for a in raw_articles:
        a["published_at"] = _normalize_date(a.get("published_at"))

    # ── Apply comprehensive relevance filtering ──
    if name_variants:
        scored = []
        for art in raw_articles:
            is_relevant, rel_score = _is_article_relevant(art["title"], art.get("source", ""), name_variants)
            if is_relevant:
                art["relevance_score"] = rel_score
                scored.append(art)
        # Sort by relevance score (highest first)
        scored.sort(key=lambda a: a.get("relevance_score", 0), reverse=True)
        return scored
    else:
        # Fallback: basic spam filter only (for macro/sector-level queries without specific ticker)
        all_spam = SPAM_SOURCES + SPAM_TITLE_PATTERNS
        filtered = []
        for art in raw_articles:
            combined = (art["title"] + " " + art.get("source", "")).lower()
            if any(s in combined for s in all_spam):
                continue
            if any(s in combined for s in SPAM_KEYWORDS):
                continue
            filtered.append(art)
        return filtered


def _summarize_english_title(title: str, company_name: str) -> str:
    """Translate/summarize English news title to Korean explanation.
    Extracts entities, numbers, and context to build a meaningful Korean summary."""
    t = title.lower()
    original = title.strip()
    parts = []

    # Extract specific numbers (%, $, amounts)
    pct_matches = re.findall(r'(\d+\.?\d*)%', t)
    dollar_matches = re.findall(r'\$\s*([\d,.]+)\s*(billion|million|trillion|B|M)?', t, re.IGNORECASE)

    # Extract analyst/firm names
    firm_match = re.search(r'(morgan stanley|goldman sachs|jp morgan|jpmorgan|barclays|citi|citigroup|ubs|deutsche bank|bofa|bank of america|wells fargo|rbc|bernstein|jefferies|wedbush|piper sandler|needham|truist|stifel|cowen|loop capital|mizuho|hsbc|nomura|daiwa|macquarie|samsung securities|merrill|oppenheimer)', t)
    firm_name = firm_match.group(1).title() if firm_match else ""

    # Target price
    tp_match = re.search(r'(?:target|price target|pt|tp)\s*(?:to\s*)?(?:of\s*)?(?:krw|usd|\$)?\s*([\d,.]+)', t)
    if tp_match:
        tp_val = tp_match.group(1)
        parts.append(f"목표주가 ${tp_val}" if not any(c in t for c in ["krw", "원"]) else f"목표주가 {tp_val}")

    # Rating changes
    if "buy" in t or "outperform" in t:
        parts.append("매수 의견")
    elif "sell" in t or "underperform" in t:
        parts.append("매도 의견")
    elif "hold" in t or "neutral" in t or "equal.weight" in t:
        parts.append("중립 의견")
    if "initiates" in t or "initiate" in t:
        parts.append("신규 커버리지 개시")
    elif "upgrade" in t:
        parts.append("투자의견 상향")
    elif "downgrade" in t:
        parts.append("투자의견 하향")
    elif "maintains" in t or "reiterate" in t:
        parts.append("투자의견 유지")
    elif "raises" in t and "target" in t:
        parts.append("목표주가 상향")
    elif "lowers" in t or "cuts" in t:
        parts.append("목표주가 하향")

    if firm_name:
        parts.insert(0, f"{firm_name}")

    # Revenue/earnings specifics
    rev_match = re.search(r'revenue\s*(?:of\s*)?\$?([\d,.]+)\s*(billion|million|B|M)?', t, re.IGNORECASE)
    if rev_match:
        parts.append(f"매출 ${rev_match.group(1)}{rev_match.group(2) or ''}")
    eps_match = re.search(r'eps\s*(?:of\s*)?\$?([\d,.]+)', t, re.IGNORECASE)
    if eps_match:
        parts.append(f"EPS ${eps_match.group(1)}")

    # Percentage moves
    if "surge" in t or "soar" in t or "jump" in t or "rally" in t or "gain" in t:
        pct = pct_matches[0] if pct_matches else ""
        parts.append(f"{pct}% 급등" if pct else "급등세")
    elif "falls" in t or "drop" in t or "plunge" in t or "tumble" in t or "slide" in t or "slump" in t:
        pct = pct_matches[0] if pct_matches else ""
        parts.append(f"{pct}% 급락" if pct else "급락세")

    # Specific business events
    if "partnership" in t or "deal" in t or "signs" in t:
        parts.append("파트너십/계약 체결")
    if "acquisition" in t or "acquire" in t or "merger" in t:
        parts.append("인수합병(M&A)")
    if "layoff" in t or "cut" in t and "job" in t:
        parts.append("구조조정/감원")
    if "buyback" in t or "repurchase" in t:
        parts.append("자사주 매입")
    if "dividend" in t:
        parts.append("배당 관련")
    if "split" in t and "stock" in t:
        parts.append("주식 분할")
    if "ipo" in t:
        parts.append("IPO 관련")

    # Industry-specific
    if "ai chip" in t or "ai boom" in t or "artificial intelligence" in t:
        parts.append("AI 수혜")
    if "hbm" in t:
        parts.append("HBM 수요")
    if "data center" in t or "datacenter" in t:
        parts.append("데이터센터 수요")
    if "foundry" in t or "tsmc" in t:
        parts.append("파운드리 관련")
    if "ev" in t or "electric vehicle" in t:
        parts.append("전기차 관련")
    if "battery" in t or "lithium" in t:
        parts.append("배터리/리튬")
    if "tariff" in t or "trade war" in t or "sanctions" in t:
        parts.append("관세/무역 리스크")
    if "fda" in t and ("approv" in t or "clear" in t):
        parts.append("FDA 승인")
    if "clinical" in t or "trial" in t:
        parts.append("임상시험")
    if "record" in t and ("high" in t or "breaking" in t):
        parts.append("사상 최고치")
    if "guidance" in t and ("raise" in t or "above" in t or "beat" in t):
        parts.append("가이던스 상향")
    if "miss" in t and ("estimate" in t or "expectation" in t):
        parts.append("시장 기대 하회")
    if "beat" in t and ("estimate" in t or "expectation" in t):
        parts.append("시장 기대 상회")

    if parts:
        return " · ".join(parts[:5])  # max 5 points

    # Fallback: simple word-level translation for common patterns
    simple_map = {
        "reports": "실적 발표", "quarterly": "분기", "annual": "연간",
        "growth": "성장", "decline": "하락", "strong": "호조",
        "weak": "부진", "outlook": "전망", "demand": "수요",
        "supply": "공급", "shortage": "부족", "expansion": "확장",
        "contract": "수주", "order": "주문", "shipment": "출하",
    }
    found = [v for k, v in simple_map.items() if k in t]
    if found:
        return " · ".join(found[:4])
    return ""


def _classify_sentiment_detailed(title: str, company_name: str) -> tuple[str, str, str]:
    """
    Classify a news title into (direction, category, analysis).
    Returns Korean summary with actual analysis, not just copy-paste.
    """
    text = title.lower()
    title_clean = title.strip()

    pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text]
    neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text]

    # Check if English title — if so, translate key points
    is_english = all(ord(c) < 0x1100 or ord(c) > 0xD7AF for c in title_clean.replace(" ", "")[:20]) if title_clean else False
    en_summary = _summarize_english_title(title_clean, company_name) if is_english else ""

    def _build_explanation(direction_kr: str, detail: str, impact: str) -> str:
        """Build a clean Korean explanation. If English title, add translated summary."""
        if en_summary:
            return f"{direction_kr} — {en_summary}. {impact}"
        return f"{direction_kr} — {detail}. {impact}"

    # Category detection with sentiment
    if any(kw in text for kw in ["실적", "매출", "영업이익", "earnings", "revenue", "profit", "순이익"]):
        if any(kw in text for kw in ["부진", "miss", "적자", "감소", "하락"]):
            detail = en_summary or f"{company_name} 실적 부진 보도"
            return "negative", "실적 악재", _build_explanation("실적 악재", detail, "실적 미달은 밸류에이션 하향 조정으로 이어질 수 있습니다")
        elif any(kw in text for kw in ["호실적", "beat", "상승", "성장", "흑자", "개선", "증가", "사상최대", "record", "surge"]):
            detail = en_summary or f"{company_name} 실적 호조 보도"
            return "positive", "실적 호재", _build_explanation("실적 호재", detail, "실적 서프라이즈는 목표주가 상향의 직접 트리거입니다")
        else:
            detail = en_summary or f"{company_name} 실적 관련 보도"
            return "neutral", "실적 발표", _build_explanation("실적 관련", detail, "구체적 수치 확인이 필요합니다")

    if any(kw in text for kw in ["가이던스", "guidance", "전망", "outlook", "forecast"]):
        if any(kw in text for kw in ["상향", "raise", "upbeat", "강화"]):
            detail = en_summary or f"{company_name} 가이던스 상향"
            return "positive", "가이던스 상향", _build_explanation("호재", detail, "가이던스 상향은 시장 기대치를 높이는 강력한 신호입니다")
        elif any(kw in text for kw in ["하향", "lower", "cut", "축소", "우려"]):
            detail = en_summary or f"{company_name} 가이던스 하향"
            return "negative", "가이던스 하향", _build_explanation("악재", detail, "가이던스 하향은 성장 둔화 우려를 키웁니다")
        detail = en_summary or f"{company_name} 전망 관련 보도"
        return "neutral", "가이던스", _build_explanation("전망 관련", detail, "가이던스 방향성 확인이 필요합니다")

    if any(kw in text for kw in ["승인", "approval", "수주", "contract", "계약", "납품", "공급", "deal", "partnership"]):
        detail = en_summary or f"{company_name} 신규 수주/계약 보도"
        return "positive", "수주/계약 호재", _build_explanation("호재", detail, "신규 수주·계약은 매출 성장 가시성을 높입니다")

    if any(kw in text for kw in ["규제", "regulation", "소송", "lawsuit", "probe", "조사", "벌금", "제재", "ban", "tariff", "관세"]):
        detail = en_summary or f"{company_name} 규제/법적 이슈"
        return "negative", "규제/법적 리스크", _build_explanation("악재", detail, "규제·법적 리스크는 불확실성을 키워 주가를 압박합니다")

    if any(kw in text for kw in ["목표가", "target", "상향", "upgrade", "outperform", "매수", "buy", "initiates", "raises"]):
        detail = en_summary or f"{company_name} 투자의견 상향"
        return "positive", "애널리스트 호평", _build_explanation("호재", detail, "투자의견 상향은 기관 매수세 유입의 신호입니다")

    if any(kw in text for kw in ["하향", "downgrade", "매도", "sell", "underperform", "underweight"]):
        detail = en_summary or f"{company_name} 투자의견 하향"
        return "negative", "애널리스트 하향", _build_explanation("악재", detail, "투자의견 하향은 기관 매도 압력으로 이어질 수 있습니다")

    if any(kw in text for kw in ["인수", "합병", "m&a", "acquisition", "merge", "투자", "지분"]):
        if any(kw in text for kw in ["우려", "반대", "실패"]):
            detail = en_summary or f"{company_name} M&A 리스크"
            return "negative", "M&A 리스크", _build_explanation("악재", detail, "M&A 관련 불확실성이 주가에 부담을 줍니다")
        detail = en_summary or f"{company_name} 전략적 투자/M&A"
        return "positive", "M&A/전략적 투자", _build_explanation("호재", detail, "전략적 투자·M&A는 성장 기대를 높입니다")

    if any(kw in text for kw in ["신제품", "출시", "launch", "발표", "공개", "신기술"]):
        detail = en_summary or f"{company_name} 신제품/신기술 발표"
        return "positive", "제품/기술 호재", _build_explanation("호재", detail, "신제품·신기술 발표는 성장 동력 확대의 신호입니다")

    if any(kw in text for kw in ["리콜", "recall", "결함", "defect", "지연", "delay"]):
        detail = en_summary or f"{company_name} 제품 리스크"
        return "negative", "제품 리스크", _build_explanation("악재", detail, "리콜·결함은 비용 증가와 브랜드 훼손을 야기합니다")

    if any(kw in text for kw in ["war", "전쟁", "iran", "이란", "conflict", "분쟁", "geopoliti", "지정학"]):
        detail = en_summary or "지정학적 리스크 고조"
        return "negative", "지정학 리스크", _build_explanation("악재", detail, "지정학 리스크는 시장 전체 위험회피 심리를 키웁니다")

    if any(kw in text for kw in ["oil", "유가", "crude", "원유", "opec"]):
        detail = en_summary or "원유/유가 관련"
        direction = "negative" if any(kw in text for kw in ["surge", "spike", "급등", "상승"]) else "neutral"
        return direction, "유가/원자재", _build_explanation("유가 관련", detail, "유가 변동은 기업 원가와 소비심리에 영향을 줍니다")

    # Fallback: keyword-based sentiment
    if len(pos_hits) > len(neg_hits):
        detail = en_summary or f"{company_name} 관련 긍정 보도"
        return "positive", "호재", _build_explanation("호재", detail, "긍정적 영향이 예상됩니다")
    elif len(neg_hits) > len(pos_hits):
        detail = en_summary or f"{company_name} 관련 부정 보도"
        return "negative", "악재", _build_explanation("악재", detail, "부정적 영향이 우려됩니다")
    detail = en_summary or f"{company_name} 관련 보도"
    return "neutral", "모니터링 필요", _build_explanation("중립", detail, "후속 뉴스로 방향성 확인이 필요합니다")


def _extract_live_impact_news(ticker: str, info: dict | None = None, sector_id: str | None = None) -> list[dict]:
    cache_key = f"live-impact-news:{_ticker_key(ticker)}"
    cached = _get_cached_ttl(cache_key, 180)  # 3분 — 뉴스는 실시간
    if cached is not None:
        return cached

    company_name = str((info or {}).get("shortName") or (info or {}).get("longName") or ticker).strip()

    # Build per-stock search queries
    queries = _build_stock_news_queries(ticker, info=info, sector_id=sector_id)

    # Direct search with built-in relevance filtering
    raw_articles = _search_stock_latest_news(queries, max_per_query=6, ticker=ticker, company_name=company_name)

    # Already filtered by _is_article_relevant — now classify sentiment
    candidates = []
    for art in raw_articles:
        title = art["title"]

        # Classify sentiment with detailed analysis
        direction, category, analysis = _classify_sentiment_detailed(title, company_name)

        # Use the relevance score from filtering + sentiment bonus
        score = art.get("relevance_score", 5.0)
        if direction != "neutral":
            score += 3  # actionable news scores higher

        candidates.append({
            "title": title,
            "source": art.get("source"),
            "published_at": art.get("published_at"),
            "url": art.get("url"),
            "impact_score": score,
            "impact_direction": direction,
            "issue_label": category,
            "explanation": analysis,
        })

    candidates.sort(key=lambda item: item["impact_score"], reverse=True)
    top = candidates[:5]
    _set_cached(cache_key, top)
    return top


def _derive_earnings_fallbacks(stock: yf.Ticker) -> dict:
    fallback = {
        "revenue_growth": None,
        "earnings_growth": None,
        "profit_margin": None,
        "operating_margin": None,
        "roe": None,
        "price_to_book": None,
        "pe_ratio": None,
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
        # Earnings (net income) growth
        if len(cols) >= 2 and "Net Income" in qf.index:
            cur_ni = qf.loc["Net Income", cols[0]]
            prev_ni = qf.loc["Net Income", cols[1]]
            if not pd.isna(cur_ni) and not pd.isna(prev_ni) and float(prev_ni) != 0:
                fallback["earnings_growth"] = (float(cur_ni) - float(prev_ni)) / abs(float(prev_ni))
        if "Total Revenue" in qf.index:
            cur_rev = qf.loc["Total Revenue", cols[0]]
            if not pd.isna(cur_rev) and float(cur_rev) != 0:
                if "Net Income" in qf.index and not pd.isna(qf.loc["Net Income", cols[0]]):
                    fallback["profit_margin"] = float(qf.loc["Net Income", cols[0]]) / float(cur_rev)
                if "Operating Income" in qf.index and not pd.isna(qf.loc["Operating Income", cols[0]]):
                    fallback["operating_margin"] = float(qf.loc["Operating Income", cols[0]]) / float(cur_rev)

        # TTM P/E from quarterly net income + balance sheet shares
        if "Net Income" in qf.index:
            ni_vals = []
            for c in cols[:4]:  # last 4 quarters
                v = qf.loc["Net Income", c]
                if not pd.isna(v):
                    ni_vals.append(float(v))
            if len(ni_vals) >= 2:  # at least 2 quarters
                ttm_ni = sum(ni_vals)
                if ttm_ni > 0:
                    try:
                        bs = stock.balance_sheet
                        hist = stock.history(period="5d")
                        if bs is not None and not bs.empty and not hist.empty:
                            shares_row = next((r for r in ["Ordinary Shares Number", "Share Issued"] if r in bs.index), None)
                            if shares_row:
                                shares = float(bs.loc[shares_row].dropna().values[0])
                                price = float(hist["Close"].iloc[-1])
                                eps = ttm_ni / shares
                                if eps > 0:
                                    fallback["pe_ratio"] = round(price / eps, 2)
                            # P/B while we have bs loaded
                            eq_row = next((r for r in ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"] if r in bs.index), None)
                            if eq_row and shares_row:
                                equity = float(bs.loc[eq_row].dropna().values[0])
                                shares = float(bs.loc[shares_row].dropna().values[0])
                                price = float(hist["Close"].iloc[-1])
                                if equity > 0 and shares > 0:
                                    bvps = equity / shares
                                    fallback["price_to_book"] = round(price / bvps, 2)
                    except Exception:
                        pass
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

    # Use continuous item_score (0-100) weighted by importance for precise scoring
    weighted_total = 0.0
    weighted_score = 0.0
    for item in scored_items:
        weight = max(20, float(item.get("importance", 40)))
        if "item_score" in item:
            # Use continuous 0-100 score for precision
            weighted_score += float(item["item_score"]) * weight
        else:
            # Fallback for commodity items that don't have item_score
            signal_score = 80.0 if item["status"] == "positive" else (20.0 if item["status"] == "negative" else 50.0)
            weighted_score += signal_score * weight
        weighted_total += weight

    summary_score = round(max(0, min(100, weighted_score / weighted_total))) if weighted_total else 50
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


def _load_top_pick_name_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    try:
        for sector in StockDataService._load_sectors():
            for stock in sector.get("stocks", []):
                ticker = _ticker_key(stock.get("ticker", ""))
                name = str(stock.get("name", "")).strip()
                if ticker and name:
                    mapping[ticker] = name
    except Exception:
        pass
    return mapping


TOP_PICK_NAME_MAP = _load_top_pick_name_map()

# Ensure all TOP_PICK_SECTOR_MAP tickers have a name — fallback for tickers missing from sectors.json
_FALLBACK_NAMES: dict[str, str] = {
    "NVDA": "엔비디아", "TSM": "TSMC", "AVGO": "브로드컴",
    "000660.KS": "SK하이닉스", "005930.KS": "삼성전자",
    "TSLA": "테슬라", "ISRG": "인튜이티브서지컬",
    "CEG": "컨스텔레이션에너지", "CCJ": "카메코",
    "CRWD": "크라우드스트라이크", "PANW": "팔로알토네트웍스",
    "FTNT": "포티넷", "ZS": "지스케일러", "S": "센티넬원",
    "RKLB": "로켓랩", "LMT": "록히드마틴", "BA": "보잉",
    "CRSP": "크리스퍼테라퓨틱스", "LLY": "일라이릴리", "ILMN": "일루미나",
    "207940.KS": "삼성바이오로직스", "068270.KS": "셀트리온",
    "IONQ": "아이온큐", "GOOG": "구글(알파벳)", "IBM": "IBM",
    "RGTI": "리게티컴퓨팅", "MSFT": "마이크로소프트",
    "BE": "블룸에너지", "PLUG": "플러그파워", "ENPH": "엔페이즈에너지",
    "005380.KS": "현대자동차", "336260.KS": "두산퓨얼셀",
    "086520.KS": "에코프로", "247540.KS": "에코프로비엠",
    "373220.KS": "LG에너지솔루션", "006400.KS": "삼성SDI",
    "047810.KS": "한국항공우주", "012450.KS": "한화에어로스페이스",
    "267250.KS": "현대로보틱스", "034020.KS": "두산에너빌리티",
    "BWXT": "BWX Technologies",
}
for _tk, _nm in _FALLBACK_NAMES.items():
    if _ticker_key(_tk) not in TOP_PICK_NAME_MAP:
        TOP_PICK_NAME_MAP[_ticker_key(_tk)] = _nm


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

    if any(keyword in text for keyword in ["semiconductor", "chip", "foundry", "memory", "gpu"]):
        return "ai-semi"
    if any(keyword in text for keyword in ["robot", "automation", "auto manufacturer", "machinery"]):
        return "robotics"
    if any(keyword in text for keyword in ["uranium", "nuclear", "utility", "power generation"]):
        return "smr-nuclear"
    if any(keyword in text for keyword in ["cyber", "security", "cloud software", "software - infrastructure"]):
        return "cybersec"
    if any(keyword in text for keyword in ["defense", "weapon", "missile", "military", "munition",
                                            "방산", "방위", "군수", "군사", "무기", "탄약",
                                            "한화에어로", "한국항공우주", "한화디펜스", "LIG넥스원"]):
        return "defense-geo"
    if any(keyword in text for keyword in ["aerospace", "space", "satellite", "aircraft"]):
        return "space"
    if any(keyword in text for keyword in ["biotech", "drug", "pharma", "healthcare", "genomics", "life sciences"]):
        return "biotech"
    if any(keyword in text for keyword in ["quantum", "superconduct"]):
        return "quantum"
    if any(keyword in text for keyword in ["hydrogen", "fuel cell", "solar", "clean energy", "renewable"]):
        return "hydrogen"
    # Additional sectors — don't misclassify as ai-semi
    if any(keyword in text for keyword in ["battery", "lithium", "cathode", "anode", "electrolyte",
                                            "2차전지", "배터리", "양극재", "음극재", "전해질",
                                            "에코프로", "엘앤에프", "포스코퓨처엠",
                                            "삼성sdi", "lg에너지", "sk온", "에너지솔루션",
                                            "electrical equipment"]):
        return "battery"
    if any(keyword in text for keyword in ["electric vehicle", "ev ", "자동차", "auto", "motor",
                                            "운송장비", "차량", "automobile"]):
        return "ev"
    if any(keyword in text for keyword in ["chemical", "specialty chemical", "화학", "석유화학",
                                            "정밀화학", "기초화학"]):
        return "chemical"
    if any(keyword in text for keyword in ["steel", "metal", "mining", "철강", "광업", "금속",
                                            "비철금속", "철강금속"]):
        return "materials"
    if any(keyword in text for keyword in ["bank", "insurance", "financial", "은행", "보험", "증권",
                                            "금융", "캐피탈", "저축은행"]):
        return "financial"
    if any(keyword in text for keyword in ["전기전자", "display", "디스플레이", "반도체장비"]):
        return "ai-semi"
    if any(keyword in text for keyword in ["electronics", "consumer electronics"]):
        return "ai-semi"
    if any(keyword in text for keyword in ["software", "cloud", "saas", "platform", "internet",
                                            "소프트웨어", "it서비스", "게임"]):
        return "software"
    if any(keyword in text for keyword in ["food", "beverage", "consumer", "retail", "식품",
                                            "유통", "음식료", "생활용품"]):
        return "consumer"
    if any(keyword in text for keyword in ["construction", "engineering", "건설", "엔지니어링",
                                            "건설업"]):
        return "construction"
    if any(keyword in text for keyword in ["shipping", "logistics", "transportation", "해운",
                                            "물류", "운수", "항공"]):
        return "logistics"
    if any(keyword in text for keyword in ["telecom", "communication", "통신", "미디어",
                                            "방송", "광고"]):
        return "telecom"
    if any(keyword in text for keyword in ["의약품", "의료", "바이오", "제약", "헬스케어"]):
        return "biotech"
    if any(keyword in text for keyword in ["유틸리티", "전력", "가스", "수도"]):
        return "smr-nuclear"
    # Last resort: search news headlines to determine industry
    try:
        company_name = ""
        for field in ["shortName", "longName"]:
            v = payload.get(field)
            if v:
                company_name = str(v)
                break
        if not company_name and ticker:
            company_name = ticker.split(".")[0]
        if company_name:
            from services.news_crawler import NewsCrawlerService
            articles = NewsCrawlerService.crawl_google_news_rss(company_name, lang="ko")[:5]
            news_text = " ".join(getattr(a, "title", "") or "" for a in articles).lower()
            if any(kw in news_text for kw in ["배터리", "2차전지", "양극재", "리튬", "전지"]):
                return "battery"
            if any(kw in news_text for kw in ["반도체", "chip", "hbm", "메모리", "파운드리"]):
                return "ai-semi"
            if any(kw in news_text for kw in ["바이오", "임상", "신약", "의약"]):
                return "biotech"
            if any(kw in news_text for kw in ["자동차", "ev", "전기차"]):
                return "ev"
            if any(kw in news_text for kw in ["로봇", "자동화", "robot"]):
                return "robotics"
            if any(kw in news_text for kw in ["원전", "우라늄", "smr", "원자력"]):
                return "smr-nuclear"
            if any(kw in news_text for kw in ["보안", "사이버", "security"]):
                return "cybersec"
            if any(kw in news_text for kw in ["방산", "방위", "군수", "미사일", "전투기", "defense", "military"]):
                return "defense-geo"
            if any(kw in news_text for kw in ["수소", "연료전지", "태양광", "풍력"]):
                return "hydrogen"
            if any(kw in news_text for kw in ["화학", "석유화학", "정유"]):
                return "chemical"
    except Exception:
        pass

    # Default: None (will use generic checklist, NOT misclassify as semiconductor)
    return None


_INDUSTRY_CACHE: dict[str, tuple[float, dict]] = {}


# Fast static mapping for well-known Korean stocks (avoids Naver scraping delay)
_KRX_INDUSTRY_MAP: dict[str, dict] = {
    # 2차전지/배터리
    "086520": {"name": "에코프로", "industry": "2차전지", "sector": "battery"},
    "247540": {"name": "에코프로비엠", "industry": "2차전지 양극재", "sector": "battery"},
    "373220": {"name": "LG에너지솔루션", "industry": "배터리", "sector": "battery"},
    "006400": {"name": "삼성SDI", "industry": "배터리", "sector": "battery"},
    "003670": {"name": "포스코퓨처엠", "industry": "2차전지 소재", "sector": "battery"},
    "066970": {"name": "엘앤에프", "industry": "양극재", "sector": "battery"},
    # 방산
    "012450": {"name": "한화에어로스페이스", "industry": "방산", "sector": "defense-geo"},
    "047810": {"name": "한국항공우주", "industry": "방산", "sector": "defense-geo"},
    "079550": {"name": "LIG넥스원", "industry": "방산", "sector": "defense-geo"},
    "272210": {"name": "한화시스템", "industry": "방산", "sector": "defense-geo"},
    # 반도체
    "000660": {"name": "SK하이닉스", "industry": "반도체", "sector": "ai-semi"},
    "005930": {"name": "삼성전자", "industry": "전자", "sector": "ai-semi"},
    # 바이오
    "207940": {"name": "삼성바이오로직스", "industry": "바이오", "sector": "biotech"},
    "068270": {"name": "셀트리온", "industry": "바이오시밀러", "sector": "biotech"},
    # 자동차
    "005380": {"name": "현대자동차", "industry": "자동차", "sector": "ev"},
    "000270": {"name": "기아", "industry": "자동차", "sector": "ev"},
}


def _fetch_stock_industry(ticker: str) -> dict:
    """
    Actively fetch industry/sector info for a stock when yfinance is empty.
    Korean stocks: check static map first, then scrape Naver Finance.
    US stocks: scrape Yahoo Finance summary page.
    Returns dict with keys: industry, sector, name, market_cap.
    """
    cache_key = f"industry:{ticker}"
    cached = _INDUSTRY_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < 86400:  # 24h cache
        return cached[1]

    result: dict = {}
    is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")

    # Fast static lookup for well-known Korean stocks
    if is_krx:
        code = ticker.split(".")[0]
        static = _KRX_INDUSTRY_MAP.get(code)
        if static:
            result = dict(static)
            _INDUSTRY_CACHE[cache_key] = (time.time(), result)
            return result

    if is_krx:
        code = ticker.split(".")[0]
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            with limit_http():
                r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                # 종목명
                name_el = soup.select_one("div.wrap_company h2 a")
                if name_el:
                    result["name"] = name_el.get_text(strip=True)
                # 업종 (sector category)
                blind_els = soup.select("div.section div.sub_section")
                for section in blind_els:
                    text = section.get_text()
                    if "업종" in text:
                        a_tag = section.select_one("a")
                        if a_tag:
                            result["industry"] = a_tag.get_text(strip=True)
                            break
                # Also check the "belongs to" category link
                category_el = soup.select_one("div.trade_compare em a")
                if category_el:
                    result["industry"] = category_el.get_text(strip=True)
                # Try 종목 프로필 for more detail
                profile_url = f"https://finance.naver.com/item/coinfo.naver?code={code}"
                with limit_http():
                    r2 = requests.get(profile_url, headers=headers, timeout=8)
                if r2.status_code == 200:
                    soup2 = BeautifulSoup(r2.text, "html.parser")
                    for td in soup2.select("td"):
                        t = td.get_text(strip=True)
                        if "업종" in t:
                            next_td = td.find_next_sibling("td")
                            if next_td:
                                result["industry"] = next_td.get_text(strip=True)
                                break
        except Exception:
            pass
    else:
        # US stocks: try Yahoo Finance summary
        try:
            if _cffi_available:
                from curl_cffi.requests import Session as CffiSession
                session = CffiSession(impersonate="chrome")
                r = session.get(f"https://finance.yahoo.com/quote/{ticker}/", timeout=10)
            else:
                with limit_http():
                    r = requests.get(f"https://finance.yahoo.com/quote/{ticker}/",
                                     headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                # Look for sector/industry in the page
                for span in soup.select("span"):
                    text = span.get_text(strip=True)
                    if text in ("Sector", "Industry"):
                        next_span = span.find_next("span")
                        if next_span:
                            if text == "Sector":
                                result["sector"] = next_span.get_text(strip=True)
                            else:
                                result["industry"] = next_span.get_text(strip=True)
        except Exception:
            pass

    if result:
        _INDUSTRY_CACHE[cache_key] = (time.time(), result)
    return result


def _build_dynamic_checklist_sources(ticker: str, info: dict | None = None) -> list[dict]:
    """Build intelligent, stock-specific checklist sources based on industry analysis.

    For any stock not in the pre-built CHECKLIST_SOURCES, this analyzes the company's
    industry, business type, financial profile, and competitive landscape to generate
    a tailored checklist similar in quality to hand-crafted ones.

    If yfinance info is empty (rate limited), actively fetches industry from
    Naver Finance (Korean) or Yahoo Finance (US) to ensure correct classification.
    """
    info = info or {}

    # If yfinance info is empty, actively search for industry info
    industry_raw = str(info.get("industry") or "").lower()
    yf_sector = str(info.get("sector") or "").lower()
    name = str(info.get("shortName") or info.get("longName") or ticker)

    if not industry_raw and not yf_sector:
        # yfinance failed — actively fetch from Naver/Yahoo
        fetched = _fetch_stock_industry(ticker)
        if fetched:
            industry_raw = str(fetched.get("industry") or "").lower()
            yf_sector = str(fetched.get("sector") or "").lower()
            if fetched.get("name") and name == ticker:
                name = fetched["name"]
            # Merge into info for downstream use
            if not info.get("industry"):
                info["industry"] = fetched.get("industry", "")
            if not info.get("sector"):
                info["sector"] = fetched.get("sector", "")
            if not info.get("shortName"):
                info["shortName"] = fetched.get("name", ticker)

    sector_id = _infer_sector_id_from_profile(ticker, info=info)
    industry = industry_raw
    market_cap = info.get("marketCap") or 0
    profit_margin = info.get("profitMargins")
    revenue_growth = info.get("revenueGrowth")
    is_profitable = profit_margin is not None and profit_margin > 0
    is_high_growth = revenue_growth is not None and revenue_growth > 0.15
    is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")

    dynamic_sources: list[dict] = []

    # ── Sector-specific tailored checklists (like pre-built, per stock) ──
    SECTOR_CHECKLISTS: dict[str, list[dict]] = {
        "battery": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.1, weight=90,
               thesis=f"{name}의 양극재/배터리 소재 출하량이 매출 성장에 직결됩니다. EV 수요 둔화 시 가장 먼저 타격.", window="향후 1~2분기"),
            ck(f"{name} 영업이익률", "earnings_metric", metric="operating_margin",
               positive_if="above", threshold=0.05, weight=92,
               thesis=f"리튬 가격 하락기에 {name}의 마진 방어가 밸류에이션의 핵심입니다.", window="향후 1~2분기"),
            ck("리튬 가격 (LIT)", "commodity", symbol="LIT", positive_if="up", weight=88,
               thesis=f"리튬 가격은 {name}의 양극재 ASP와 직접 연동됩니다. 가격 하락 = 매출 감소.", window="향후 1~3개월"),
            ck("니켈 가격 (원가 압박)", "commodity", symbol="NI=F", positive_if="down", weight=72,
               thesis=f"니켈은 양극재 핵심 원료입니다. 니켈 급등 시 {name}의 원가 부담이 커집니다.", window="향후 1~3개월"),
            ck("EV 판매 추이 (DRIV)", "commodity", symbol="DRIV", positive_if="up", weight=78,
               thesis="글로벌 EV 판매 기대가 꺾이면 배터리 소재 수요도 함께 줄어듭니다.", window="향후 1~3개월"),
            ck("고객사 (LG에너지솔루션)", "commodity", symbol="373220.KS", positive_if="up", weight=65,
               thesis="LG에너지솔루션 등 고객사 주가는 배터리 밸류체인 기대를 선반영합니다.", window="향후 1~3개월"),
            ck("경쟁사 (포스코퓨처엠)", "commodity", symbol="003670.KS", positive_if="down", weight=55,
               thesis="경쟁사 주가가 강해지면 시장 점유율 경쟁 우려가 커질 수 있습니다.", window="향후 1~3개월"),
            ck(f"{name} ROE", "earnings_metric", metric="roe",
               positive_if="above", threshold=0.05, weight=60,
               thesis=f"적자 탈출 여부가 {name} 주가 방향을 결정합니다.", window="향후 2~4분기"),
        ],
        "ev": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.08, weight=88,
               thesis=f"{name}의 차량 인도량/매출 성장 둔화가 확인되면 기대감이 먼저 무너집니다.", window="향후 1~2분기"),
            ck(f"{name} 이익률", "earnings_metric", metric="profit_margin",
               positive_if="above", threshold=0.05, weight=92,
               thesis=f"{name}의 마진 방향이 주가를 가장 크게 좌우합니다.", window="향후 1~2분기"),
            ck("배터리 원가 (리튬 ETF)", "commodity", symbol="LIT", positive_if="down", weight=75,
               thesis="리튬 가격 하락은 배터리 원가 절감으로 마진 개선에 유리합니다.", window="향후 1~3개월"),
            ck("EV 섹터 심리 (DRIV)", "commodity", symbol="DRIV", positive_if="up", weight=72,
               thesis="EV 밸류체인 심리가 꺾이면 개별주 프리미엄도 같이 압축됩니다.", window="향후 1~3개월"),
            ck("원유 가격", "commodity", symbol="CL=F", positive_if="up", weight=55,
               thesis="유가 상승은 EV 전환 기대를 높이지만, 소비심리는 약화시킬 수 있습니다.", window="향후 1~3개월"),
        ],
        "chemical": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.05, weight=82,
               thesis=f"화학 업황 턴어라운드가 {name} 매출 성장으로 이어지는지가 핵심입니다.", window="향후 1~2분기"),
            ck(f"{name} 영업이익률", "earnings_metric", metric="operating_margin",
               positive_if="above", threshold=0.08, weight=90,
               thesis=f"나프타/원료 가격과 제품 스프레드가 {name}의 마진을 결정합니다.", window="향후 1~2분기"),
            ck("원유 가격 (나프타 원가)", "commodity", symbol="CL=F", positive_if="down", weight=78,
               thesis="유가 하락은 화학 기업의 원료비 절감으로 직결됩니다.", window="향후 1~3개월"),
            ck("소재 섹터 (XLB)", "commodity", symbol="XLB", positive_if="up", weight=65,
               thesis="소재 섹터 전체 사이클이 개별 화학주에 직접적으로 영향을 줍니다.", window="향후 1~3개월"),
        ],
        "materials": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.05, weight=85,
               thesis=f"글로벌 산업 수요 회복이 {name} 매출에 직결됩니다.", window="향후 1~2분기"),
            ck(f"{name} 영업이익률", "earnings_metric", metric="operating_margin",
               positive_if="above", threshold=0.08, weight=88,
               thesis=f"원자재 가격과 수요 사이클이 {name}의 마진을 결정합니다.", window="향후 1~2분기"),
            ck("구리 가격", "commodity", symbol="HG=F", positive_if="up", weight=75,
               thesis="산업 금속 수요의 전반적 트렌드를 반영합니다.", window="향후 1~3개월"),
            ck("소재 ETF (XLB)", "commodity", symbol="XLB", positive_if="up", weight=68,
               thesis="소재 섹터 전체 자금 흐름과 사이클을 보여줍니다.", window="향후 1~3개월"),
        ],
        "financial": [
            ck(f"{name} 이익률", "earnings_metric", metric="profit_margin",
               positive_if="above", threshold=0.15, weight=88,
               thesis=f"금리 환경과 건전성이 {name}의 수익성을 결정합니다.", window="향후 1~2분기"),
            ck(f"{name} ROE", "earnings_metric", metric="roe",
               positive_if="above", threshold=0.08, weight=85,
               thesis=f"금융주는 ROE가 자본 효율성의 핵심 지표입니다.", window="향후 2~4분기"),
            ck("금융 ETF (XLF)", "commodity", symbol="XLF", positive_if="up", weight=78,
               thesis="금융 섹터 전체 심리와 금리 기대를 반영합니다.", window="향후 1~3개월"),
            ck("장기채 (TLT)", "commodity", symbol="TLT", positive_if="down", weight=72,
               thesis="금리 상승(채권 하락)은 은행 NIM에 유리하지만, 건전성에 부담을 줄 수 있습니다.", window="향후 1~3개월"),
        ],
        "software": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.15, weight=90,
               thesis=f"SaaS/소프트웨어 기업에서 매출 성장 둔화는 멀티플 압축의 직접 트리거입니다.", window="향후 1~2분기"),
            ck(f"{name} 이익률", "earnings_metric", metric="profit_margin",
               positive_if="above", threshold=0.1, weight=85,
               thesis=f"{name}의 수익성 개선이 밸류에이션 프리미엄 유지의 핵심입니다.", window="향후 1~2분기"),
            ck("소프트웨어 ETF (IGV)", "commodity", symbol="IGV", positive_if="up", weight=75,
               thesis="소프트웨어 업종 전체 밸류에이션 흐름을 반영합니다.", window="향후 1~3개월"),
            ck("빅테크 심리 (QQQ)", "commodity", symbol="QQQ", positive_if="up", weight=65,
               thesis="기술주 위험선호 변화가 직접적으로 영향을 줍니다.", window="향후 1~3개월"),
        ],
        "consumer": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.05, weight=85,
               thesis=f"소비재 기업은 매출 성장이 시장 점유율 유지의 핵심입니다.", window="향후 1~2분기"),
            ck(f"{name} 이익률", "earnings_metric", metric="profit_margin",
               positive_if="above", threshold=0.08, weight=88,
               thesis=f"원가 상승 압박 속에서 마진 방어가 주가 방향을 결정합니다.", window="향후 1~2분기"),
            ck("경기소비재 ETF (XLY)", "commodity", symbol="XLY", positive_if="up", weight=72,
               thesis="소비 경기 사이클이 개별 소비재 기업에 직접적으로 영향합니다.", window="향후 1~3개월"),
        ],
        "construction": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.05, weight=85,
               thesis=f"수주 잔고와 착공 실적이 {name} 매출로 직결됩니다.", window="향후 1~2분기"),
            ck(f"{name} 영업이익률", "earnings_metric", metric="operating_margin",
               positive_if="above", threshold=0.06, weight=88,
               thesis=f"원자재 가격과 공사 수익성이 마진을 결정합니다.", window="향후 1~2분기"),
            ck("주택건설 ETF (XHB)", "commodity", symbol="XHB", positive_if="up", weight=72,
               thesis="건설/주택 경기 전체 흐름을 반영합니다.", window="향후 1~3개월"),
        ],
        "logistics": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.05, weight=85,
               thesis=f"물동량 회복이 {name} 매출 성장에 직결됩니다.", window="향후 1~2분기"),
            ck("원유 가격", "commodity", symbol="CL=F", positive_if="down", weight=78,
               thesis="연료비가 해운/물류 기업 수익의 핵심 변수입니다.", window="향후 1~3개월"),
        ],
        "telecom": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.03, weight=80,
               thesis=f"통신 기업은 안정적 매출 성장 유지가 핵심입니다.", window="향후 1~2분기"),
            ck(f"{name} 배당수익률", "earnings_metric", metric="dividend_yield",
               positive_if="above", threshold=0.03, weight=75,
               thesis=f"통신주는 배당 매력이 밸류에이션의 핵심 요소입니다.", window="향후 2~4분기"),
            ck("통신서비스 ETF (XLC)", "commodity", symbol="XLC", positive_if="up", weight=65,
               thesis="통신/미디어 섹터 전체 심리를 반영합니다.", window="향후 1~3개월"),
        ],
        "defense-geo": [
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
               positive_if="above", threshold=0.05, weight=82,
               thesis=f"{name}의 수주가 실제 매출로 전환되는지가 핵심입니다.", window="향후 1~2분기"),
            ck(f"{name} 영업이익률", "earnings_metric", metric="operating_margin",
               positive_if="above", threshold=0.06, weight=88,
               thesis=f"방산 기업은 수주만 많아도 마진이 뒷받침돼야 주가가 유지됩니다.", window="향후 1~2분기"),
            ck("방산 ETF (ITA)", "commodity", symbol="ITA", positive_if="up", weight=85,
               thesis="글로벌 국방비 증가 기대가 방산주 전체 프리미엄을 좌우합니다.", window="향후 1~3개월"),
            ck("유가 (지정학 프록시)", "commodity", symbol="CL=F", positive_if="up", weight=72,
               thesis="유가 급등은 지정학 리스크 심화의 신호이며 방산 수요 기대를 높입니다.", window="향후 1~3개월"),
            ck("금 가격 (안전자산)", "commodity", symbol="GC=F", positive_if="up", weight=65,
               thesis="금 강세는 지정학 불안 → 방산주 수혜 시나리오를 지지합니다.", window="향후 1~3개월"),
        ],
    }

    # Use sector-specific tailored checklist if available
    if sector_id and sector_id in SECTOR_CHECKLISTS:
        dynamic_sources = list(SECTOR_CHECKLISTS[sector_id])
    else:
        # Generic: core financial metrics
        margin_threshold = 0.15 if is_profitable else 0.0
        margin_thesis = (
            f"{name}의 수익성이 유지되는지가 밸류에이션 프리미엄의 핵심입니다."
            if is_profitable else
            f"{name}은 아직 적자 상태로, 흑자전환 시점이 주가 방향을 결정합니다."
        )
        dynamic_sources.append(
            ck(f"{name} 영업이익률", "earnings_metric", metric="profit_margin",
               positive_if="above", threshold=margin_threshold, weight=90,
               thesis=margin_thesis, window="향후 1~2분기")
        )
        dynamic_sources.append(
            ck(f"{name} 매출 성장률", "earnings_metric", metric="revenue_growth",
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
        "battery": [
            {"symbol": "LIT", "label": "리튬/배터리 ETF", "why": "2차전지 밸류체인 전체 심리와 리튬 수급을 반영합니다."},
            {"symbol": "BATT", "label": "배터리 테크 ETF", "why": "배터리 기술주 전체 자금 흐름을 보여줍니다."},
        ],
        "electric vehicle": [
            {"symbol": "LIT", "label": "리튬/배터리 ETF", "why": "EV 배터리 원자재 가격과 수요를 반영합니다."},
            {"symbol": "DRIV", "label": "EV/자율주행 ETF", "why": "EV 섹터 전체 기대감 변화를 보여줍니다."},
        ],
        "ev": [
            {"symbol": "LIT", "label": "리튬/배터리 ETF", "why": "배터리 원자재 가격이 EV 밸류체인 마진에 직결됩니다."},
            {"symbol": "DRIV", "label": "EV/자율주행 ETF", "why": "EV 밸류체인 전체 심리를 반영합니다."},
        ],
        "cathode": [
            {"symbol": "LIT", "label": "리튬/배터리 ETF", "why": "양극재 기업은 리튬 가격과 EV 배터리 수요에 직접 연동됩니다."},
        ],
        "chemical": [
            {"symbol": "XLB", "label": "소재 ETF", "why": "소재 섹터 전체 사이클을 반영합니다."},
        ],
        "materials": [
            {"symbol": "XLB", "label": "소재 ETF", "why": "소재/금속 섹터 사이클을 반영합니다."},
            {"symbol": "HG=F", "label": "구리", "why": "산업 금속 수요의 전반적 트렌드를 보여줍니다."},
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
    # Also use sector_id for matching (handles Korean stocks where yfinance info is empty)
    matched_peers: list[dict] = []
    # Map sector_id to industry keyword for matching
    SECTOR_TO_INDUSTRY = {
        "ai-semi": "semiconductor", "robotics": "auto", "smr-nuclear": "utility",
        "cybersec": "software", "space": "aerospace", "biotech": "biotech",
        "quantum": "software", "hydrogen": "energy", "battery": "battery",
        "ev": "electric vehicle", "chemical": "chemical", "materials": "steel",
        "financial": "financial", "software": "software", "consumer": "consumer",
        "construction": "construction", "logistics": "shipping", "telecom": "telecom",
    }
    sector_industry = SECTOR_TO_INDUSTRY.get(sector_id or "", "")
    for keyword, peers in INDUSTRY_PEERS.items():
        if keyword in industry or keyword in yf_sector or keyword == sector_industry:
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
        if ind_key in industry or ind_key == sector_industry:
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

    # ── 7. Geopolitical / Macro risk items (대외이슈) ──
    # Add oil/gold/VIX as geopolitical risk proxies for all stocks
    geo_items = []
    if "CL=F" not in seen_symbols:
        geo_items.append(
            ck("유가 (지정학 리스크)", "commodity", symbol="CL=F",
               positive_if="stable", weight=45,
               thesis="유가 급등은 이란·중동 리스크 심화 신호이며, 인플레이션과 공급망 교란으로 전 업종에 영향을 줍니다.",
               window="향후 1~3개월")
        )
    if "GC=F" not in seen_symbols:
        geo_items.append(
            ck("금 가격 (안전자산 선호)", "commodity", symbol="GC=F",
               positive_if="stable", weight=40,
               thesis="금 급등은 지정학 불안과 경기 침체 우려를 반영합니다. 위험자산 선호 약화 시그널.",
               window="향후 1~3개월")
        )
    # For Korean stocks, add additional geopolitical sensitivity
    if is_krx and "KRW=X" not in seen_symbols:
        geo_items.append(
            ck("원/달러 환율 (대외 리스크)", "commodity", symbol="KRW=X",
               positive_if="stable", weight=48,
               thesis="지정학 리스크 확대 시 원화 급락 → 외국인 자금 이탈, 수입 원자재 원가 상승으로 이중 타격.",
               window="향후 1~3개월")
        )
    dynamic_sources.extend(geo_items)

    # Dedup: remove duplicate commodity symbols (sector template + generic may overlap)
    seen_syms: set[str] = set()
    deduped: list[dict] = []
    for src in dynamic_sources:
        if src["type"] == "commodity":
            sym = src.get("symbol", "")
            if sym in seen_syms:
                continue
            seen_syms.add(sym)
        deduped.append(src)
    return deduped


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
        with limit_http():
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
def get_analysis(ticker: str) -> AnalysisResult:
    """Full technical analysis with buy/sell signal for a ticker."""
    cache_key = f"analysis:{_ticker_key(ticker)}"

    def _produce() -> AnalysisResult:
        df = StockDataService.get_stock_history(ticker, period="6mo")

        rsi = TechnicalAnalysisService.calculate_rsi(df)
        macd_val, macd_signal, _ = TechnicalAnalysisService.calculate_macd(df)
        bb_upper, bb_middle, bb_lower = TechnicalAnalysisService.calculate_bollinger_bands(df)
        smas = TechnicalAnalysisService.calculate_sma(df)
        recommendation, confidence = TechnicalAnalysisService.generate_buy_sell_signal(df)

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
            buy_sell_signal=recommendation,
        )

        return AnalysisResult(
            ticker=ticker.upper(),
            indicators=indicators,
            recommendation=recommendation,
            confidence_score=confidence,
        )

    return _run_singleflight(cache_key, _produce, ttl=1800, model_cls=AnalysisResult)


@router.get("/analysis/{ticker}/trading-targets")
def get_trading_targets(ticker: str) -> dict:
    """
    Calculate precise buy/sell/stop targets using multi-indicator analysis.
    Uses: Support/Resistance levels, Fibonacci retracement, RSI zones,
    Bollinger bands, SMA crossovers, volume profile, MACD momentum.
    """
    cache_key = f"targets:{ticker}"
    cached = _get_cached_ttl(cache_key, 600)
    if cached is not None:
        return cached

    # Get longer history for better analysis
    df_long = StockDataService.get_stock_history(ticker, period="1y")
    df_3mo = StockDataService.get_stock_history(ticker, period="3mo")

    if df_long.empty or len(df_long) < 20:
        return {"ticker": ticker, "targets": None, "reasons": []}

    close = df_long["Close"]
    high = df_long["High"]
    low = df_long["Low"]
    volume = df_long["Volume"]
    price = float(close.iloc[-1])

    # ── 1. Support & Resistance from recent pivots ──
    supports = []
    resistances = []
    window = 10
    for i in range(window, len(df_long) - window):
        is_support = all(float(low.iloc[i]) <= float(low.iloc[i-j]) for j in range(1, window+1)) and \
                     all(float(low.iloc[i]) <= float(low.iloc[i+j]) for j in range(1, min(window+1, len(df_long)-i)))
        is_resistance = all(float(high.iloc[i]) >= float(high.iloc[i-j]) for j in range(1, window+1)) and \
                        all(float(high.iloc[i]) >= float(high.iloc[i+j]) for j in range(1, min(window+1, len(df_long)-i)))
        if is_support:
            supports.append(float(low.iloc[i]))
        if is_resistance:
            resistances.append(float(high.iloc[i]))

    # Cluster nearby levels (within 2% of each other)
    def _cluster_levels(levels: list[float], tolerance: float = 0.02) -> list[float]:
        if not levels:
            return []
        levels.sort()
        clusters = [[levels[0]]]
        for lv in levels[1:]:
            if abs(lv - clusters[-1][-1]) / clusters[-1][-1] < tolerance:
                clusters[-1].append(lv)
            else:
                clusters.append([lv])
        return [sum(c) / len(c) for c in clusters]

    support_levels = _cluster_levels(supports)
    resistance_levels = _cluster_levels(resistances)

    # ── 2. Fibonacci retracement ──
    recent_high = float(high.tail(60).max())
    recent_low = float(low.tail(60).min())
    fib_range = recent_high - recent_low
    fib_levels = {
        "0.236": recent_high - fib_range * 0.236,
        "0.382": recent_high - fib_range * 0.382,
        "0.500": recent_high - fib_range * 0.500,
        "0.618": recent_high - fib_range * 0.618,
        "0.786": recent_high - fib_range * 0.786,
    }

    # ── 3. SMAs as dynamic support/resistance ──
    sma_20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
    sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    # ── 4. Bollinger Bands ──
    bb_mid = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else price
    bb_std = float(close.rolling(20).std().iloc[-1]) if len(close) >= 20 else 0
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    # ── 5. RSI ──
    rsi = TechnicalAnalysisService.calculate_rsi(df_long)

    # ── 6. MACD ──
    macd_val, macd_signal, macd_hist = TechnicalAnalysisService.calculate_macd(df_long)

    # ── 7. ATR (Average True Range) for volatility-adjusted targets ──
    tr = pd.DataFrame({
        "hl": high - low,
        "hc": abs(high - close.shift(1)),
        "lc": abs(low - close.shift(1)),
    }).max(axis=1)
    atr_14 = float(tr.rolling(14).mean().iloc[-1]) if len(tr) >= 14 else float(tr.mean())
    atr_pct = atr_14 / price * 100  # ATR as % of price

    # ── 8. Volume-weighted price analysis ──
    recent_vwap = float((close.tail(20) * volume.tail(20)).sum() / volume.tail(20).sum()) if len(close) >= 20 else price

    # ── 9. Trend strength: ADX-like (using price vs SMAs) ──
    sma_values = [v for v in [sma_20, sma_50, sma_200] if v is not None]
    bullish_smas = sum(1 for s in sma_values if price > s)
    trend_strength = bullish_smas / len(sma_values) if sma_values else 0.5  # 0=bearish, 1=bullish

    # ── 10. Recent momentum (last 5 days) ──
    if len(close) >= 5:
        momentum_5d = (price - float(close.iloc[-5])) / float(close.iloc[-5]) * 100
    else:
        momentum_5d = 0

    # ═══════════════════════════════════════
    # CALCULATE SMART TARGETS
    # ═══════════════════════════════════════

    buy_reasons = []
    sell_reasons = []
    stop_reasons = []

    # ── BUY TARGET: Find the best entry point ──
    buy_candidates = []

    # Support levels below current price
    nearby_supports = [s for s in support_levels if s < price * 0.99]
    if nearby_supports:
        best_support = max(nearby_supports)  # closest support below
        buy_candidates.append(("지지선", best_support, f"과거 반등 지지선 ₩{round(best_support):,} — 이 가격대에서 {len([s for s in supports if abs(s - best_support)/best_support < 0.02])}회 반등 이력"))

    # Fibonacci levels below price
    for fib_name, fib_val in fib_levels.items():
        if fib_val < price * 0.98 and fib_val > price * 0.80:
            buy_candidates.append(("피보나치", fib_val, f"피보나치 {fib_name} 되돌림 (₩{round(fib_val):,}) — 기술적 매수 구간"))

    # Bollinger lower band
    if bb_lower < price * 0.99:
        buy_candidates.append(("볼린저 하단", bb_lower, f"볼린저밴드 하단 ₩{round(bb_lower):,} — 과매도 반등 기대 구간"))

    # SMA support
    for name, sma_val in [("20일선", sma_20), ("50일선", sma_50), ("200일선", sma_200)]:
        if sma_val and sma_val < price * 0.99 and sma_val > price * 0.85:
            buy_candidates.append(("이동평균선", sma_val, f"{name} ₩{round(sma_val):,} — 이동평균선 지지 매수"))

    # VWAP
    if recent_vwap < price * 0.98:
        buy_candidates.append(("VWAP", recent_vwap, f"20일 거래량가중평균가 ₩{round(recent_vwap):,} — 매물대 지지"))

    # Sort by proximity to current price (closest = most likely to reach)
    buy_candidates.sort(key=lambda x: abs(x[1] - price))

    # Pick best buy target: consider trend strength
    if buy_candidates:
        if trend_strength >= 0.7:
            # Strong uptrend: buy closer to current price (shallow dip)
            buy_target = buy_candidates[0][1]
            buy_reasons = [buy_candidates[0][2]]
            if len(buy_candidates) > 1:
                buy_reasons.append(f"2차 매수: {buy_candidates[1][2]}")
        else:
            # Weak/bearish: buy at deeper support
            buy_target = buy_candidates[min(1, len(buy_candidates)-1)][1]
            buy_reasons = [buy_candidates[min(1, len(buy_candidates)-1)][2]]
            if buy_candidates:
                buy_reasons.insert(0, f"1차 매수: {buy_candidates[0][2]}")
    else:
        # Fallback: ATR-based
        buy_target = price * (1 - max(atr_pct * 1.5, 3) / 100)
        buy_reasons = [f"ATR 기반 매수 구간 (변동성 {atr_pct:.1f}% × 1.5배 하단)"]

    # ── SELL TARGET: Find the best profit-taking point ──
    sell_candidates = []

    # Resistance levels above current price
    nearby_resistances = [r for r in resistance_levels if r > price * 1.01]
    if nearby_resistances:
        best_resistance = min(nearby_resistances)  # closest resistance above
        sell_candidates.append(("저항선", best_resistance, f"과거 저항선 ₩{round(best_resistance):,} — 이 가격대에서 {len([r for r in resistances if abs(r - best_resistance)/best_resistance < 0.02])}회 하락 반전 이력"))

    # Fibonacci levels above price
    for fib_name, fib_val in fib_levels.items():
        if fib_val > price * 1.03:
            sell_candidates.append(("피보나치", fib_val, f"피보나치 {fib_name} 저항 (₩{round(fib_val):,}) — 기술적 매도 구간"))

    # Bollinger upper band
    if bb_upper > price * 1.02:
        sell_candidates.append(("볼린저 상단", bb_upper, f"볼린저밴드 상단 ₩{round(bb_upper):,} — 과매수 주의 구간"))

    # Recent high
    if recent_high > price * 1.03:
        sell_candidates.append(("전고점", recent_high, f"최근 고점 ₩{round(recent_high):,} — 돌파 전 차익실현 구간"))

    # Sort by distance from current price
    sell_candidates.sort(key=lambda x: x[1])

    # Pick sell target considering trend and verdict
    # Minimum sell distance depends on trend strength and volatility
    if trend_strength >= 0.7:
        min_sell_pct = max(10, atr_pct * 4)  # Strong trend: aim high (10%+ or 4x ATR)
    elif trend_strength >= 0.4:
        min_sell_pct = max(8, atr_pct * 3)   # Moderate: 8%+ or 3x ATR
    else:
        min_sell_pct = max(5, atr_pct * 2)   # Weak: 5%+ or 2x ATR

    min_sell_price = price * (1 + min_sell_pct / 100)

    # Filter sell candidates that are above minimum distance
    strong_sells = [s for s in sell_candidates if s[1] >= min_sell_price]
    close_sells = [s for s in sell_candidates if s[1] < min_sell_price and s[1] > price]

    if strong_sells:
        if trend_strength >= 0.7 and (rsi is None or rsi < 65) and len(strong_sells) > 1:
            # Strong trend + not overbought: aim for 2nd target
            sell_target = strong_sells[min(1, len(strong_sells) - 1)][1]
            sell_reasons = [strong_sells[min(1, len(strong_sells) - 1)][2]]
            sell_reasons.insert(0, f"1차 익절: {strong_sells[0][2]}")
        else:
            sell_target = strong_sells[0][1]
            sell_reasons = [strong_sells[0][2]]
            if len(strong_sells) > 1:
                sell_reasons.append(f"2차 목표: {strong_sells[1][2]}")
        # Add close resistance as partial take-profit note
        if close_sells:
            sell_reasons.append(f"참고 — 단기 저항: {close_sells[0][2]}")
    elif sell_candidates:
        # No candidates above minimum → use minimum + note the resistance
        sell_target = min_sell_price
        sell_reasons = [f"최소 목표 수익률 +{min_sell_pct:.0f}% (추세 강도·변동성 기반)"]
        if sell_candidates:
            sell_reasons.append(f"참고 — 가까운 저항: {sell_candidates[0][2]}")
    else:
        # Fallback: ATR-based
        sell_target = min_sell_price
        sell_reasons = [f"ATR 기반 목표가 (변동성 {atr_pct:.1f}% × {4 if trend_strength >= 0.7 else 3}배 상단)"]

    # Also ensure sell is at least 8% above buy target
    min_sell_from_buy = buy_target * 1.08
    if sell_target < min_sell_from_buy:
        sell_target = min_sell_from_buy
        sell_reasons.append("매수 대비 최소 8% 수익 보장")

    # ── STOP LOSS: Smart stop below key support ──
    stop_candidates = []

    # Below nearest support (with buffer)
    if nearby_supports:
        stop_below_support = max(nearby_supports) * 0.97  # 3% below support
        stop_candidates.append(("지지선 이탈", stop_below_support, f"주요 지지선(₩{round(max(nearby_supports)):,}) 하방 이탈 시 — 추가 하락 가능성"))

    # SMA200 break
    if sma_200 and sma_200 < price:
        stop_candidates.append(("200일선 이탈", sma_200 * 0.97, f"200일 이동평균선(₩{round(sma_200):,}) 이탈 시 — 장기 추세 전환 신호"))

    # ATR-based stop
    atr_stop = price - atr_14 * 2
    stop_candidates.append(("ATR 기반", atr_stop, f"ATR 2배 하단 (일 변동폭 {atr_pct:.1f}% × 2) — 단기 노이즈 필터링"))

    # Fibonacci support break
    fib_stops = [(n, v) for n, v in fib_levels.items() if v < price * 0.95]
    if fib_stops:
        fib_stops.sort(key=lambda x: x[1], reverse=True)
        stop_candidates.append(("피보나치 이탈", fib_stops[0][1] * 0.98, f"피보나치 {fib_stops[0][0]} (₩{round(fib_stops[0][1]):,}) 하방 이탈"))

    # Pick stop loss
    if stop_candidates:
        # Use the tightest reasonable stop (but not tighter than -5%)
        valid_stops = [s for s in stop_candidates if s[1] < price * 0.95]
        if not valid_stops:
            valid_stops = stop_candidates
        valid_stops.sort(key=lambda x: x[1], reverse=True)  # highest = tightest
        stop_price = valid_stops[0][1]
        stop_reasons = [valid_stops[0][2]]
        if len(valid_stops) > 1:
            stop_reasons.append(f"최종 손절: {valid_stops[-1][2]}")
    else:
        stop_price = price * 0.90
        stop_reasons = ["기본 손절 라인 (-10%)"]

    # Ensure stop is at least 5% below current and below buy target
    if stop_price > price * 0.95:
        stop_price = price * 0.95
    if stop_price > buy_target * 0.97:
        stop_price = buy_target * 0.95
        stop_reasons.append("매수 타점 대비 5% 하단으로 조정")

    # ── Overall strategy assessment ──
    buy_pct = (buy_target - price) / price * 100
    sell_pct = (sell_target - price) / price * 100
    stop_pct = (stop_price - price) / price * 100
    risk_reward = abs(sell_pct / stop_pct) if stop_pct != 0 else 0

    # Strategy description based on indicators
    strategy_signals = []
    if rsi is not None:
        if rsi < 30:
            strategy_signals.append(f"RSI {rsi:.0f} — 과매도 구간, 반등 임박 가능")
        elif rsi < 40:
            strategy_signals.append(f"RSI {rsi:.0f} — 매도 과열 완화 중")
        elif rsi > 70:
            strategy_signals.append(f"RSI {rsi:.0f} — 과매수 구간, 조정 주의")
        elif rsi > 60:
            strategy_signals.append(f"RSI {rsi:.0f} — 매수세 강한 구간")
        else:
            strategy_signals.append(f"RSI {rsi:.0f} — 중립 구간")

    if macd_val is not None and macd_signal is not None:
        if macd_val > macd_signal and macd_hist and macd_hist > 0:
            strategy_signals.append("MACD 골든크로스 — 상승 모멘텀 확인")
        elif macd_val < macd_signal and macd_hist and macd_hist < 0:
            strategy_signals.append("MACD 데드크로스 — 하락 모멘텀 주의")
        elif macd_val > macd_signal:
            strategy_signals.append("MACD 매수 신호 유지 중")
        else:
            strategy_signals.append("MACD 매도 신호 — 추세 전환 모니터링")

    if trend_strength >= 0.7:
        strategy_signals.append(f"이동평균선 정배열 ({bullish_smas}/{len(sma_values)}개 상향) — 상승 추세")
    elif trend_strength <= 0.3:
        strategy_signals.append(f"이동평균선 역배열 ({bullish_smas}/{len(sma_values)}개 상향) — 하락 추세")
    else:
        strategy_signals.append(f"이동평균선 혼조 ({bullish_smas}/{len(sma_values)}개 상향) — 추세 불확실")

    if momentum_5d > 3:
        strategy_signals.append(f"최근 5일 +{momentum_5d:.1f}% 상승 — 단기 모멘텀 강함")
    elif momentum_5d < -3:
        strategy_signals.append(f"최근 5일 {momentum_5d:.1f}% 하락 — 단기 약세")

    # Position in Bollinger band
    if bb_upper != bb_lower:
        bb_position = (price - bb_lower) / (bb_upper - bb_lower)
        if bb_position > 0.8:
            strategy_signals.append(f"볼린저밴드 상단({bb_position:.0%}) — 과매수 주의")
        elif bb_position < 0.2:
            strategy_signals.append(f"볼린저밴드 하단({bb_position:.0%}) — 과매도 반등 기대")
        else:
            strategy_signals.append(f"볼린저밴드 중간({bb_position:.0%})")

    result = {
        "ticker": ticker.upper(),
        "current_price": round(price, 2),
        "targets": {
            "buy": {
                "price": round(buy_target, 2),
                "pct": round(buy_pct, 1),
                "reasons": buy_reasons,
            },
            "sell": {
                "price": round(sell_target, 2),
                "pct": round(sell_pct, 1),
                "reasons": sell_reasons,
            },
            "stop": {
                "price": round(stop_price, 2),
                "pct": round(stop_pct, 1),
                "reasons": stop_reasons,
            },
        },
        "risk_reward_ratio": round(risk_reward, 2),
        "strategy_signals": strategy_signals,
        "atr_pct": round(atr_pct, 2),
        "trend_strength": round(trend_strength, 2),
        "support_levels": [round(s, 2) for s in support_levels if s < price][-3:],
        "resistance_levels": [round(r, 2) for r in resistance_levels if r > price][:3],
        "fibonacci": {k: round(v, 2) for k, v in fib_levels.items()},
    }

    _set_cached(cache_key, result)
    return result


@router.get("/analysis/{ticker}/chart-data")
def get_chart_data(ticker: str, period: str = "3mo") -> dict:
    """OHLCV data with ALL indicator overlays inlined per data point."""
    cache_key = f"chart-data:{_ticker_key(ticker)}:{period}"
    cached = _get_best_cached(cache_key, 1800)
    if cached is not None:
        return cached

    df = StockDataService.get_stock_history(ticker, period=period)

    if df.empty:
        stale = _load_disk_cached(cache_key, 1800, allow_stale=True)
        if stale is not None:
            return stale
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

    result = {"ticker": ticker.upper(), "data": data}
    _set_cached(cache_key, result)
    _save_disk_cached(cache_key, result)
    return result


@router.get("/analysis/{ticker}/earnings")
def get_earnings(ticker: str) -> dict:
    """Get earnings and valuation data with cached fallbacks.

    Avoid depending on yfinance stock.info for Korean stocks because that is the
    most common rate-limit failure path in production.
    """
    cache_key = f"earnings:{_ticker_key(ticker)}"
    cached = _get_cached_ttl(cache_key, 1800)
    if cached is not None:
        return cached

    try:
        is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")

        # Use global cached info — avoids redundant yfinance calls
        info = {}
        if not is_krx:
            try:
                info = get_yf_info(ticker)
            except Exception:
                info = {}

        # Quarterly earnings & financials — use global cached financials
        quarterly_earnings = []
        quarterly_revenue = []
        try:
            qf, _qbs = get_yf_financials(ticker)
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

        # 3-source fallback: yfinance info → yf quarterly fallback → Naver/Yahoo scraping
        earnings_fallback = {}
        try:
            # Build a lightweight stock object for _derive_earnings_fallbacks
            stock = type("_S", (), {"quarterly_financials": qf if 'qf' in dir() else pd.DataFrame(), "quarterly_balance_sheet": _qbs if '_qbs' in dir() else pd.DataFrame()})()
            earnings_fallback = _derive_earnings_fallbacks(stock)
        except Exception:
            pass

        alt_data = {}
        try:
            alt_data = fetch_fundamentals(ticker)
        except Exception:
            pass

        def _epick(info_key: str, fb_key: str):
            v = info.get(info_key)
            if v is not None:
                return v
            v = earnings_fallback.get(fb_key)
            if v is not None:
                return v
            return alt_data.get(fb_key)

        result = {
            "ticker": ticker.upper(),
            "market_cap": info.get("marketCap"),
            "pe_ratio": _epick("trailingPE", "pe_ratio"),
            "forward_pe": _epick("forwardPE", "forward_pe"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": _epick("priceToBook", "price_to_book"),
            "revenue_growth": _epick("revenueGrowth", "revenue_growth"),
            "earnings_growth": _epick("earningsGrowth", "earnings_growth"),
            "profit_margin": _epick("profitMargins", "profit_margin"),
            "operating_margin": _epick("operatingMargins", "operating_margin"),
            "roe": _epick("returnOnEquity", "roe"),
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "dividend_yield": _epick("dividendYield", "dividend_yield"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "quarterly_earnings": quarterly_earnings,
            "quarterly_revenue": quarterly_revenue,
        }
        _set_cached(cache_key, result)
        return result
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


@router.get("/analysis/{ticker}/pattern")
def get_pattern_analysis(ticker: str) -> dict:
    """
    Historical pattern analysis:
    - Find significant price moves in history
    - Analyze what indicators looked like before each major move
    - Compare current setup to historical patterns
    - Return pattern matches with similarity scores
    """
    cache_key = f"pattern:{_ticker_key(ticker)}"
    cached = _get_best_cached(cache_key, 43200)
    if cached is not None:
        return cached

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

        result = {
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
        _set_cached(cache_key, result)
        _save_disk_cached(cache_key, result)
        return result
    except Exception as e:
        stale = _load_disk_cached(cache_key, 43200, allow_stale=True)
        if stale is not None:
            return stale
        return {"ticker": ticker.upper(), "patterns": [], "current_setup": {}, "events": [], "error": str(e)}


@router.get("/analysis/{ticker}/prediction")
def get_prediction(ticker: str) -> dict:
    """
    Comprehensive 50+ technical indicator analysis with future price prediction.
    Analyses: trend, momentum, volatility, volume, oscillators, pattern, support/resistance.
    Returns aggregated scores per category and an overall prediction.
    """
    cache_key = f"prediction:{_ticker_key(ticker)}"
    cached = _get_best_cached(cache_key, 3600)
    if cached is not None:
        return cached

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

        result = {
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
        _set_cached(cache_key, result)
        _save_disk_cached(cache_key, result)
        return result
    except Exception as e:
        stale = _load_disk_cached(cache_key, 3600, allow_stale=True)
        if stale is not None:
            return stale
        return {"ticker": ticker.upper(), "error": str(e)}


_MOVE_SPAM_SOURCES = {
    "smartkarma", "tradingkey", "simplywall", "stockanalysis.com",
    "wallstreetzen", "marketscreener", "trendlyne",
}
_MOVE_SPAM_PATTERNS = [
    "주식 움직였습니다", "주식이 움직였습니다", "변동을 뒷받침하는",
    "핵심 원인 공개", "투자자가 알아야 할", "what you need to know",
    "stock moved", "here's what happened", "why it moved",
    "what drove", "핵심 원인", "알아야 할 정보",
]


def _search_news_for_date(query: str, date_str: str) -> list[dict]:
    """Search Naver & Google for news around a specific date, filter spam.
    Uses Naver's date range parameters (ds/de) for precise date matching.
    """
    from urllib.parse import quote
    from datetime import datetime, timedelta
    results = []
    seen = set()

    # Compute date range: target date ±2 days
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        ds = (target - timedelta(days=2)).strftime("%Y.%m.%d")
        de = (target + timedelta(days=2)).strftime("%Y.%m.%d")
    except Exception:
        ds = de = ""

    # Naver: date-range search (ds/de parameters for precise date filtering)
    try:
        naver_params = f"where=news&query={quote(query)}&sm=tab_opt&sort=0&ds={ds}&de={de}" if ds else f"where=news&query={quote(query)}&sm=tab_opt&sort=1"
        url = f"https://search.naver.com/search.naver?{naver_params}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        with limit_http():
            r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select("div.news_area")[:8]:
                title_tag = item.select_one("a.news_tit")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                source_tag = item.select_one("a.info.press")
                source = source_tag.get_text(strip=True) if source_tag else ""
                if title in seen:
                    continue
                if any(s in source.lower() for s in _MOVE_SPAM_SOURCES):
                    continue
                if any(p in title.lower() for p in _MOVE_SPAM_PATTERNS):
                    continue
                seen.add(title)
                results.append({"title": title, "source": source})
    except Exception:
        pass

    # Google News RSS with date filter
    try:
        import feedparser
        encoded = quote(query)
        before_date = (target + timedelta(days=3)).strftime("%Y-%m-%d") if ds else ""
        after_date = (target - timedelta(days=3)).strftime("%Y-%m-%d") if ds else date_str
        feed_url = f"https://news.google.com/rss/search?q={encoded}+after:{after_date}+before:{before_date}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:6]:
            title = entry.get("title", "")
            source = entry.get("source", {}).get("title", "") if hasattr(entry, "source") else ""
            if title in seen:
                continue
            if any(s in source.lower() for s in _MOVE_SPAM_SOURCES):
                continue
            if any(p in title.lower() for p in _MOVE_SPAM_PATTERNS):
                continue
            seen.add(title)
            results.append({"title": title, "source": source})
    except Exception:
        pass

    return results


def _build_issue_summary(category: str, reason: str, pct: float) -> str:
    """Build a short (≤15 char) summary for chart dot labels."""
    direction = "↑" if pct > 0 else "↓"
    # Map category to short label
    cat_map = {
        "실적": f"실적{direction}",
        "가이던스": f"가이던스{direction}",
        "제품/수주": f"수주{direction}",
        "규제/정책": f"규제이슈",
        "리포트": f"리포트{direction}",
        "매크로": f"매크로{direction}",
        "업황": f"업황{direction}",
        "M&A/투자": f"M&A",
        "수급": f"수급{direction}",
    }
    summary = cat_map.get(category, "")
    if summary:
        return summary
    # Fallback: extract key term from reason
    if "거래량" in reason and "폭증" in reason:
        return f"거래량폭증{direction}"
    if "시장 전체" in reason or "지수 연동" in reason:
        return f"시장연동{direction}"
    return f"변동{direction}"


def _analyze_move_reason(titles: list[str], ticker: str, company_name: str,
                         pct: float, vol_ratio: float) -> tuple[str, str, str]:
    """
    Analyze news titles to determine the specific reason for a price move.
    Returns (category, reason_detail, confidence).
    """
    if not titles:
        # No news found — analyze based on price/volume pattern alone
        direction = "상승" if pct > 0 else "하락"
        if vol_ratio > 2.0:
            return "수급", f"뉴스 없이 거래량 {vol_ratio:.1f}배 폭증과 함께 {direction} — 기관/외국인 수급 주도 가능성", "low"
        elif vol_ratio > 1.5:
            return "수급", f"특별한 뉴스 없이 거래량 증가와 함께 {direction} — 시장 전반의 섹터 순환 또는 수급 변동 추정", "low"
        else:
            return "시장", f"뉴스·거래량 특이점 없는 {direction} — 시장 전체 흐름(지수 연동) 또는 기술적 조정 가능성", "low"

    combined = " ".join(titles).lower()

    # Pattern matching for specific catalysts
    patterns = [
        # Earnings / Guidance
        (["실적", "매출", "영업이익", "순이익", "잠정", "earnings", "revenue", "profit", "quarterly"],
         "실적", lambda: _build_earnings_reason(titles, pct)),
        # Guidance / Outlook
        (["가이던스", "전망", "guidance", "outlook", "forecast", "목표", "상향", "하향"],
         "가이던스", lambda: _build_guidance_reason(titles, pct)),
        # Product / Orders
        (["수주", "계약", "납품", "출시", "승인", "양산", "order", "deal", "contract", "launch", "approval", "shipment"],
         "제품/수주", lambda: _build_product_reason(titles, pct)),
        # Regulation / Policy
        (["규제", "관세", "제재", "소송", "tariff", "regulation", "ban", "probe", "lawsuit", "export control", "수출규제"],
         "규제/정책", lambda: _build_regulation_reason(titles, pct)),
        # Upgrade / Downgrade
        (["목표가", "투자의견", "upgrade", "downgrade", "매수", "매도", "outperform", "overweight", "상향", "하향"],
         "리포트", lambda: _build_analyst_reason(titles, pct)),
        # Macro
        (["금리", "fed", "fomc", "인플레이션", "cpi", "환율", "달러", "rate", "inflation", "경기"],
         "매크로", lambda: _build_macro_reason(titles, pct)),
        # Sector / Industry
        (["hbm", "dram", "nand", "메모리", "반도체", "ai ", "gpu", "capex", "데이터센터"],
         "업황", lambda: _build_sector_reason(titles, pct)),
        # M&A / Investment
        (["인수", "합병", "투자", "지분", "acquisition", "merger", "stake", "buyback", "자사주"],
         "M&A/투자", lambda: _build_ma_reason(titles, pct)),
    ]

    best_score = 0
    best_result = ("시장", "관련 뉴스 확인 필요", "low")
    for keywords, category, builder in patterns:
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            reason = builder()
            confidence = "high" if score >= 3 else "medium" if score >= 2 else "low"
            best_result = (category, reason, confidence)

    return best_result


def _extract_key_detail(titles: list[str], keywords: list[str]) -> str:
    """Extract the most relevant title as a key detail."""
    scored = []
    for t in titles:
        tl = t.lower()
        score = sum(1 for kw in keywords if kw in tl)
        if score > 0:
            scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else titles[0]


def _build_earnings_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["실적", "매출", "영업이익", "earnings", "revenue", "profit"])
    direction = "호실적 서프라이즈" if pct > 0 else "실적 미스/부진"
    return f"{direction} 반영 — \"{key}\""

def _build_guidance_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["가이던스", "전망", "guidance", "outlook", "목표"])
    direction = "가이던스 상향/기대 초과" if pct > 0 else "가이던스 하향/기대 하회"
    return f"{direction} — \"{key}\""

def _build_product_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["수주", "계약", "출시", "승인", "order", "deal", "launch", "approval"])
    direction = "호재" if pct > 0 else "차질"
    return f"사업 이벤트 {direction} — \"{key}\""

def _build_regulation_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["규제", "관세", "제재", "소송", "tariff", "regulation", "ban"])
    return f"규제·정책 이슈 반영 — \"{key}\""

def _build_analyst_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["목표가", "투자의견", "upgrade", "downgrade", "상향", "하향"])
    direction = "목표가 상향/매수 리포트" if pct > 0 else "목표가 하향/매도 리포트"
    return f"{direction} — \"{key}\""

def _build_macro_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["금리", "fed", "cpi", "환율", "달러", "rate", "inflation"])
    return f"매크로 환경 변화 반영 — \"{key}\""

def _build_sector_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["hbm", "dram", "ai ", "gpu", "capex", "반도체", "메모리"])
    direction = "업황 기대 강화" if pct > 0 else "업황 우려 확대"
    return f"{direction} — \"{key}\""

def _build_ma_reason(titles: list[str], pct: float) -> str:
    key = _extract_key_detail(titles, ["인수", "합병", "투자", "지분", "acquisition", "merger"])
    return f"M&A·투자 이슈 — \"{key}\""


@router.get("/analysis/{ticker}/move-reasons")
def get_move_reasons(ticker: str, period: str = "3mo") -> dict:
    """
    Find significant price moves and search for specific news/reasons for each date.
    For each big move, directly searches Naver & Google News around that date
    and analyzes the actual cause from news titles.
    """
    cache_key = f"move-reasons:{ticker}:{period}"
    cached = _get_cached_ttl(cache_key, 600)  # 10 min cache
    if cached is not None:
        return cached

    try:
        df = StockDataService.get_stock_history(ticker, period=period)
        if df.empty or len(df) < 5:
            return {"ticker": ticker.upper(), "moves": []}

        close = df["Close"]
        volume_s = df["Volume"]
        vol_sma = volume_s.rolling(10).mean()

        # Get company name for news search — use global cache
        try:
            info = get_yf_info(ticker)
            company_name = info.get("shortName", info.get("longName", ticker))
        except Exception:
            company_name = ticker

        # Build search name: short, useful for news search
        is_krx = ticker.endswith(".KS") or ticker.endswith(".KQ")
        if is_krx:
            # Korean stock: use Korean name from our data or info
            search_name = company_name if not company_name.startswith(ticker.split(".")[0]) else ticker.split(".")[0]
        else:
            # US stock: use first word of company name + ticker
            search_name = company_name.split(" ")[0] if company_name != ticker else ticker

        # Detect all significant moves first
        raw_moves = []
        for i in range(1, len(df)):
            pct = (float(close.iloc[i]) - float(close.iloc[i-1])) / float(close.iloc[i-1]) * 100
            if abs(pct) < 2.5:
                continue
            date_str = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            vol_ratio = float(volume_s.iloc[i]) / float(vol_sma.iloc[i]) if not pd.isna(vol_sma.iloc[i]) and float(vol_sma.iloc[i]) > 0 else 1.0
            raw_moves.append({
                "index": i, "date": date_str, "pct": pct,
                "price": round(float(close.iloc[i]), 2), "vol_ratio": vol_ratio,
            })

        # Sort by magnitude, keep top N
        raw_moves.sort(key=lambda m: abs(m["pct"]), reverse=True)
        limit = 20 if period in ("1y", "2y", "5y", "max") else 12
        top_moves = raw_moves[:limit]

        # For each top move, search news around that date
        moves = []
        for mv in top_moves:
            date_str = mv["date"]
            pct = mv["pct"]
            vol_ratio = mv["vol_ratio"]

            # Search with company name + exact date context
            query = f"{search_name} 주가" if is_krx else f"{search_name} stock"
            articles = _search_news_for_date(query, date_str)

            # Also try broader company name search
            if len(articles) < 3:
                articles.extend(_search_news_for_date(search_name, date_str))

            # Also try ticker-based search for US stocks
            if not is_krx and len(articles) < 3:
                articles.extend(_search_news_for_date(f"{ticker} stock price", date_str))

            # Deduplicate
            seen_titles = set()
            unique_articles = []
            for a in articles:
                if a["title"] not in seen_titles:
                    seen_titles.add(a["title"])
                    unique_articles.append(a)
            articles = unique_articles[:6]

            # Analyze the reason from news titles
            titles = [a["title"] for a in articles]
            category, reason, confidence = _analyze_move_reason(
                titles, ticker, company_name, pct, vol_ratio
            )

            # Classify move type
            if pct > 5:
                move_type = "급등"
            elif pct > 2.5:
                move_type = "상승"
            elif pct < -5:
                move_type = "급락"
            else:
                move_type = "하락"

            vol_note = ""
            if vol_ratio > 2.0:
                vol_note = f"거래량 {vol_ratio:.1f}배 폭증"
            elif vol_ratio > 1.5:
                vol_note = f"거래량 {vol_ratio:.1f}배 증가"

            # Build short issue_summary (≤15 chars) for chart dot label
            issue_summary = _build_issue_summary(category, reason, pct)

            moves.append({
                "date": date_str,
                "change_pct": round(pct, 2),
                "price": mv["price"],
                "volume_ratio": round(vol_ratio, 2),
                "move_type": move_type,
                "reason": reason,
                "issue_summary": issue_summary,
                "issue_category": category,
                "confidence": confidence,
                "vol_note": vol_note,
                "news": [{"title": a["title"], "source": a.get("source", "")} for a in articles[:3]],
            })

        # Re-sort by date for chart display
        moves.sort(key=lambda m: m["date"])
        response = {"ticker": ticker.upper(), "moves": moves}
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
        ck("데이터센터 매출 성장률 (QoQ)", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=95, thesis="NVDA는 데이터센터 매출 성장률이 둔화되면 멀티플이 가장 먼저 눌리는 구조입니다.", window="향후 1~2분기"),
        ck("HBM/GPU ASP 추이", "commodity", symbol="SOXX", positive_if="up", weight=85, thesis="GPU/HBM ASP 상승은 NVDA 마진 확대의 핵심입니다. SOXX로 업황 기대를 확인합니다.", window="향후 1~3개월"),
        ck("AI 캡엑스 지출 (MSFT/GOOG/META)", "commodity", symbol="MSFT", positive_if="up", weight=90, thesis="빅테크 AI 인프라 캡엑스가 꺾이면 NVDA 수주 기대도 바로 약해집니다.", window="향후 1~2분기"),
        ck("중국 수출 규제 변동", "commodity", symbol="QQQ", positive_if="up", weight=58, thesis="중국 수출 규제 강화 시 NVDA 중국 매출 직접 타격. QQQ 약세 시 빅테크 전반 위험선호 후퇴.", window="향후 1~2개월"),
        ck("경쟁사 AMD MI300 점유율", "commodity", symbol="AMD", positive_if="down", weight=70, thesis="AMD MI300이 빠르게 점유율을 가져가면 NVDA 독점 프리미엄이 약해질 수 있습니다.", window="향후 1~3개월"),
    ],
    "TSM": [
        ck("3nm/2nm 가동률", "commodity", symbol="SOXX", positive_if="up", weight=85, thesis="TSMC 3nm/2nm 가동률이 올라야 ASP 상승과 마진 확대가 이어집니다. SOXX로 반도체 업황 확인.", window="향후 1~3개월"),
        ck("웨이퍼 ASP 변동", "commodity", symbol="NVDA", positive_if="up", weight=82, thesis="NVDA 등 주요 팹리스 고객의 주문 강도가 웨이퍼 ASP 방향을 결정합니다.", window="향후 1~3개월"),
        ck("월별 매출 공시 (MoM)", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.08, weight=90, thesis="TSMC는 월별 매출을 공시합니다. MoM 성장 둔화가 가장 빠른 경보 신호입니다.", window="향후 1~2분기"),
        ck("지정학 리스크 (대만 해협)", "commodity", symbol="TWD=X", positive_if="down", weight=60, thesis="대만달러 급변은 대만 해협 긴장을 반영합니다. 지정학 리스크 확대 시 TSMC 밸류 할인.", window="향후 1~3개월"),
        ck("CAPEX 집행률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.35, weight=88, thesis="CAPEX 집행률이 높을수록 향후 생산능력 확대와 수주 확보 기대가 살아 있다는 신호입니다.", window="향후 1~2분기"),
    ],
    "AVGO": [
        ck("커스텀 AI칩 수주 현황", "commodity", symbol="SOXX", positive_if="up", weight=78, thesis="AVGO 커스텀 AI칩(ASIC) 수주 확대가 성장 핵심입니다. SOXX로 AI 반도체 업황 확인.", window="향후 1~3개월"),
        ck("VMware 통합 시너지", "earnings_metric", metric="operating_margin", positive_if="above", threshold=0.32, weight=88, thesis="VMware 인수 후 통합 시너지가 영업이익률 개선으로 나타나야 합니다.", window="향후 1~3분기"),
        ck("네트워킹 매출 비중", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=82, thesis="AI 네트워킹 매출 비중이 확대되면 성장성 재평가가 가능합니다.", window="향후 1~2분기"),
        ck("배당 성장률", "earnings_metric", metric="dividend_yield", positive_if="above", threshold=0.01, weight=35, thesis="AVGO는 배당 성장주로 배당 인상 지속 여부가 장기 투자 매력입니다.", window="향후 2~4분기"),
        ck("Google TPU 계약", "commodity", symbol="GOOG", positive_if="up", weight=66, thesis="Google TPU 등 커스텀칩 기대는 GOOG 투자 심리와 직결됩니다.", window="향후 1~3개월"),
    ],
    "000660.KS": [
        ck("DRAM 현물/계약가격 추이", "commodity", symbol="MU", positive_if="up", weight=92, thesis="DRAM 현물가가 계약가 대비 프리미엄을 유지하면 업사이클 지속 신호입니다. MU 주가가 메모리 현물가 기대를 대리합니다.", window="향후 1~3개월"),
        ck("HBM 출하량/ASP", "commodity", symbol="SOXX", positive_if="up", weight=82, thesis="HBM 출하량과 ASP 상승이 동시에 유지돼야 하이닉스 프리미엄이 유지됩니다.", window="향후 1~3개월"),
        ck("재고 수준 (bit growth)", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.12, weight=88, thesis="메모리 재고가 줄고 bit growth가 건강하면 업사이클 지속입니다. 매출 성장률로 출하 추이 확인.", window="향후 1~2분기"),
        ck("NVDA HBM 공급 비중", "commodity", symbol="NVDA", positive_if="up", weight=88, thesis="NVDA HBM 물량에서 하이닉스 점유율이 유지되어야 프리미엄이 유지됩니다.", window="향후 1~2개월"),
        ck("영업이익률 추이", "earnings_metric", metric="operating_margin", positive_if="above", threshold=0.12, weight=95, thesis="메모리주는 이익률 피크아웃 신호가 나오면 주가가 가장 먼저 꺾이는 경향이 있습니다.", window="향후 1~2분기"),
    ],
    "005930.KS": [
        ck("DRAM/NAND 가격 추이", "commodity", symbol="MU", positive_if="up", weight=90, thesis="DRAM/NAND 현물가격은 삼성전자 메모리 실적의 선행지표입니다. MU 주가가 현물가 기대를 대리합니다.", window="향후 1~3개월"),
        ck("파운드리 수율 개선", "commodity", symbol="SOXX", positive_if="up", weight=78, thesis="삼성 파운드리 3nm/2nm 수율 개선은 TSMC 대비 경쟁력 회복의 핵심입니다. 반도체 업황과 함께 움직입니다.", window="향후 1~3개월"),
        ck("HBM 수율 이슈", "commodity", symbol="000660.KS", positive_if="up", weight=82, thesis="삼성 HBM 수율 문제가 해결되면 NVDA 공급 확대로 실적이 크게 개선됩니다. SK하이닉스 대비 격차 모니터링.", window="향후 1~3개월"),
        ck("갤럭시 판매량", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.06, weight=75, thesis="갤럭시 시리즈 판매량이 삼성전자 IM(모바일) 사업부 매출에 직결됩니다. 전체 매출 성장률로 확인.", window="향후 1~2분기"),
        ck("자사주 매입", "earnings_metric", metric="price_to_book", positive_if="below", threshold=2.0, weight=55, thesis="삼성전자 밸류업 프로그램(자사주 매입·소각)으로 PBR 할인 해소 기대. P/B가 낮을수록 매입 효과가 큽니다.", window="향후 1~2개월"),
    ],
    "TSLA": [
        ck("차량 인도량 (QoQ)", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.08, weight=88, thesis="TSLA 분기별 차량 인도량이 시장 기대를 충족하는지가 주가 방향의 핵심입니다.", window="향후 1~2분기"),
        ck("Optimus 로봇 진행상황", "commodity", symbol="DRIV", positive_if="up", weight=70, thesis="Optimus 휴머노이드 로봇 양산 스케줄이 주가 기대감에 큰 영향을 줍니다. EV/자동화 심리로 확인.", window="향후 1~3개월"),
        ck("FSD 라이센싱 수익", "commodity", symbol="QQQ", positive_if="up", weight=60, thesis="FSD(자율주행) 소프트웨어 라이센싱 수익이 실현되면 소프트웨어 밸류에이션 재평가 가능.", window="향후 1~3개월"),
        ck("마진율 추이", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.07, weight=95, thesis="TSLA는 매출보다 자동차/에너지 마진 방향이 주가를 더 크게 좌우합니다.", window="향후 1~2분기"),
        ck("에너지 사업 매출", "commodity", symbol="ICLN", positive_if="up", weight=55, thesis="에너지저장/솔라루프 사업 매출 확대가 TSLA 밸류 재평가의 보조축입니다.", window="향후 1~3개월"),
    ],
    "ISRG": [
        ck("다빈치 시술 건수 (QoQ)", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=80, thesis="다빈치 로봇 시술 건수가 매출과 반복매출(소모품)의 핵심 드라이버입니다.", window="향후 1~2분기"),
        ck("시스템 설치 대수", "commodity", symbol="XLV", positive_if="up", weight=42, thesis="병원 신규 다빈치 시스템 설치 수가 장기 반복매출 기반을 넓힙니다. 헬스케어 업황으로 확인.", window="향후 1~3개월"),
        ck("반복매출 비중", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.18, weight=86, thesis="소모품·서비스 반복매출 비중이 높을수록 실적 안정성이 좋고 프리미엄 유지.", window="향후 1~2분기"),
        ck("경쟁사 진입 여부", "commodity", symbol="MDT", positive_if="down", weight=55, thesis="Medtronic Hugo 등 경쟁 수술 로봇 진입 시 ISRG 독점 프리미엄 약화 가능.", window="향후 1~3개월"),
        ck("중국 시장 확대", "earnings_metric", metric="roe", positive_if="above", threshold=0.15, weight=58, thesis="중국 시장 침투율 확대가 장기 성장 동력이며, ROE로 자본효율성 확인.", window="향후 2~4분기"),
    ],
    "CEG": [
        ck("원전 가동률", "commodity", symbol="URA", positive_if="up", weight=70, thesis="원전 가동률이 높을수록 전력 공급량과 매출이 늘어납니다. 우라늄 가격으로 업황 확인.", window="향후 1~3개월"),
        ck("전력 계약 가격(PPA)", "commodity", symbol="XLU", positive_if="up", weight=78, thesis="장기 전력 구매 계약(PPA) 가격이 상승하면 CEG 수익성이 직접 개선됩니다.", window="향후 1~3개월"),
        ck("Microsoft/Google 전력 계약", "commodity", symbol="MSFT", positive_if="up", weight=75, thesis="빅테크의 AI 데이터센터 전력 수요가 CEG의 핵심 성장 동력입니다.", window="향후 1~3개월"),
        ck("규제 환경 변화", "commodity", symbol="NG=F", positive_if="up", weight=54, thesis="원전 규제 완화/천연가스 가격 상승은 원전의 상대 경제성을 높입니다.", window="향후 1~2개월"),
        ck("전력 수요 전망", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=76, thesis="AI 데이터센터 확장으로 전력 수요가 폭증하면 CEG 매출 성장에 직결.", window="향후 1~2분기"),
    ],
    "CCJ": [
        ck("우라늄 현물가격", "commodity", symbol="URA", positive_if="up", weight=96, thesis="CCJ는 우라늄 현물가격을 가장 직접적으로 반영합니다. URA ETF로 확인.", window="향후 1~3개월"),
        ck("장기 계약가격", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=72, thesis="장기 계약가격 상승은 CCJ의 향후 수년간 매출을 결정합니다.", window="향후 1~2분기"),
        ck("공급 부족 규모", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.08, weight=78, thesis="글로벌 우라늄 공급 부족이 심화되면 가격 상승과 CCJ 이익 확대로 이어집니다.", window="향후 1~2분기"),
        ck("카자흐스탄 생산량", "commodity", symbol="NG=F", positive_if="down", weight=60, thesis="카자흐 Kazatomprom 생산 차질 시 공급 부족이 심화돼 우라늄 가격 상승 요인.", window="향후 1~3개월"),
        ck("러시아 수출 제재", "commodity", symbol="GC=F", positive_if="up", weight=55, thesis="러시아 우라늄 수출 제재 시 서방권 공급 부족이 CCJ에 직접 수혜.", window="향후 1~3개월"),
    ],
    "CRWD": [
        ck("ARR 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.2, weight=90, thesis="CRWD는 ARR(연간반복매출) 성장 둔화가 보이면 고밸류가 빠르게 압축될 수 있습니다.", window="향후 1~2분기"),
        ck("고객당 모듈 수", "commodity", symbol="BUG", positive_if="up", weight=72, thesis="고객당 채택 모듈 수 증가는 플랫폼 고착도를 보여줍니다. 사이버보안 업황으로 확인.", window="향후 1~3개월"),
        ck("순유지율(NRR)", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.05, weight=82, thesis="순유지율(NRR) 120%+ 유지가 SaaS 프리미엄의 핵심 지표입니다.", window="향후 1~2분기"),
        ck("경쟁사 대비 점유율", "commodity", symbol="PANW", positive_if="down", weight=65, thesis="Palo Alto 등 경쟁사 대비 점유율 방어가 중요합니다.", window="향후 1~3개월"),
        ck("보안사고 리스크", "commodity", symbol="QQQ", positive_if="up", weight=55, thesis="블루스크린 같은 보안사고 재발 시 급락 위험. 빅테크 전반 위험선호로 간접 확인.", window="향후 1~2개월"),
    ],
    "CRSP": [
        ck("임상시험 진행 단계", "commodity", symbol="XBI", positive_if="up", weight=76, thesis="CRSP 파이프라인 임상 진행 상황이 주가 핵심 변수. 바이오 업황으로 간접 확인.", window="향후 1~3개월"),
        ck("FDA 승인 일정", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.0, weight=62, thesis="FDA 승인/거절이 임박할수록 주가 변동성이 극대화됩니다. 매출 인식 시작 여부 확인.", window="향후 1~2분기"),
        ck("적응증 확대 파이프라인", "commodity", symbol="ARKG", positive_if="up", weight=68, thesis="유전자편집을 새 적응증(암, 심혈관)으로 확장하면 시장 규모가 수십배 커집니다.", window="향후 1~3개월"),
        ck("현금 보유량(런웨이)", "earnings_metric", metric="price_to_book", positive_if="below", threshold=10.0, weight=84, thesis="현금 런웨이가 줄면 희석 발행 우려로 주가 압박. P/B로 자금 상태 확인.", window="향후 1~2분기"),
        ck("경쟁 유전자치료 동향", "commodity", symbol="NTLA", positive_if="down", weight=55, thesis="Intellia 등 경쟁사 유전자편집 성과가 CRSP의 기술적 우위를 위협할 수 있습니다.", window="향후 1~3개월"),
    ],
    "LLY": [
        ck("비만약(GLP-1) 처방 데이터", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.15, weight=92, thesis="GLP-1 비만약 처방 건수와 매출 성장이 LLY 밸류에이션의 핵심입니다.", window="향후 1~2분기"),
        ck("분기별 매출 서프라이즈", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.18, weight=80, thesis="분기 실적이 시장 기대를 상회하면 멀티플 확장이 지속됩니다.", window="향후 1~2분기"),
        ck("파이프라인 임상 결과", "commodity", symbol="IBB", positive_if="up", weight=45, thesis="알츠하이머(도나네맙) 등 파이프라인 임상 성과가 장기 성장 동력입니다.", window="향후 1~3개월"),
        ck("경쟁사(NVO) 동향", "commodity", symbol="NVO", positive_if="down", weight=68, thesis="노보노디스크 GLP-1 경쟁이 심화되면 LLY 점유율 방어가 핵심 이슈.", window="향후 1~3개월"),
        ck("보험 커버리지 확대", "commodity", symbol="XLV", positive_if="up", weight=55, thesis="비만약 보험 급여 확대가 처방 증가의 핵심 트리거. 헬스케어 업황으로 확인.", window="향후 1~3개월"),
    ],
    "IONQ": [
        ck("큐비트 수 로드맵 진척", "commodity", symbol="QTUM", positive_if="up", weight=74, thesis="큐비트 수 로드맵 달성이 기술적 마일스톤의 핵심. 양자 업황으로 기대감 확인.", window="향후 1~3개월"),
        ck("매출 증가율", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.25, weight=86, thesis="IONQ는 실적 절대값보다 성장률 유지 여부가 기대감 유지의 핵심입니다.", window="향후 1~2분기"),
        ck("현금 소진율", "earnings_metric", metric="profit_margin", positive_if="above", threshold=-0.5, weight=92, thesis="적자 폭이 다시 확대되면 기술 기대보다 자금 조달 우려가 먼저 커집니다.", window="향후 1~2분기"),
        ck("정부/기업 계약", "commodity", symbol="XLK", positive_if="up", weight=60, thesis="정부/대기업과의 양자 컴퓨팅 계약 확보가 매출 가시성을 높입니다.", window="향후 1~3개월"),
        ck("기술적 마일스톤", "commodity", symbol="QQQ", positive_if="up", weight=55, thesis="양자 우위 실험 성공 등 기술 마일스톤은 주가 급등 트리거.", window="향후 1~2개월"),
    ],
    "RKLB": [
        ck("발사 횟수/성공률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.2, weight=88, thesis="Electron 발사 횟수와 성공률이 RKLB 매출 성장의 직접 드라이버입니다.", window="향후 1~2분기"),
        ck("Neutron 로켓 개발 진척", "commodity", symbol="UFO", positive_if="up", weight=75, thesis="Neutron 중형 로켓 개발 성공 시 발사 시장 점유율이 크게 확대됩니다.", window="향후 1~3개월"),
        ck("우주시스템 매출 비중", "earnings_metric", metric="profit_margin", positive_if="above", threshold=-0.2, weight=70, thesis="발사 외 우주시스템(위성부품) 매출 비중 확대가 밸류 재평가 핵심.", window="향후 1~2분기"),
        ck("수주잔고", "commodity", symbol="ITA", positive_if="up", weight=55, thesis="정부 및 국방 수주잔고가 향후 매출 가시성을 결정합니다.", window="향후 1~3개월"),
        ck("경쟁사(SpaceX) 동향", "commodity", symbol="BA", positive_if="down", weight=50, thesis="SpaceX Starship 성공 시 RKLB의 상대적 포지셔닝이 변할 수 있습니다.", window="향후 1~3개월"),
    ],
    "BE": [
        ck("SOFC 주문 잔고", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.12, weight=78, thesis="고체산화물 연료전지(SOFC) 주문 잔고가 BE 매출 성장의 선행 지표입니다.", window="향후 1~2분기"),
        ck("매출총이익률 추이", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.0, weight=94, thesis="매출총이익률 개선이 흑자전환의 핵심 전제조건입니다.", window="향후 1~2분기"),
        ck("AI 데이터센터 계약", "commodity", symbol="MSFT", positive_if="up", weight=70, thesis="빅테크 데이터센터 분산전원(연료전지) 계약 확대가 BE 성장의 핵심 동력.", window="향후 1~3개월"),
        ck("수소 전환 로드맵", "commodity", symbol="ICLN", positive_if="up", weight=60, thesis="수소 경제 전환 기대가 BE의 장기 밸류에이션을 결정합니다.", window="향후 1~3개월"),
        ck("정부 보조금 현황", "commodity", symbol="PL=F", positive_if="up", weight=35, thesis="IRA 등 정부 클린에너지 보조금이 BE의 수익성과 수주에 직접 영향.", window="향후 1~3개월"),
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
    # ── 방산/지정학 섹터 ──
    "LMT": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=78, thesis="LMT는 F-35·미사일 방어 수주가 실제 매출로 전환되는지가 중요합니다.", window="향후 1~2분기"),
        ck("방산 ETF (ITA)", "commodity", symbol="ITA", positive_if="up", weight=85, thesis="글로벌 국방비 증가 기대가 방산주 전체 프리미엄을 좌우합니다.", window="향후 1~3개월"),
        ck("유가 (지정학 프록시)", "commodity", symbol="CL=F", positive_if="up", weight=72, thesis="유가 급등은 지정학 리스크 심화의 신호이며 방산 수요 기대를 높입니다.", window="향후 1~3개월"),
        ck("금 가격 (안전자산)", "commodity", symbol="GC=F", positive_if="up", weight=65, thesis="금 강세는 지정학 불안 → 방산주 수혜 시나리오를 지지합니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.08, weight=82, thesis="수주만 많아도 이익률이 안정적이어야 밸류 프리미엄이 유지됩니다.", window="향후 1~2분기"),
        ck("VIX (변동성)", "commodity", symbol="^VIX", positive_if="up", weight=55, thesis="시장 불안이 커지면 방산주는 방어적 포지션으로 수혜받는 경향이 있습니다.", window="향후 1~2개월"),
    ],
    "012450.KS": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.1, weight=88, thesis="한화에어로는 K9·천무 등 수출 수주가 매출로 실현돼야 멀티플이 유지됩니다.", window="향후 1~2분기"),
        ck("방산 ETF (ITA)", "commodity", symbol="ITA", positive_if="up", weight=78, thesis="글로벌 방산 심리 상승은 한국 방산주에도 직접 긍정적입니다.", window="향후 1~3개월"),
        ck("영업이익률", "earnings_metric", metric="operating_margin", positive_if="above", threshold=0.06, weight=92, thesis="한화에어로는 수출 물량이 늘어도 이익률이 뒷받침돼야 주가가 갑니다.", window="향후 1~2분기"),
        ck("유가 (지정학 프록시)", "commodity", symbol="CL=F", positive_if="up", weight=68, thesis="중동 긴장과 유가 상승은 K-방산 수출 기대를 높입니다.", window="향후 1~3개월"),
        ck("환율 (USD/KRW)", "commodity", symbol="KRW=X", positive_if="up", weight=55, thesis="원화 약세는 방산 수출 채산성에 우호적입니다.", window="향후 1~2개월"),
        ck("유럽 방산 심리 (EUAD)", "commodity", symbol="LMT", positive_if="up", weight=60, thesis="유럽 재무장 수요가 K-방산 수출의 핵심 동력입니다.", window="향후 1~3개월"),
    ],
    "RTX": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.05, weight=75, thesis="패트리어트 미사일과 항공엔진 수요가 안정적 성장을 뒷받침합니다.", window="향후 1~2분기"),
        ck("방산 ETF (ITA)", "commodity", symbol="ITA", positive_if="up", weight=82, thesis="미국 방산 섹터 전체 심리가 RTX에 직접 반영됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.08, weight=80, thesis="방산+항공 이중사업에서 마진 개선이 핵심입니다.", window="향후 1~2분기"),
        ck("유가 (군수/항공)", "commodity", symbol="CL=F", positive_if="up", weight=60, thesis="지정학 긴장과 유가 상승은 군수 수요 기대를 높입니다.", window="향후 1~3개월"),
    ],
    "GD": [
        ck("매출 성장률", "earnings_metric", metric="revenue_growth", positive_if="above", threshold=0.03, weight=72, thesis="핵잠수함·전차 수주는 장기계약이라 안정적이나 증가율 확인이 필요합니다.", window="향후 1~2분기"),
        ck("방산 ETF (ITA)", "commodity", symbol="ITA", positive_if="up", weight=80, thesis="방산 섹터 펀드 흐름이 GD에도 직접 반영됩니다.", window="향후 1~3개월"),
        ck("이익률", "earnings_metric", metric="profit_margin", positive_if="above", threshold=0.08, weight=78, thesis="Gulfstream과 방산의 이중 마진이 핵심 경쟁력입니다.", window="향후 1~2분기"),
        ck("배당수익률", "earnings_metric", metric="dividend_yield", positive_if="above", threshold=0.015, weight=55, thesis="안정적 배당은 방어주 매력의 일부입니다.", window="향후 2~4분기"),
    ],
}


def _build_geopolitical_risk_item(
    ticker: str,
    info: dict,
    commodity_cache: dict,
    stock_overlay: list,
) -> dict | None:
    """Build a geopolitical risk checklist item for Korean stocks.

    Checks oil price (CL=F), VIX (^VIX), USD/KRW (KRW=X) trends and
    searches Naver news for geopolitical keywords to determine risk level.
    Returns a fully-formed checklist item dict, or None if data is unavailable.
    """
    company_name = info.get("shortName") or info.get("longName") or ticker

    # ── 1. Fetch oil, VIX, KRW data (reuse commodity_cache or fetch fresh) ──
    geo_symbols = {"CL=F": "유가", "^VIX": "VIX", "KRW=X": "USD/KRW"}
    geo_data: dict[str, dict] = {}  # sym -> {last, month_change_pct, trend_dir}

    for sym, label in geo_symbols.items():
        try:
            hist = commodity_cache.get(sym)
            if hist is None or (hasattr(hist, "empty") and hist.empty):
                hist = StockDataService.get_stock_history(sym, period="3mo")
            if hist is not None and not hist.empty and len(hist) > 5:
                closes = hist["Close"].values.astype(float)
                last_price = float(closes[-1])
                month_ago = float(closes[-22]) if len(closes) >= 22 else float(closes[0])
                month_change = (last_price - month_ago) / month_ago * 100
                ma5 = float(np.mean(closes[-5:])) if len(closes) >= 5 else last_price
                ma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else last_price
                short_trend = (ma5 - ma20) / ma20 * 100
                if short_trend > 2:
                    trend_dir = "급상승"
                elif short_trend > 0.5:
                    trend_dir = "상승"
                elif short_trend < -2:
                    trend_dir = "급하락"
                elif short_trend < -0.5:
                    trend_dir = "하락"
                else:
                    trend_dir = "보합"
                geo_data[sym] = {
                    "last": round(last_price, 2),
                    "month_change": round(month_change, 1),
                    "trend_dir": trend_dir,
                    "short_trend": round(short_trend, 2),
                }
        except Exception:
            pass

    if not geo_data:
        return None

    # ── 2. Search geopolitical news via Naver ──
    geo_keywords = [
        f"{company_name} 지정학",
        "이란 전쟁 한국",
        "관세 한국 수출",
        "북한 리스크",
    ]
    geo_news_titles: list[str] = []
    geo_news_count = 0
    for kw in geo_keywords:
        try:
            articles = NewsCrawlerService.crawl_naver_news(kw)
            for art in articles[:3]:
                title = art.title if hasattr(art, "title") else str(art)
                if title not in geo_news_titles:
                    geo_news_titles.append(title)
                    geo_news_count += 1
        except Exception:
            pass

    # ── 3. Score geopolitical risk ──
    # Oil spike = negative for Korean manufacturers (cost pressure)
    # VIX spike = negative for EM stocks
    # KRW weakening (KRW=X rising = more KRW per USD) = mixed (hurts imports, helps exporters)
    risk_score = 50  # start neutral

    oil = geo_data.get("CL=F")
    vix = geo_data.get("^VIX")
    krw = geo_data.get("KRW=X")

    detail_parts = []
    negative_signals = []
    positive_signals = []

    if oil:
        mc = oil["month_change"]
        if mc > 10:
            risk_score -= 20
            negative_signals.append(f"유가 급등 (+{mc}%)")
        elif mc > 5:
            risk_score -= 10
            negative_signals.append(f"유가 상승 (+{mc}%)")
        elif mc < -10:
            risk_score += 15
            positive_signals.append(f"유가 급락 ({mc}%)")
        elif mc < -5:
            risk_score += 8
            positive_signals.append(f"유가 하락 ({mc}%)")
        detail_parts.append(f"유가 {oil['trend_dir']} ({'+' if mc > 0 else ''}{mc}%)")

    if vix:
        vix_level = vix["last"]
        if vix_level > 30:
            risk_score -= 20
            negative_signals.append(f"VIX 공포 구간 ({vix_level})")
        elif vix_level > 25:
            risk_score -= 12
            negative_signals.append(f"VIX 경계 구간 ({vix_level})")
        elif vix_level > 20:
            risk_score -= 5
        elif vix_level < 15:
            risk_score += 10
            positive_signals.append(f"VIX 안정 ({vix_level})")
        detail_parts.append(f"VIX {vix_level}")

    if krw:
        krw_level = krw["last"]
        mc = krw["month_change"]
        if mc > 3:
            # Won weakening sharply
            risk_score -= 8
            negative_signals.append(f"원화 약세 ({'+' if mc > 0 else ''}{mc}%)")
        elif mc < -3:
            risk_score += 5
            positive_signals.append(f"원화 강세 ({mc}%)")
        detail_parts.append(f"USD/KRW {int(krw_level)}원 ({'+' if mc > 0 else ''}{mc}%)")

    # News sentiment: check for alarming keywords
    alarm_keywords = ["전쟁", "이란", "공격", "제재", "sanctions", "tariff", "관세", "보복", "핵", "미사일", "봉쇄"]
    calm_keywords = ["휴전", "협상", "타결", "완화", "해제", "면제"]
    alarm_count = 0
    calm_count = 0
    for title in geo_news_titles:
        title_lower = title.lower()
        if any(kw in title_lower for kw in alarm_keywords):
            alarm_count += 1
        if any(kw in title_lower for kw in calm_keywords):
            calm_count += 1

    if alarm_count >= 3:
        risk_score -= 15
        negative_signals.append(f"지정학 뉴스 경보 ({alarm_count}건)")
    elif alarm_count >= 1:
        risk_score -= 5
    if calm_count >= 2:
        risk_score += 10
        positive_signals.append("긴장 완화 뉴스 감지")

    # Clamp score
    risk_score = max(5, min(95, risk_score))

    # Determine status
    if risk_score >= 60:
        status = "positive"
    elif risk_score <= 35:
        status = "negative"
    else:
        status = "neutral"

    # Build detail string
    detail = " / ".join(detail_parts) if detail_parts else "데이터 부족"
    if negative_signals:
        detail += " — " + ", ".join(negative_signals[:2])
    elif positive_signals:
        detail += " — " + ", ".join(positive_signals[:2])

    # Build trend data from oil price (most impactful for Korean manufacturers)
    trend_data = []
    oil_hist = commodity_cache.get("CL=F")
    if oil_hist is None or (hasattr(oil_hist, "empty") and oil_hist.empty):
        try:
            oil_hist = StockDataService.get_stock_history("CL=F", period="3mo")
        except Exception:
            oil_hist = pd.DataFrame()
    if oil_hist is not None and not oil_hist.empty and len(oil_hist) > 5:
        c_min = float(oil_hist["Close"].min())
        c_max = float(oil_hist["Close"].max())
        c_range = c_max - c_min if c_max > c_min else 1.0
        step = max(1, len(oil_hist) // 60)
        for idx, row in oil_hist.iloc[::step].iterrows():
            d = str(idx.date()) if hasattr(idx, "date") else str(idx)
            trend_data.append({
                "date": d,
                "close": round(float(row["Close"]), 2),
                "norm": round((float(row["Close"]) - c_min) / c_range * 100, 1),
            })

    return {
        "name": "지정학적 리스크",
        "status": status,
        "value": None,
        "detail": detail,
        "trend_data": trend_data,
        "stock_overlay": stock_overlay,
        "correlation": 0.0,
        "corr_label": "거시 리스크",
        "thresholds": {},
        "source": "유가(CL=F) / VIX / USD·KRW + 네이버 뉴스",
        "importance": 80,
        "window": "향후 1~3개월",
        "why_it_matters": "한국 수출 대기업은 유가, 환율, 글로벌 리스크에 직접적 영향을 받습니다. "
                          "유가 급등은 제조 원가를 압박하고, VIX 상승은 외국인 자금 이탈을, "
                          "원화 약세는 수입 비용 증가를 초래합니다.",
        "expected_condition": "유가 안정 + VIX 20 이하 + 원화 안정 시 긍정적",
        "item_score": risk_score,
        "lead_signal": "리스크 완화" if status == "positive" else (
            "리스크 경고" if status == "negative" else "리스크 중립"
        ),
        "geo_details": {
            "oil": geo_data.get("CL=F"),
            "vix": geo_data.get("^VIX"),
            "krw": geo_data.get("KRW=X"),
            "news_count": geo_news_count,
            "alarm_keywords_found": alarm_count,
        },
    }


@router.get("/analysis/{ticker}/checklist-live")
def get_checklist_live(ticker: str) -> dict:
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
    cached = _get_best_cached(cache_key, 86400)
    if cached is not None:
        # If it was a rate-limited fallback, only cache 5 min
        if cached.get("rate_limited"):
            if time.time() - _ANALYSIS_CACHE[cache_key][0] > 300:
                pass  # Expired fallback — retry below
            else:
                return _strip_news_from_checklist(cached)
        else:
            return _strip_news_from_checklist(cached)

    # Also keep a "last good" cache that never expires, for rate limit fallback
    stale_key = f"checklist-stale:{ticker}"

    try:
        sources = CHECKLIST_SOURCES.get(ticker, CHECKLIST_SOURCES.get(ticker.replace(".KS", "").replace(".KQ", ""), []))

        # Fetch stock data — use GLOBAL CACHE to avoid duplicate yfinance calls
        info = get_yf_info(ticker)
        # If info is empty/rate-limited, still proceed with history-based analysis
        info_available = isinstance(info, dict) and len(info) > 3
        if not info_available:
            # Try stale cache first
            stale = _ANALYSIS_CACHE.get(stale_key)
            if stale:
                return stale[1]
            # Proceed without info — earnings metrics will be empty but commodity items still work
            info = {"shortName": ticker}
        sector_id = _infer_sector_id_from_profile(ticker, info=info)
        if not sources:
            sources = _build_dynamic_checklist_sources(ticker, info=info)
        # Use global cached financials — avoids separate yfinance call
        try:
            qf, qbs = get_yf_financials(ticker)
            stock = type("_S", (), {"quarterly_financials": qf, "quarterly_balance_sheet": qbs})()
            earnings_fallback = _derive_earnings_fallbacks(stock)
        except Exception:
            earnings_fallback = {}
            stock = type("_S", (), {"quarterly_financials": pd.DataFrame(), "quarterly_balance_sheet": pd.DataFrame()})()
        # Build earnings_data from 3 sources (priority order):
        #   1. yfinance stock.info (fastest, but rate-limited on servers)
        #   2. yfinance quarterly_financials computed fallback
        #   3. Alternative sources: Naver Finance (KR) / Yahoo web scraping (US)
        alt_data = {}
        try:
            alt_data = fetch_fundamentals(ticker)
        except Exception:
            pass

        def _pick(info_key: str, fb_key: str, alt_key: str | None = None):
            """Pick first non-None value from info → yf fallback → alt source."""
            v = info.get(info_key)
            if v is not None:
                return v
            v = earnings_fallback.get(fb_key)
            if v is not None:
                return v
            if alt_key:
                return alt_data.get(alt_key)
            return alt_data.get(fb_key)

        earnings_data = {
            "revenue_growth": _pick("revenueGrowth", "revenue_growth"),
            "earnings_growth": _pick("earningsGrowth", "earnings_growth"),
            "profit_margin": _pick("profitMargins", "profit_margin"),
            "operating_margin": _pick("operatingMargins", "operating_margin"),
            "roe": _pick("returnOnEquity", "roe"),
            "dividend_yield": _pick("dividendYield", "dividend_yield"),
            "price_to_book": _pick("priceToBook", "price_to_book"),
            "pe_ratio": _pick("trailingPE", "pe_ratio"),
            "forward_pe": _pick("forwardPE", "forward_pe"),
        }

        # Fetch stock's own 1-year price history for correlation analysis
        stock_hist = pd.DataFrame()
        try:
            with limit_yfinance():
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

        with ThreadPoolExecutor(max_workers=3) as executor:
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

                    # Graduated scoring: continuous 0-100 per item, not just pass/fail
                    if positive_if == "above":
                        if threshold > 0:
                            ratio = val / threshold  # how close to target
                            if ratio >= 1.5:
                                item_score = 95  # far exceeds target
                            elif ratio >= 1.0:
                                item_score = 70 + int((ratio - 1.0) / 0.5 * 25)  # 70-95
                            elif ratio >= 0.5:
                                item_score = 40 + int((ratio - 0.5) / 0.5 * 30)  # 40-70
                            elif ratio >= 0:
                                item_score = 20 + int(ratio / 0.5 * 20)  # 20-40
                            else:
                                item_score = max(5, 20 + int(ratio * 20))  # negative val
                        else:
                            item_score = 70 if val >= threshold else 30
                        # Status from score
                        if item_score >= 65:
                            item["status"] = "positive"
                        elif item_score <= 30:
                            item["status"] = "negative"
                        else:
                            item["status"] = "neutral"
                    elif positive_if == "below":
                        if threshold > 0:
                            ratio = val / threshold
                            if ratio <= 0.5:
                                item_score = 95  # far below limit = very good
                            elif ratio <= 1.0:
                                item_score = 65 + int((1.0 - ratio) / 0.5 * 30)  # 65-95
                            elif ratio <= 1.5:
                                item_score = 35 + int((1.5 - ratio) / 0.5 * 30)  # 35-65
                            elif ratio <= 2.0:
                                item_score = 15 + int((2.0 - ratio) / 0.5 * 20)  # 15-35
                            else:
                                item_score = max(5, 15 - int((ratio - 2.0) * 5))  # 5-15
                        else:
                            item_score = 70 if val <= threshold else 30
                        if item_score >= 65:
                            item["status"] = "positive"
                        elif item_score <= 30:
                            item["status"] = "negative"
                        else:
                            item["status"] = "neutral"
                    else:
                        item_score = 50
                    item["item_score"] = max(0, min(100, item_score))
                    if "margin" in metric or "growth" in metric or metric == "roe" or metric == "dividend_yield":
                        item["value"] = round(val * 100, 1)
                        pct_str = f"{round(val * 100, 1)}%"
                        # Build contextual detail text
                        thr_pct = round(threshold * 100, 1)
                        if positive_if == "above":
                            if val >= threshold * 1.5:
                                ctx = f"기준({thr_pct}%) 대비 크게 상회 — 매우 양호"
                            elif val >= threshold:
                                ctx = f"기준({thr_pct}%) 충족 — 양호"
                            elif val >= threshold * 0.5:
                                ctx = f"기준({thr_pct}%) 근접 — 주의 필요"
                            elif val > 0:
                                ctx = f"기준({thr_pct}%) 대비 부족 — 부진"
                            else:
                                ctx = f"마이너스 전환 — 위험 신호"
                        else:
                            if val <= threshold * 0.5:
                                ctx = f"기준({thr_pct}%) 대비 크게 하회 — 매우 양호"
                            elif val <= threshold:
                                ctx = f"기준({thr_pct}%) 이하 — 양호"
                            elif val <= threshold * 1.5:
                                ctx = f"기준({thr_pct}%) 초과 — 주의"
                            else:
                                ctx = f"기준({thr_pct}%) 크게 초과 — 부담"
                        trend_ctx = ""
                        if quarterly_trend:
                            if ("+" in quarterly_trend or "상승" in quarterly_trend) and positive_if == "above":
                                trend_ctx = f" | {quarterly_trend} ↑ 개선 추세"
                            elif ("-" in quarterly_trend or "−" in quarterly_trend or "하락" in quarterly_trend):
                                trend_ctx = f" | {quarterly_trend} ↓ 하락 추세"
                            else:
                                trend_ctx = f" | {quarterly_trend}"
                        item["detail"] = f"{pct_str} — {ctx}{trend_ctx}"
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
                        # Non-percentage metrics (PER, PBR, etc.)
                        item["value"] = round(val, 2)
                        thr_str = f"{round(threshold, 2)}"
                        ratio = val / threshold if threshold > 0 else 1.0
                        if positive_if == "below":
                            if ratio <= 0.5:
                                ctx = f"기준({thr_str}) 대비 크게 하회 — 저평가 매력"
                            elif ratio <= 1.0:
                                ctx = f"기준({thr_str}) 이하 — 적정 수준"
                            elif ratio <= 1.5:
                                ctx = f"기준({thr_str}) 초과 — 밸류 부담"
                            else:
                                ctx = f"기준({thr_str}) 대비 {ratio:.1f}배 — 고평가 부담 큼"
                        else:
                            if ratio >= 1.5:
                                ctx = f"기준({thr_str}) 대비 크게 상회 — 우수"
                            elif ratio >= 1.0:
                                ctx = f"기준({thr_str}) 충족 — 양호"
                            else:
                                ctx = f"기준({thr_str}) 미달 — 부진"
                        item["detail"] = f"{round(val, 2)} — {ctx}"
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
                    # Provide meaningful fallback for legitimately missing data
                    if metric == "pe_ratio":
                        item["detail"] = "적자 구간 (P/E 산출 불가)"
                        item["status"] = "negative"
                        item["value"] = None
                        item["importance"] = src.get("weight", metadata["weight"])
                    elif metric == "dividend_yield":
                        item["detail"] = "무배당 (0%)"
                        item["value"] = 0
                        item["status"] = "neutral"
                        item["importance"] = src.get("weight", metadata["weight"])
                    elif metric == "price_to_book":
                        item["detail"] = "데이터 조회 실패"
                        item["importance"] = src.get("weight", metadata["weight"])
                    else:
                        item["detail"] = "데이터 조회 실패"
                        item["importance"] = src.get("weight", metadata["weight"])

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

                        # STATUS + item_score based on TREND DIRECTION
                        # Convert trend to continuous score (0-100)
                        if positive_if == "up":
                            # Positive trend = good → higher score
                            if short_trend > 3:
                                c_item_score = 90
                            elif short_trend > 1:
                                c_item_score = 65 + int((short_trend - 1) / 2 * 25)
                            elif short_trend > -0.5:
                                c_item_score = 45 + int((short_trend + 0.5) / 1.5 * 20)
                            elif short_trend > -2:
                                c_item_score = 25 + int((short_trend + 2) / 1.5 * 20)
                            else:
                                c_item_score = max(10, 25 + int((short_trend + 2) * 5))
                        elif positive_if == "down":
                            # Negative trend = good → higher score
                            if short_trend < -3:
                                c_item_score = 90
                            elif short_trend < -1:
                                c_item_score = 65 + int((-1 - short_trend) / 2 * 25)
                            elif short_trend < 0.5:
                                c_item_score = 45 + int((0.5 - short_trend) / 1.5 * 20)
                            elif short_trend < 2:
                                c_item_score = 25 + int((2 - short_trend) / 1.5 * 20)
                            else:
                                c_item_score = max(10, 25 - int((short_trend - 2) * 5))
                        elif positive_if == "stable":
                            c_item_score = max(10, 80 - int(abs(short_trend) * 15))
                        else:
                            c_item_score = 50

                        c_item_score = max(0, min(100, c_item_score))
                        item["item_score"] = c_item_score

                        if c_item_score >= 65:
                            item["status"] = "positive"
                        elif c_item_score <= 30:
                            item["status"] = "negative"
                        else:
                            item["status"] = "neutral"

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

        # NOTE: News items are NO LONGER injected into the checklist.
        # News analysis is served separately via /analysis/{ticker}/news-analysis endpoint
        # and displayed in the dedicated "실시간 뉴스 분석" section on the frontend.

        # ── PRELIMINARY EARNINGS — auto-inject if found ──
        # This is NOT a news item — it's actual financial data extracted from earnings announcements
        if preliminary_earnings.get("found"):
            pe_data = preliminary_earnings["data"]
            pe_headlines = preliminary_earnings.get("headlines", [])[:3]

            # Build detail text from actual numbers
            detail_parts = []
            if "revenue_억" in pe_data:
                rev = pe_data["revenue_억"]
                if rev >= 10000:
                    detail_parts.append(f"매출 {rev/10000:.1f}조원")
                else:
                    detail_parts.append(f"매출 {rev:,.0f}억원")
            if "operating_profit_억" in pe_data:
                op = pe_data["operating_profit_억"]
                if op >= 10000:
                    detail_parts.append(f"영업이익 {op/10000:.1f}조원")
                else:
                    detail_parts.append(f"영업이익 {op:,.0f}억원")
            if "net_income_억" in pe_data:
                ni = pe_data["net_income_억"]
                if ni >= 10000:
                    detail_parts.append(f"순이익 {ni/10000:.1f}조원")
                else:
                    detail_parts.append(f"순이익 {ni:,.0f}억원")
            if "revenue_usd_b" in pe_data:
                detail_parts.append(f"매출 ${pe_data['revenue_usd_b']:.1f}B")
            if "op_profit_usd_b" in pe_data:
                detail_parts.append(f"영업이익 ${pe_data['op_profit_usd_b']:.1f}B")

            detail_text = " / ".join(detail_parts) if detail_parts else "잠정실적 발표 확인됨"

            # Determine status: positive if revenue/profit numbers are present (earnings announcements are usually bullish signals)
            # The actual sentiment is determined by whether results beat expectations
            has_growth_signal = False
            if pe_headlines:
                headline_text = " ".join(pe_headlines).lower()
                if any(kw in headline_text for kw in ["사상최대", "호실적", "서프라이즈", "beat", "record", "증가", "성장", "흑자전환"]):
                    has_growth_signal = True
                    earnings_status = "positive"
                    earnings_score = 85
                elif any(kw in headline_text for kw in ["부진", "감소", "적자", "miss", "하락", "축소"]):
                    earnings_status = "negative"
                    earnings_score = 25
                else:
                    earnings_status = "neutral"
                    earnings_score = 55
            else:
                earnings_status = "neutral"
                earnings_score = 55

            results.append({
                "name": "잠정실적 발표",
                "status": earnings_status,
                "value": None,
                "detail": detail_text,
                "trend_data": [],
                "stock_overlay": stock_overlay,
                "correlation": 0.0,
                "corr_label": "실적 직접 반영",
                "thresholds": {},
                "source": preliminary_earnings.get("source", "뉴스 잠정실적 크롤링"),
                "importance": 95,  # Highest importance — earnings are the #1 driver
                "window": "당분기",
                "why_it_matters": "잠정실적은 주가에 가장 직접적인 영향을 미치는 데이터입니다. 시장 컨센서스 대비 서프라이즈 여부가 핵심입니다.",
                "expected_condition": "컨센서스 대비 매출/영업이익 초과 시 주가 상승 압력, 미달 시 하락 압력",
                "item_score": earnings_score,
                "lead_signal": "실적 호조" if earnings_status == "positive" else ("실적 부진" if earnings_status == "negative" else "실적 확인 필요"),
                "preliminary_data": pe_data,
                "preliminary_headlines": pe_headlines,
            })

        # ── GEOPOLITICAL RISK — auto-inject for Korean stocks (.KS/.KQ) ──
        is_krx_ticker = ticker.endswith(".KS") or ticker.endswith(".KQ")
        if is_krx_ticker:
            try:
                geo_item = _build_geopolitical_risk_item(
                    ticker, info, commodity_cache, stock_overlay
                )
                if geo_item:
                    results.append(geo_item)
            except Exception:
                pass

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
        # Only cache for 24h if we have good data; bad data gets 5min cache
        has_data = any(
            item.get("detail") not in ("데이터 없음", "조회 실패", "")
            for item in results
            if item.get("detail")
        )
        if has_data:
            _set_cached(cache_key, response)
            _save_disk_cached(cache_key, response)
            # Also save as stale backup for rate limit situations
            _ANALYSIS_CACHE[stale_key] = (time.time(), response)
        else:
            # Bad/empty result — cache only 5 min so we retry soon
            _ANALYSIS_CACHE[cache_key] = (time.time() - 86400 + 300, response)
        return response

    except Exception as e:
        # If rate limited or error, try to return stale cached data
        stale = _ANALYSIS_CACHE.get(stale_key)
        if stale:
            return stale[1]
        disk_stale = _load_disk_cached(cache_key, 86400, allow_stale=True)
        if disk_stale is not None:
            return disk_stale
        return {"ticker": ticker.upper(), "checklist": [], "error": str(e)}


@router.get("/analysis/stock-search/{query}")
def search_stocks(query: str) -> dict:
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
def get_sector_pulse(sector_id: str) -> dict:
    cache_key = f"sector-pulse:{sector_id}"
    cached = _get_best_cached(cache_key, 600)
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
        _save_disk_cached(cache_key, response)
        return response
    except Exception as e:
        stale = _load_disk_cached(cache_key, 600, allow_stale=True)
        if stale is not None:
            return stale
        return {"sector_id": sector_id, "checklist": [], "error": str(e)}


@router.get("/commodities/history/{symbol}")
def get_commodity_history(symbol: str, period: str = "6mo") -> dict:
    """Get commodity price history for charting."""
    try:
        hist = StockDataService.get_stock_history(symbol, period=period)
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


@router.get("/analysis/rankings/top-ranked")
def get_top_ranked_rankings() -> dict:
    """Stable rankings endpoint that does not collide with /analysis/{ticker}."""
    return get_top_ranked()


@router.get("/analysis/top-ranked")
def get_top_ranked() -> dict:
    """Return top 10 stocks ranked by composite score (cached 10 min).
    Uses cached chart data (from StockDataService) instead of direct yfinance
    to avoid rate limiting on Render."""
    cache_key = "top-ranked-v2"
    cached = _get_cached_ttl(cache_key, 600)
    if cached is not None:
        return cached

    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_tickers = list(TOP_PICK_SECTOR_MAP.keys())
    results = []

    def score_stock(ticker: str) -> dict | None:
        try:
            # Use StockDataService (has its own cache) instead of direct yf.Ticker
            hist = StockDataService.get_stock_history(ticker, period="3mo")
            if hist.empty or len(hist) < 5:
                return None

            price = float(hist["Close"].iloc[-1])
            name = TOP_PICK_NAME_MAP.get(_ticker_key(ticker), "")

            # Only fall back to cached info name if TOP_PICK_NAME_MAP didn't have it
            if not name:
                info_cached = _ANALYSIS_CACHE.get(f"info:{ticker}")
                if info_cached:
                    _, info_data = info_cached
                    if isinstance(info_data, dict) and info_data.get("name"):
                        name = info_data["name"]

                if not name:
                    from services.stock_data import _cache as _stock_cache
                    stock_cached = _stock_cache.get(f"info:{ticker}")
                    if stock_cached and isinstance(stock_cached, tuple) and len(stock_cached) >= 2:
                        sc_data = stock_cached[1]
                        if isinstance(sc_data, dict) and sc_data.get("name"):
                            name = sc_data["name"]

            if not name:
                name = ticker

            score = 50  # base
            rsi = None
            if len(hist) >= 14:
                delta = hist["Close"].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 1
                rsi = 100 - (100 / (1 + rs))

            # RSI score
            if rsi is not None:
                if rsi < 30: score += 15
                elif rsi < 45: score += 8
                elif rsi > 70: score -= 10
                elif rsi > 60: score -= 5

            # Momentum (1mo return)
            if len(hist) >= 21:
                ret_1m = (price - float(hist["Close"].iloc[-21])) / float(hist["Close"].iloc[-21]) * 100
                if ret_1m > 10: score += 12
                elif ret_1m > 3: score += 6
                elif ret_1m < -10: score -= 8
                elif ret_1m < -3: score -= 4
            else:
                ret_1m = 0

            # Use fundamentals service (Naver/Yahoo scraping) instead of yfinance .info
            try:
                fund = fetch_fundamentals(ticker)
                rev_growth = fund.get("revenue_growth")
                if rev_growth is not None:
                    if rev_growth > 0.2: score += 10
                    elif rev_growth > 0: score += 5
                    elif rev_growth < -0.1: score -= 8
                margin = fund.get("profit_margin")
                if margin is not None:
                    if margin > 0.2: score += 8
                    elif margin > 0: score += 3
                    elif margin < 0: score -= 5
            except Exception:
                pass

            score = max(0, min(100, score))
            sector_id = TOP_PICK_SECTOR_MAP.get(ticker, "")

            return {
                "ticker": ticker,
                "name": name,
                "price": round(price, 2),
                "change_1m": round(ret_1m, 1) if len(hist) >= 21 else None,
                "score": score,
                "rsi": round(rsi, 1) if rsi else None,
                "sector_id": sector_id,
                "sector_name": SECTOR_NAME_MAP.get(sector_id, ""),
                "flag": "KR" if ticker.endswith(".KS") or ticker.endswith(".KQ") else "US",
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(score_stock, t): t for t in all_tickers}
        for future in as_completed(futures, timeout=45):
            try:
                result = future.result(timeout=20)
                if result:
                    results.append(result)
            except Exception:
                pass

    results.sort(key=lambda x: x["score"], reverse=True)
    top10 = results[:10]

    # If too few results, fill with static fallback from sectors data
    if len(top10) < 5:
        existing_tickers = {r["ticker"] for r in top10}
        for ticker, sector_id in list(TOP_PICK_SECTOR_MAP.items())[:15]:
            if ticker in existing_tickers:
                continue
            top10.append({
                "ticker": ticker,
                "name": TOP_PICK_NAME_MAP.get(_ticker_key(ticker), ticker),
                "price": 0,
                "change_1m": None,
                "score": 50,  # neutral default
                "rsi": None,
                "sector_id": sector_id,
                "sector_name": SECTOR_NAME_MAP.get(sector_id, ""),
                "flag": "KR" if ticker.endswith(".KS") or ticker.endswith(".KQ") else "US",
            })
            if len(top10) >= 10:
                break

    response = {"rankings": top10[:10], "total_analyzed": len(results)}
    if results:  # Only cache if we got real data
        _set_cached(cache_key, response)
    return response


@router.get("/commodities")
def get_commodities() -> list[CommodityPrice]:
    """Get all tracked commodity prices."""
    return CommodityDataService.get_commodity_prices()


@router.get("/commodities/{sector_name}")
def get_sector_commodities(sector_name: str) -> list[CommodityPrice]:
    """Get commodities related to a specific sector."""
    return CommodityDataService.get_related_commodities(sector_name)


# ═══════════════════════════════════════════════════════════════
# MACRO / GEOPOLITICAL EVENTS SECTION
# ═══════════════════════════════════════════════════════════════

_MACRO_QUERIES = [
    # Geopolitical
    "이란 전쟁 중동 유가",
    "미중 관세 무역전쟁",
    "한국 주식시장 지정학 리스크",
    # Oil & Commodities
    "국제유가 WTI 브렌트",
    "원자재 가격 금 구리",
    # Macro economy
    "미국 금리 FOMC 연준",
    "환율 원달러 달러 강세",
    "인플레이션 CPI 물가",
    # Market-wide
    "코스피 코스닥 시장 전망",
]

_MACRO_CATEGORIES = {
    "지정학": ["이란", "전쟁", "중동", "미사일", "제재", "대만", "우크라이나", "러시아", "북한", "군사", "지정학", "war", "iran", "geopolitical", "sanctions", "strike"],
    "유가/원자재": ["유가", "wti", "브렌트", "brent", "원유", "oil", "opec", "원자재", "금값", "구리", "commodity", "crude"],
    "금리/통화": ["금리", "fomc", "연준", "fed", "기준금리", "인하", "인상", "rate", "interest", "환율", "원달러", "달러", "dollar", "yen", "엔화"],
    "관세/무역": ["관세", "tariff", "무역", "trade war", "수출규제", "수입", "반덤핑", "미중", "관세전쟁", "보호무역"],
    "경기/물가": ["인플레이션", "cpi", "물가", "디플레이션", "경기침체", "recession", "gdp", "고용", "실업률", "소비자심리"],
    "시장전반": ["코스피", "코스닥", "나스닥", "s&p", "증시", "주식시장", "rally", "crash", "sell-off", "폭락", "급등"],
}


def _classify_macro_category(title: str) -> str:
    tl = title.lower()
    best_cat = "시장전반"
    best_score = 0
    for cat, keywords in _MACRO_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in tl)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def _assess_macro_impact(title: str, category: str) -> tuple[str, str]:
    """Return (direction, explanation) for macro news impact on Korean stocks."""
    tl = title.lower()
    direction = "neutral"
    explanation = ""

    if category == "지정학":
        if any(w in tl for w in ["휴전", "합의", "평화", "완화", "철수"]):
            direction = "positive"
            explanation = "지정학 리스크 완화 → 위험자산 선호 회복, 한국 증시 반등 기대"
        else:
            direction = "negative"
            explanation = "지정학 리스크 확대 → 안전자산 선호, 외국인 매도 압력 증가"

    elif category == "유가/원자재":
        if any(w in tl for w in ["급등", "상승", "폭등", "돌파", "surge", "jump", "rally", "high"]):
            direction = "negative"
            explanation = "유가 상승 → 수입 비용 증가, 인플레 우려, 제조업 마진 압박"
        elif any(w in tl for w in ["하락", "급락", "폭락", "drop", "fall", "plunge"]):
            direction = "positive"
            explanation = "유가 하락 → 수입 비용 감소, 인플레 완화, 소비 여력 확대"
        else:
            direction = "neutral"
            explanation = "원자재 가격 변동 — 수출입 기업 영향 모니터링 필요"

    elif category == "금리/통화":
        if any(w in tl for w in ["인하", "비둘기", "dovish", "cut", "완화"]):
            direction = "positive"
            explanation = "금리 인하 기대 → 유동성 확대, 성장주·신흥국 자금 유입 기대"
        elif any(w in tl for w in ["인상", "매파", "hawkish", "hike", "긴축"]):
            direction = "negative"
            explanation = "금리 인상/긴축 → 유동성 축소, 외국인 자금 이탈 우려"
        elif any(w in tl for w in ["환율", "원달러", "달러 강세", "달러강세"]):
            if any(w in tl for w in ["약세", "하락"]):
                direction = "positive"
                explanation = "원화 강세 → 외국인 투자 매력 증가, 수입 비용 감소"
            else:
                direction = "negative"
                explanation = "원화 약세 → 외국인 매도 압력, 수입 물가 상승"
        else:
            direction = "neutral"
            explanation = "통화·금리 정책 변화 모니터링 필요"

    elif category == "관세/무역":
        if any(w in tl for w in ["완화", "면제", "철회", "합의", "해소"]):
            direction = "positive"
            explanation = "무역 갈등 완화 → 수출 기업 수혜, 글로벌 공급망 안정"
        else:
            direction = "negative"
            explanation = "무역 갈등 심화 → 수출 기업 타격, 공급망 불확실성 확대"

    elif category == "경기/물가":
        if any(w in tl for w in ["둔화", "하락", "안정", "개선"]) and any(w in tl for w in ["인플레이션", "cpi", "물가"]):
            direction = "positive"
            explanation = "물가 안정 → 금리 인하 기대, 소비 회복 긍정적"
        elif any(w in tl for w in ["침체", "recession", "둔화", "위축"]):
            direction = "negative"
            explanation = "경기 둔화 우려 → 기업 실적 부진 가능성, 방어적 투자 필요"
        else:
            direction = "neutral"
            explanation = "경기 지표 변동 — 시장 반응 모니터링 필요"

    else:
        if any(w in tl for w in ["급등", "반등", "상승", "rally", "surge"]):
            direction = "positive"
            explanation = "시장 전반 긍정적 흐름"
        elif any(w in tl for w in ["급락", "폭락", "하락", "crash", "sell"]):
            direction = "negative"
            explanation = "시장 전반 약세 흐름"

    return direction, explanation


@router.get("/analysis/macro-events")
def get_macro_events() -> dict:
    """
    Fetch current geopolitical and macroeconomic events affecting Korean stock market.
    Categorized by type with impact assessment.
    """
    cache_key = "macro-events:global"
    cached = _get_best_cached(cache_key, 900)
    if cached is not None:
        return cached

    articles = _search_stock_latest_news(_MACRO_QUERIES, max_per_query=5)

    # Deduplicate and classify
    seen_titles = set()
    events = []
    for a in articles:
        title = a.get("title", "")
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        category = _classify_macro_category(title)
        direction, explanation = _assess_macro_impact(title, category)

        events.append({
            "title": title,
            "source": a.get("source", ""),
            "published_at": a.get("published_at", ""),
            "category": category,
            "impact_direction": direction,
            "explanation": explanation,
        })

    # Sort: negative first (most impactful to Korean market), then positive, then neutral
    priority = {"negative": 0, "positive": 1, "neutral": 2}
    events.sort(key=lambda e: priority.get(e["impact_direction"], 2))

    # Group by category
    by_category: dict[str, list] = {}
    for e in events:
        cat = e["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(e)

    # Summary: count by direction
    neg_count = sum(1 for e in events if e["impact_direction"] == "negative")
    pos_count = sum(1 for e in events if e["impact_direction"] == "positive")
    if neg_count > pos_count * 2:
        market_sentiment = "매우 부정적"
        sentiment_detail = "지정학·매크로 악재가 다수 — 방어적 투자 전략 권장"
    elif neg_count > pos_count:
        market_sentiment = "부정적"
        sentiment_detail = "악재가 우세 — 리스크 관리 강화 필요"
    elif pos_count > neg_count * 2:
        market_sentiment = "매우 긍정적"
        sentiment_detail = "매크로 환경 우호적 — 적극적 투자 기회"
    elif pos_count > neg_count:
        market_sentiment = "긍정적"
        sentiment_detail = "호재가 우세 — 점진적 비중 확대 고려"
    else:
        market_sentiment = "중립"
        sentiment_detail = "호·악재 혼재 — 선별적 종목 접근 필요"

    result = {
        "events": events[:30],
        "by_category": by_category,
        "summary": {
            "total": len(events),
            "positive": pos_count,
            "negative": neg_count,
            "neutral": len(events) - pos_count - neg_count,
            "market_sentiment": market_sentiment,
            "sentiment_detail": sentiment_detail,
        },
    }

    _set_cached(cache_key, result)
    _save_disk_cached(cache_key, result)
    return result


@router.get("/analysis/{ticker}/research")
def get_stock_research(ticker: str) -> dict:
    """
    Fetch all external research data for a stock:
    - KRX: Naver analyst reports + DART filings + consensus estimates
    - US: SEC EDGAR filings + Yahoo analyst targets
    """
    cache_key = f"research:{ticker}"
    cached = _get_best_cached(cache_key, 1800)
    if cached is not None:
        return cached

    result = fetch_all_research(ticker)

    _set_cached(cache_key, result)
    _save_disk_cached(cache_key, result)
    return result


def _assess_priced_in(title: str, ticker: str, info: dict | None, direction: str) -> dict:
    """
    Assess whether a news item is already priced into the stock.
    Returns {priced_in_level, priced_in_reason, forward_prediction}.

    Levels: "fully_priced" / "partially_priced" / "not_priced" / "unknown"
    """
    text = title.lower()
    result = {"priced_in_level": "unknown", "priced_in_reason": "", "forward_prediction": ""}

    # Determine if the news is backward-looking (already happened) or forward-looking
    is_past = any(kw in text for kw in [
        "발표", "announced", "reported", "기록", "달성", "recorded",
        "confirmed", "확인", "completed", "완료", "승인", "approved",
    ])
    is_future = any(kw in text for kw in [
        "전망", "outlook", "expected", "예상", "계획", "plans", "will",
        "예정", "forecast", "가능성", "추진", "검토", "considering",
    ])
    is_rumor = any(kw in text for kw in [
        "보도", "소문", "rumors", "reportedly", "sources say", "관측",
        "것으로 알려", "가능성", "speculation",
    ])

    # Check recent price momentum from yfinance for priced-in assessment
    recent_change = None
    try:
        if info:
            # 1M change as proxy for "has the market already moved on this?"
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
            current = info.get("currentPrice") or info.get("regularMarketPrice")
            if prev_close and current and prev_close > 0:
                recent_change = (current - prev_close) / prev_close
    except Exception:
        pass

    if is_past:
        if recent_change is not None:
            if direction == "positive" and recent_change > 0.02:
                result["priced_in_level"] = "partially_priced"
                result["priced_in_reason"] = "이미 발표된 호재 — 주가가 일부 반영한 것으로 보이나 추가 상승 여력 확인 필요"
            elif direction == "negative" and recent_change < -0.02:
                result["priced_in_level"] = "partially_priced"
                result["priced_in_reason"] = "이미 발표된 악재 — 주가가 일부 반영한 것으로 보이나 추가 하락 리스크 확인 필요"
            else:
                result["priced_in_level"] = "not_priced"
                result["priced_in_reason"] = "발표 내용이 주가에 아직 충분히 반영되지 않은 것으로 판단"
        else:
            result["priced_in_level"] = "partially_priced"
            result["priced_in_reason"] = "이미 발표된 내용 — 시장이 일부 반영했을 가능성"
    elif is_rumor:
        result["priced_in_level"] = "not_priced"
        result["priced_in_reason"] = "루머/관측 단계 — 공식 확인 시 주가 변동 가능성 높음"
    elif is_future:
        result["priced_in_level"] = "not_priced"
        result["priced_in_reason"] = "미래 전망/계획 — 실현 여부에 따라 주가 반영 예정"
    else:
        result["priced_in_level"] = "unknown"
        result["priced_in_reason"] = "선반영 여부 판단을 위해 추가 데이터 필요"

    # Forward prediction based on news type
    if any(kw in text for kw in ["실적", "매출", "earnings", "revenue"]):
        if direction == "positive":
            result["forward_prediction"] = "실적 호조 → 다음 분기 가이던스 상향 기대 / 애널리스트 목표가 상향 가능성. 동일 섹터 종목도 동반 수혜 기대."
        else:
            result["forward_prediction"] = "실적 부진 → 가이던스 하향 리스크. 다음 실적 시즌까지 밸류에이션 재조정 압력."
    elif any(kw in text for kw in ["수주", "계약", "contract", "납품", "supply"]):
        result["forward_prediction"] = "수주/계약 → 향후 매출 파이프라인 확대. 수주잔고 기반 중기 실적 개선 기대."
    elif any(kw in text for kw in ["규제", "관세", "tariff", "제재", "regulation"]):
        result["forward_prediction"] = "규제/관세 → 단기 불확실성 확대. 정책 확정 시까지 변동성 지속 예상. 대체 수혜주 탐색 필요."
    elif any(kw in text for kw in ["신제품", "launch", "출시", "신기술"]):
        result["forward_prediction"] = "신제품/기술 → 시장 확대 기대. 초기 판매 데이터가 핵심 트리거. 경쟁사 대응 모니터링 필요."
    elif any(kw in text for kw in ["목표가", "target", "투자의견", "rating", "upgrade", "downgrade"]):
        if direction == "positive":
            result["forward_prediction"] = "애널리스트 상향 → 기관 매수세 유입 예상. 다른 증권사 연쇄 상향 가능성 주시."
        else:
            result["forward_prediction"] = "애널리스트 하향 → 기관 포지션 축소 압력. 컨센서스 하향 추세 확인 필요."
    elif any(kw in text for kw in ["인수", "합병", "m&a", "acquisition"]):
        result["forward_prediction"] = "M&A → 합병 시너지 효과는 통상 6~12개월 후 반영. 인수 프리미엄과 부채 증가 주시."
    elif any(kw in text for kw in ["hbm", "메모리", "반도체", "semiconductor"]):
        result["forward_prediction"] = "반도체 업황 → AI 수요 사이클과 연동. HBM/DRAM 가격 추이가 실적 방향을 선행."
    elif any(kw in text for kw in ["배터리", "리튬", "ev ", "전기차"]):
        result["forward_prediction"] = "배터리/EV → 원자재(리튬, 니켈) 가격과 완성차 업체 판매량이 핵심 변수."
    elif any(kw in text for kw in ["방산", "defense", "무기", "전쟁", "war"]):
        result["forward_prediction"] = "방산/지정학 → 분쟁 지속 시 방산주 수혜 지속. 평화 협상 진전 시 차익실현 압력."
    else:
        if direction == "positive":
            result["forward_prediction"] = "호재 요인이 지속 가능한지, 일회성인지 확인 필요. 지속적이면 추가 상승 여력."
        elif direction == "negative":
            result["forward_prediction"] = "악재의 일회성 여부 확인 필요. 구조적 문제라면 중장기 하락 압력."
        else:
            result["forward_prediction"] = "방향성 확인을 위해 후속 뉴스와 시장 반응 모니터링 필요."

    return result


def _build_deep_news_item(news: dict, ticker: str, info: dict | None, company_name: str) -> dict:
    """Build a deeply analyzed news item with meaning, prediction, and priced-in assessment."""
    title = news.get("title", "")
    direction = news.get("impact_direction", "neutral")
    category = news.get("issue_label", "뉴스")
    explanation = news.get("explanation", "")

    # Check if English — build Korean interpretation
    is_english = all(ord(c) < 0x1100 or ord(c) > 0xD7AF for c in title.replace(" ", "")[:20]) if title else False
    if is_english:
        ko_summary = _summarize_english_title(title, company_name)
        if ko_summary:
            # Replace generic explanation with specific Korean interpretation
            explanation = f"[기사 해석] {ko_summary}. {explanation}"
        else:
            # At minimum, note it's English and provide category context
            explanation = f"[영문 기사] {title[:80]}... — {explanation}"

    # Assess priced-in level
    priced_in = _assess_priced_in(title, ticker, info, direction)

    # Build actionable takeaway — specific to category
    if direction == "positive":
        if "실적" in category:
            action_label = "실적 호조 — 매수 관점"
            action_detail = f"{company_name}의 실적 호조가 확인됨. 컨센서스 대비 서프라이즈 폭에 따라 추가 상승 여력 판단. 선반영 여부 확인 후 분할매수 검토."
        elif "수주" in category or "계약" in category:
            action_label = "신규 수주 — 매수 관점"
            action_detail = f"신규 수주·계약은 {company_name}의 매출 가시성을 높이는 핵심 이벤트. 수주 규모와 기간을 확인하고 밸류에이션 재평가."
        elif "애널리스트" in category or "목표가" in category:
            action_label = "투자의견 개선 — 긍정적"
            action_detail = f"애널리스트 의견 개선은 기관 자금 유입의 선행 신호. 목표주가와 현재가 괴리율 확인 후 대응."
        else:
            action_label = "호재 — 매수 검토"
            action_detail = f"긍정적 뉴스 확인. 선반영 정도와 후속 모멘텀 가능성을 종합해 진입 시점 판단."
    elif direction == "negative":
        if "실적" in category:
            action_label = "실적 부진 — 리스크 관리"
            action_detail = f"{company_name} 실적이 기대에 미치지 못함. 일시적 부진인지 구조적 둔화인지 판단 필요. 보유 중이면 비중 축소 고려."
        elif "규제" in category or "법적" in category:
            action_label = "규제 리스크 — 주의"
            action_detail = f"규제·법적 이슈는 불확실성을 키워 주가를 장기간 압박할 수 있음. 과징금 규모와 사업 영향도 파악 필요."
        elif "지정학" in category:
            action_label = "지정학 리스크 — 방어적 접근"
            action_detail = f"지정학적 불안은 시장 전체 위험회피 심리를 자극. {company_name}의 직접 영향 범위(수출비중, 원자재 비용 등) 점검."
        else:
            action_label = "악재 — 비중 조절"
            action_detail = f"부정적 뉴스 확인. 보유 중이면 손절/비중축소 검토, 미보유 시 저가매수 기회인지 구조적 악재인지 판단 필요."
    else:
        action_label = "중립 — 모니터링"
        action_detail = f"방향성이 불분명한 뉴스. 후속 발표나 시장 반응을 관찰한 후 포지션 결정."

    return {
        "title": title,
        "source": news.get("source", ""),
        "published_at": news.get("published_at", ""),
        "url": news.get("url", ""),
        "category": category,
        "direction": direction,
        "explanation": explanation,
        "priced_in_level": priced_in["priced_in_level"],
        "priced_in_reason": priced_in["priced_in_reason"],
        "forward_prediction": priced_in["forward_prediction"],
        "action_label": action_label,
        "action_detail": action_detail,
        "relevance_score": news.get("impact_score", 0),
    }


@router.get("/analysis/{ticker}/news-analysis")
def get_news_analysis(ticker: str) -> dict:
    """
    Deep news analysis endpoint.

    For each news article:
    - 무슨 의미인지 (what does this mean for the stock?)
    - 선반영 여부 (is this already priced in?)
    - 향후 예측 (what can we predict from this?)
    - 어떤 액션을 취할지 (what should the investor do?)

    Fast response (~2-5s) — runs independently of the slow checklist.
    """
    cache_key = f"news-analysis:{_ticker_key(ticker)}"
    cached = _get_best_cached(cache_key, 300)
    if cached is not None:
        return cached

    info = None
    sector_id = None
    company_name = ticker
    try:
        info = get_yf_info(ticker)
        sector_id = _infer_sector_id_from_profile(ticker, info)
        company_name = str(info.get("shortName") or info.get("longName") or ticker).strip()
    except Exception:
        pass
    if not sector_id:
        sector_id = TOP_PICK_SECTOR_MAP.get(_ticker_key(ticker))

    # Fast: news crawling + sentiment classification
    live_news = _extract_live_impact_news(ticker, info=info, sector_id=sector_id)
    news_drivers = _extract_news_drivers(ticker, info=info, sector_id=sector_id)

    # Deep analysis for each news item
    deep_articles = []
    for news in live_news[:8]:
        deep = _build_deep_news_item(news, ticker, info, company_name)
        deep_articles.append(deep)

    # Build momentum notes from deep analysis
    momentum_notes = []
    seen_cats = set()
    for article in deep_articles[:5]:
        cat = article["category"]
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        direction = article["direction"]
        lead = "긍정 선행" if direction == "positive" else ("부정 선행" if direction == "negative" else "중립")
        momentum_notes.append({
            "title": cat,
            "lead": lead,
            "detail": article["explanation"],
            "why_it_matters": article["forward_prediction"],
            "expected_condition": article["priced_in_reason"],
            "window": "향후 1~3개월",
            "status": direction,
            "importance": 75,
        })

    # Sentiment summary
    pos_count = sum(1 for a in deep_articles if a["direction"] == "positive")
    neg_count = sum(1 for a in deep_articles if a["direction"] == "negative")
    total = len(deep_articles)

    # Overall market view for this stock
    if pos_count > neg_count * 2:
        overall_view = "매우 긍정적"
        overall_detail = f"최근 뉴스 {total}건 중 호재 {pos_count}건으로 긍정적 흐름. 시장 기대감 상승 중."
    elif pos_count > neg_count:
        overall_view = "긍정적"
        overall_detail = f"호재가 우세한 뉴스 흐름. 다만 악재({neg_count}건)도 모니터링 필요."
    elif neg_count > pos_count * 2:
        overall_view = "매우 부정적"
        overall_detail = f"악재 {neg_count}건이 다수. 보수적 접근 필요."
    elif neg_count > pos_count:
        overall_view = "부정적"
        overall_detail = f"악재가 우세. 리스크 관리 강화 권장."
    else:
        overall_view = "중립"
        overall_detail = f"호재와 악재가 혼재. 방향성 확인을 위해 후속 뉴스 주시 필요."

    # Key upcoming catalysts (from news drivers)
    catalysts = []
    for driver in news_drivers[:3]:
        catalysts.append({
            "name": driver.get("name", ""),
            "article_count": driver.get("count", 0),
            "headlines": driver.get("headlines", [])[:2],
            "why_it_matters": driver.get("why_it_matters", ""),
        })

    result = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "deep_articles": deep_articles,
        "live_impact_news": live_news,  # backward compat
        "news_drivers": catalysts,
        "momentum_notes": momentum_notes,
        "overall_news_view": overall_view,
        "overall_news_detail": overall_detail,
        "sentiment_summary": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": total - pos_count - neg_count,
            "total": total,
        },
    }

    _set_cached(cache_key, result)
    _save_disk_cached(cache_key, result)
    return result
