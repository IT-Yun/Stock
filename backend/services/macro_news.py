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
        "macro_paths": [
            "긴장 고조/유가 상승: 방산 발주, 탱커·LNG선 운임, 에너지 안보 투자가 살아나고 항공·여행·소비재는 연료비와 물류비가 먼저 오른다.",
            "긴장 완화/유가 하락: 항공·여행, 음식료, EV·배터리는 원가 부담이 줄고 방산·에너지 안보 프리미엄은 약해진다.",
        ],
        "favorable_details": {
            "aerospace": "지정학 긴장이 커지면 미사일·탄약·방공체계 예산과 수출 문의가 늘어 방산/항공우주 수주 기대가 커진다.",
            "shipbuilding": "호르무즈 리스크는 탱커·LNG선 운임과 에너지 운송선 발주 기대를 키워 조선에 유리하다.",
            "smr_nuclear": "에너지 안보 논리가 강해지면 원전·SMR 같은 안정 전원 투자 명분이 커진다.",
            "hydrogen_energy": "화석연료 공급 불안은 대체 에너지와 전력 인프라 투자 필요성을 높인다.",
            "cybersec": "분쟁 국면에서는 국가·기업 대상 사이버 공격 위험이 커져 보안 예산이 방어적으로 유지된다.",
        },
        "unfavorable_details": {
            "hotel_leisure": "항공유와 여행 비용이 올라 항공사 마진, 여행 수요, 레저 소비가 동시에 눌릴 수 있다.",
            "ev": "고유가 자체는 EV 수요에 중립 이상일 수 있지만 리스크오프와 금리 상승이 동반되면 고가 내구재 수요가 약해진다.",
            "battery": "유가·물류비와 위험회피가 커지면 배터리 소재 운송비와 성장주 할인율 부담이 커진다.",
            "food": "곡물·운송·포장재 비용이 올라 판가 전가 전까지 음식료 마진이 압박받는다.",
        },
    },
    {
        "id": "fed_rates",
        "title": "미국 금리 경로·인하/인상 기대",
        "query": "Federal Reserve rate cut hike Treasury yields Reuters OR CNBC when:1d",
        "keywords": ["federal reserve", "rate", "treasury", "yield", "inflation"],
        "favorable": ["finance", "telecom"],
        "unfavorable": ["platform", "gaming", "ev", "battery", "holding_reit", "construction"],
        "impact": "금리 고착/상승은 성장주·부동산·EV에 부담, 은행 NIM에는 조건부 우호.",
        "macro_paths": [
            "금리 인상/고금리 장기화: 은행은 NIM이 버틸 수 있지만 성장주, EV, 배터리, 게임, 플랫폼, 리츠, 건설은 할인율과 조달비용 부담이 커진다.",
            "금리 인하/금리 하락: 플랫폼·게임·EV·배터리·리츠·건설처럼 장기 성장과 부채 민감도가 큰 섹터가 먼저 회복하고 은행 NIM은 둔화될 수 있다.",
        ],
        "favorable_details": {
            "finance": "금리 상승 초기에는 대출금리가 예금금리보다 빨리 반영돼 NIM에 유리하다. 다만 연체율이 오르면 호재가 약해진다.",
            "telecom": "통신은 경기 민감도가 낮고 현금흐름이 안정적이라 고금리·방어주 선호 국면에서 상대적으로 버틴다.",
        },
        "unfavorable_details": {
            "platform": "금리가 오르면 미래 이익의 현재가치가 낮아져 광고·커머스 성장주 멀티플이 압박받는다.",
            "gaming": "게임은 신작 기대와 장기 현금흐름을 선반영하는 섹터라 할인율 상승에 약하다.",
            "ev": "차량 할부금리 상승은 전기차 구매 부담을 키우고 OEM 인센티브 확대 압력으로 이어질 수 있다.",
            "battery": "배터리는 증설 CAPEX와 운전자본 부담이 커 금리 상승 시 밸류에이션과 재무비용이 동시에 눌린다.",
            "holding_reit": "리츠와 지주사는 배당수익률 매력이 금리와 경쟁하고 차환 비용도 올라 NAV 할인폭이 커질 수 있다.",
            "construction": "주택 수요, PF 조달, 미분양 리스크가 모두 금리에 민감해 고금리에서는 건설/건자재가 부담을 받는다.",
        },
    },
    {
        "id": "us_china_controls",
        "title": "미중 갈등·수출통제·관세",
        "query": "US China export controls tariffs chips rare earth Reuters when:1d",
        "keywords": ["china", "export controls", "tariff", "chips", "rare earth"],
        "favorable": ["cybersec", "aerospace", "ai_semi", "ev_materials"],
        "unfavorable": ["display", "cosmetics", "retail", "k_content"],
        "impact": "수출통제와 공급망 재편은 보안·방산·국산화에는 우호, 중국 노출 소비재/디스플레이에는 부담.",
        "macro_paths": [
            "갈등 확대/관세 강화: 사이버보안, 방산, 반도체 국산화, EV 소재 탈중국 밸류체인은 좋아지고 중국 매출 비중이 큰 소비재·콘텐츠·디스플레이는 부담이다.",
            "갈등 완화/관세 완화: 중국 소비 노출 섹터와 디스플레이 수요에는 숨통이 트이고, 국산화·방산 프리미엄은 일부 되돌림이 나올 수 있다.",
        ],
        "favorable_details": {
            "cybersec": "국가 간 갈등은 해킹·정보보안 투자 필요성을 높여 보안 업체의 예산 방어력을 키운다.",
            "aerospace": "수출통제와 군비 경쟁은 방산 수주와 항공우주 공급망 내재화 투자를 자극한다.",
            "ai_semi": "첨단 반도체 통제는 국내 장비·소재·패키징 국산화와 비중국 공급망 수요를 키울 수 있다.",
            "ev_materials": "배터리 소재 탈중국과 FEOC 회피 수요가 커지면 한국 소재/부품 업체에 기회가 생긴다.",
        },
        "unfavorable_details": {
            "display": "중국 패널 업체와 최종 수요가 흔들리면 패널 가격과 출하 회복이 늦어진다.",
            "cosmetics": "중국 소비 심리와 통관/규제 리스크가 커지면 화장품 수출과 면세 채널이 눌릴 수 있다.",
            "retail": "관세와 물류비 상승은 소비재 매입원가를 높이고 실질소비를 둔화시킨다.",
            "k_content": "한한령·플랫폼 규제 같은 비가격 장벽이 커지면 콘텐츠 판매와 공연/팬덤 수익이 제한된다.",
        },
    },
    {
        "id": "ai_power",
        "title": "AI 데이터센터 전력 병목",
        "query": "AI data center power shortage grid nuclear Reuters when:2d",
        "keywords": ["ai", "data center", "power", "grid", "nuclear"],
        "favorable": ["ai_semi", "smr_nuclear", "hydrogen_energy", "robotics"],
        "unfavorable": ["telecom", "holding_reit"],
        "impact": "AI capex가 전력망·원전·전력기기 수요로 전이. 전력비 부담 업종은 압박.",
        "macro_paths": [
            "전력 병목 심화: AI 반도체 수요는 유지되면서 원전·전력기기·전력망·자동화 투자가 같이 좋아진다. 전력비 민감 업종은 마진 부담이 커진다.",
            "전력 병목 완화: 데이터센터 증설 속도는 안정되지만 전력 인프라 프리미엄은 낮아질 수 있다.",
        ],
        "favorable_details": {
            "ai_semi": "전력 제약에도 AI 투자 의지가 유지되면 고효율 GPU, HBM, 전력반도체 수요가 강하게 남는다.",
            "smr_nuclear": "데이터센터가 24시간 무탄소 전력을 원하면 원전/SMR PPA와 기자재 수요가 부각된다.",
            "hydrogen_energy": "전력망 병목은 장기 저장, 분산 전원, 전해조 같은 대체 전력 솔루션 관심을 높인다.",
            "robotics": "데이터센터·전력설비 증설은 자동화 장비, 검사, 설비투자 수요로 이어질 수 있다.",
        },
        "unfavorable_details": {
            "telecom": "기지국·IDC 전력비가 올라 통신사의 비용 부담이 커지고 요금 전가도 제한적이다.",
            "holding_reit": "전력 확보 비용과 차환비용이 동시에 커지면 데이터센터/리츠의 cap rate와 NAV가 압박받는다.",
        },
    },
    {
        "id": "oil_opec",
        "title": "OPEC·원유 공급·재고",
        "query": "OPEC oil supply inventory crude Reuters EIA when:1d",
        "keywords": ["opec", "oil", "crude", "inventory", "supply"],
        "favorable": ["shipbuilding", "hydrogen_energy"],
        "unfavorable": ["hotel_leisure", "food"],
        "impact": "원유 공급 타이트닝은 에너지/운송 관련에는 우호, 항공유·물류·식품 원가에는 부담.",
        "macro_paths": [
            "유가 상승/재고 감소: 조선·에너지 설비는 운송/개발 수요가 좋아지고 항공·여행·음식료는 연료비와 물류비 부담이 커진다.",
            "유가 하락/재고 증가: 항공·여행·음식료 원가는 완화되고 에너지 운송·개발 투자 기대는 낮아진다.",
        ],
        "favorable_details": {
            "shipbuilding": "유가가 높으면 해양플랜트, 탱커, LNG 운송 수요가 살아나 조선 수주 기대에 도움이 된다.",
            "hydrogen_energy": "화석연료 가격이 높아지면 대체 에너지와 효율화 투자 경제성이 상대적으로 좋아진다.",
        },
        "unfavorable_details": {
            "hotel_leisure": "항공유가 오르면 항공사 비용과 여행 가격이 올라 레저 수요가 둔화될 수 있다.",
            "food": "원유 상승은 포장재, 운송, 농산물 생산비를 밀어 올려 음식료 마진을 압박한다.",
        },
    },
    {
        "id": "korea_exports_fx",
        "title": "한국 수출·환율·반도체 사이클",
        "query": "South Korea exports semiconductor won dollar Reuters when:2d",
        "keywords": ["korea", "exports", "semiconductor", "won", "dollar"],
        "favorable": ["ai_semi", "shipbuilding", "aerospace"],
        "unfavorable": ["food", "retail", "hotel_leisure"],
        "impact": "수출/환율은 반도체·조선 환산 매출에는 우호, 수입원가 업종에는 부담.",
        "macro_paths": [
            "원화 약세/수출 호조: 반도체·조선·방산은 달러 매출 환산과 가격 경쟁력이 좋아지고 수입 원가 업종은 부담이 커진다.",
            "원화 강세/수출 둔화: 음식료·유통·여행은 수입원가와 해외여행 비용 부담이 줄지만 수출주는 환산 매출 모멘텀이 약해진다.",
        ],
        "favorable_details": {
            "ai_semi": "반도체 수출 증가와 원화 약세가 겹치면 달러 매출 환산 효과와 업황 회복 신호가 같이 나타난다.",
            "shipbuilding": "조선은 달러 수주 비중이 높아 원화 약세 시 매출 환산과 수주 채산성이 좋아질 수 있다.",
            "aerospace": "방산 수출 계약은 달러 기반이 많아 원화 약세가 수익성에 유리하게 작용할 수 있다.",
        },
        "unfavorable_details": {
            "food": "곡물·원재료 수입 비중이 커 원화 약세 때 투입 원가가 먼저 오른다.",
            "retail": "수입 상품 매입가가 올라 소비자 가격 부담과 마진 압박이 커질 수 있다.",
            "hotel_leisure": "원화 약세는 해외여행 비용과 항공 관련 비용을 높여 여행 수요를 둔화시킬 수 있다.",
        },
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
            "macro_paths": issue.get("macro_paths", []),
            "favorable_sectors": issue["favorable"],
            "unfavorable_sectors": issue["unfavorable"],
            "sector_effects": _sector_effects(issue),
            "articles": articles,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    issues.sort(key=lambda x: (x["urgency"], len(x["articles"])), reverse=True)
    _CACHE = (now, issues)
    return issues


def _sector_effects(issue: dict[str, Any]) -> list[dict[str, str]]:
    effects: list[dict[str, str]] = []
    favorable_details = issue.get("favorable_details", {})
    unfavorable_details = issue.get("unfavorable_details", {})
    for sid in issue.get("favorable", []):
        effects.append({
            "sector_id": sid,
            "direction": "favorable",
            "reason": favorable_details.get(sid, "해당 거시 이벤트가 수요, 가격, 정책 모멘텀에 긍정적으로 작용한다."),
        })
    for sid in issue.get("unfavorable", []):
        effects.append({
            "sector_id": sid,
            "direction": "unfavorable",
            "reason": unfavorable_details.get(sid, "해당 거시 이벤트가 비용, 할인율, 수요 둔화 압력으로 작용한다."),
        })
    return effects
