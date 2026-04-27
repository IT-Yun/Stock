"""Fast macro/geopolitical issue scanner.

Uses public Google News RSS queries as a low-friction breaking-news feed.
The output is intentionally impact-oriented: issue -> evidence articles -> sector effects.
"""
from __future__ import annotations

import email.utils
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any


_CACHE: tuple[float, list[dict[str, Any]]] | None = None
_TTL = 600

ISSUE_QUERIES: list[dict[str, Any]] = [
    {
        "id": "iran_hormuz",
        "title": "이란·호르무즈·중동 에너지 리스크",
        "query": "Iran Hormuz oil tanker Reuters OR AP when:1d",
        "keywords": ["iran", "hormuz", "oil", "tanker", "strait"],
        "favorable": ["aerospace", "shipbuilding", "smr_nuclear", "hydrogen_energy", "cybersec"],
        "unfavorable": ["hotel_leisure", "ev", "battery", "food"],
        "impact": "원유/운송로 차질은 방산·조선·에너지 안보에는 우호, 항공·여행·소비재 비용에는 부담.",
    },
    {
        "id": "fed_rates",
        "title": "미국 금리 경로·인하/인상 기대",
        "query": "Federal Reserve rate cut hike Treasury yields Reuters OR CNBC when:1d",
        "keywords": ["federal reserve", "rate", "treasury", "yield", "inflation"],
        "favorable": ["finance", "telecom"],
        "unfavorable": ["platform", "gaming", "ev", "battery", "holding_reit", "construction"],
        "impact": "금리 고착/상승은 성장주·부동산·EV에 부담, 은행 NIM에는 조건부 우호.",
    },
    {
        "id": "us_china_controls",
        "title": "미중 갈등·수출통제·관세",
        "query": "US China export controls tariffs chips rare earth Reuters when:1d",
        "keywords": ["china", "export controls", "tariff", "chips", "rare earth"],
        "favorable": ["cybersec", "aerospace", "ai_semi", "ev_materials"],
        "unfavorable": ["display", "cosmetics", "retail", "k_content"],
        "impact": "수출통제와 공급망 재편은 보안·방산·국산화에는 우호, 중국 노출 소비재/디스플레이에는 부담.",
    },
    {
        "id": "ai_power",
        "title": "AI 데이터센터 전력 병목",
        "query": "AI data center power shortage grid nuclear Reuters when:2d",
        "keywords": ["ai", "data center", "power", "grid", "nuclear"],
        "favorable": ["ai_semi", "smr_nuclear", "hydrogen_energy", "robotics"],
        "unfavorable": ["telecom", "holding_reit"],
        "impact": "AI capex가 전력망·원전·전력기기 수요로 전이. 전력비 부담 업종은 압박.",
    },
    {
        "id": "oil_opec",
        "title": "OPEC·원유 공급·재고",
        "query": "OPEC oil supply inventory crude Reuters EIA when:1d",
        "keywords": ["opec", "oil", "crude", "inventory", "supply"],
        "favorable": ["shipbuilding", "hydrogen_energy"],
        "unfavorable": ["hotel_leisure", "food"],
        "impact": "원유 공급 타이트닝은 에너지/운송 관련에는 우호, 항공유·물류·식품 원가에는 부담.",
    },
    {
        "id": "korea_exports_fx",
        "title": "한국 수출·환율·반도체 사이클",
        "query": "South Korea exports semiconductor won dollar Reuters when:2d",
        "keywords": ["korea", "exports", "semiconductor", "won", "dollar"],
        "favorable": ["ai_semi", "shipbuilding", "aerospace"],
        "unfavorable": ["food", "retail", "hotel_leisure"],
        "impact": "수출/환율은 반도체·조선 환산 매출에는 우호, 수입원가 업종에는 부담.",
    },
]


def _fetch_rss(query: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    out: list[dict[str, Any]] = []
    for item in root.findall("./channel/item")[:6]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        source = item.findtext("source") or "Google News"
        published = item.findtext("pubDate") or ""
        dt = None
        if published:
            try:
                dt = email.utils.parsedate_to_datetime(published)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
        out.append({
            "title": title,
            "url": link,
            "source": source,
            "published_at": dt.isoformat() if dt else published,
        })
    return out


def _score_articles(issue: dict[str, Any], articles: list[dict[str, Any]]) -> float:
    text = " ".join(a.get("title", "") for a in articles).lower()
    hits = sum(1 for k in issue["keywords"] if k.lower() in text)
    recency = 0.0
    now = datetime.now(timezone.utc)
    for a in articles[:3]:
        try:
            dt = datetime.fromisoformat((a.get("published_at") or "").replace("Z", "+00:00"))
            hours = max(0.0, (now - dt).total_seconds() / 3600)
            recency += max(0.0, 1.0 - hours / 36.0)
        except Exception:
            pass
    return round(min(1.0, hits / 4.0 + recency / 6.0), 2)


def scan_macro_news(force: bool = False) -> list[dict[str, Any]]:
    global _CACHE
    now = time.time()
    if not force and _CACHE and now - _CACHE[0] < _TTL:
        return _CACHE[1]

    issues: list[dict[str, Any]] = []
    for issue in ISSUE_QUERIES:
        try:
            articles = _fetch_rss(issue["query"])
        except Exception as e:
            articles = []
            error = str(e)[:120]
        else:
            error = None
        score = _score_articles(issue, articles)
        issues.append({
            "id": issue["id"],
            "title": issue["title"],
            "urgency": score,
            "impact": issue["impact"],
            "favorable_sectors": issue["favorable"],
            "unfavorable_sectors": issue["unfavorable"],
            "articles": articles,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    issues.sort(key=lambda x: (x["urgency"], len(x["articles"])), reverse=True)
    _CACHE = (now, issues)
    return issues
