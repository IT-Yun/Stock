"""Sector indicator watchlists and conservative live sentiment.

This module intentionally avoids broad "commodity moved, therefore sector bullish"
shortcuts. Commodity moves are only used when the causal link is direct enough
to be useful as a cost or demand proxy. The main output is a sector-specific
watchlist of indicators that should be checked before forming a view.
"""

from __future__ import annotations
from typing import Any
from services.macro_commodity import fetch_feed


CORE_WATCH_SIGNALS: dict[str, list[str]] = {
    "ai_semi": [
        "HBM/DRAM spot·contract price trend",
        "MOTIE Korea semiconductor export YoY/MoM",
        "ASML bookings + TSMC monthly revenue",
        "Hyperscaler AI CAPEX guidance (MSFT/AMZN/GOOGL/META)",
    ],
    "robotics": [
        "Japan robot orders / Fanuc·Yaskawa orders",
        "Korea factory automation CAPEX and smart-factory budget",
        "Collaborative robot shipment growth",
    ],
    "smr_nuclear": [
        "Uranium U3O8 spot + term price",
        "Data-center power PPA / PJM interconnection queue",
        "Nuclear policy approvals and SMR order backlog",
    ],
    "cybersec": [
        "CISA KEV additions and severity mix",
        "Enterprise security budget / billings growth",
        "ARR growth, NRR, rule-of-40 for CRWD/PANW/ZS/S",
    ],
    "aerospace": [
        "Defense budget supplemental orders",
        "Missile/munition backlog and book-to-bill",
        "Space launch cadence and satellite order backlog",
    ],
    "biotech": [
        "FDA/PDUFA calendar and clinical readout dates",
        "Prescription data / trial enrollment pace",
        "Cash runway and dilution risk",
    ],
    "quantum": [
        "Government quantum program funding",
        "Quantum hardware milestone / error-rate progress",
        "Backlog, bookings, cash runway for pure-play names",
    ],
    "hydrogen_energy": [
        "Hydrogen project FID / electrolyzer order backlog",
        "Iridium/platinum catalyst cost",
        "Policy subsidy and power price spread",
    ],
    "battery": [
        "Lithium carbonate/hydroxide spot price",
        "Cathode/anode inventory days and utilization",
        "EV battery shipment and ESS order growth",
    ],
    "ev": [
        "Monthly deliveries and inventory days",
        "ASP/incentive trend and margin guidance",
        "Battery cost per kWh and charging utilization",
    ],
    "ev_materials": [
        "Cathode precursor spread",
        "Lithium/nickel/cobalt input cost",
        "Customer utilization and long-term supply contracts",
    ],
    "shipbuilding": [
        "Clarksons newbuilding price index",
        "LNG carrier/container/tanker order flow",
        "Steel plate price and FX sensitivity",
    ],
    "steel": [
        "China steel PMI / rebar and HRC spread",
        "Iron ore/coking coal input cost",
        "Korea auto/shipbuilding demand",
    ],
    "display": [
        "Panel price trend by size",
        "OLED utilization and TV/mobile sell-through",
        "China panel maker capacity discipline",
    ],
    "platform": [
        "Ad spend growth and e-commerce GMV",
        "Cloud/AI monetization revenue",
        "Take-rate and regulatory risk",
    ],
    "gaming": [
        "SteamDB / mobile app rank / CCU",
        "New title launch calendar and retention",
        "ARPU and marketing spend efficiency",
    ],
    "k_content": [
        "Album sales, streaming, concert attendance",
        "OTT commissioning and content export data",
        "Artist comeback/tour calendar",
    ],
    "cosmetics": [
        "China/US/Japan export data by HS code",
        "Duty-free and Olive Young sell-through",
        "Amazon/TikTok ranking momentum",
    ],
    "food": [
        "Grain/sugar/coffee input cost",
        "Price hike pass-through and gross margin",
        "Export volume for ramen/snacks/beverages",
    ],
    "retail": [
        "Consumer confidence and card spending",
        "Online GMV and logistics cost",
        "Same-store sales and inventory turnover",
    ],
    "apparel": [
        "Cotton/polyester input cost",
        "Inventory days and discount rate",
        "US/China retail sell-through",
    ],
    "construction": [
        "Housing starts/permits and unsold inventory",
        "Cement/rebar cost and PF credit spread",
        "SOC budget and order backlog",
    ],
    "finance": [
        "Yield curve and NIM direction",
        "Credit cost / delinquency rate",
        "Shareholder return policy and capital ratio",
    ],
    "telecom": [
        "ARPU, 5G subscriber mix, churn",
        "CAPEX intensity and spectrum cost",
        "Power cost for utilities",
    ],
    "holding_reit": [
        "Discount to NAV and dividend yield spread",
        "Interest rate / refinancing spread",
        "Asset disposal or buyback catalyst",
    ],
    "medical_device": [
        "FDA/KFDA approvals and installed base",
        "Consumable repeat revenue growth",
        "Procedure volume and clinic CAPEX",
    ],
    "hotel_leisure": [
        "Inbound tourist arrivals and airline capacity",
        "RevPAR / occupancy / ADR",
        "Oil price and FX impact on travel demand",
    ],
}


# Conservative commodity links only. These are direct cost inputs or accepted
# demand proxies, not broad sector calls.
DIRECT_COMMODITY_RULES: dict[str, list[tuple[str, str, str]]] = {
    "battery": [("lithium_lit", "bearish_on_surge", "리튬 ETF 급등 -> 배터리 소재 원가 부담")],
    "ev_materials": [("lithium_lit", "bearish_on_surge", "리튬 ETF 급등 -> 양극재/소재 마진 부담")],
    "food": [
        ("corn", "bearish_on_surge", "옥수수 급등 -> 원가 부담"),
        ("soybean", "bearish_on_surge", "대두 급등 -> 원가 부담"),
        ("wheat", "bearish_on_surge", "밀 급등 -> 원가 부담"),
        ("sugar", "bearish_on_surge", "설탕 급등 -> 원가 부담"),
        ("coffee", "bearish_on_surge", "커피 급등 -> 원가 부담"),
    ],
    "apparel": [("cotton", "bearish_on_surge", "면화 급등 -> 원단 원가 부담")],
    "construction": [("copper", "bearish_on_surge", "구리 급등 -> 전선/설비 원가 부담")],
    "hydrogen_energy": [
        ("platinum", "bearish_on_surge", "백금 급등 -> 촉매 원가 부담"),
        ("palladium", "bearish_on_surge", "팔라듐 급등 -> 촉매/부품 원가 부담"),
    ],
    "shipbuilding": [
        ("crude_wti", "bullish_on_surge", "유가 급등 -> 탱커/LNG선 발주 기대 확인"),
        ("crude_brent", "bullish_on_surge", "Brent 급등 -> 해양플랜트/탱커 수요 proxy"),
    ],
    "hotel_leisure": [("crude_wti", "bearish_on_surge", "유가 급등 -> 항공/여행 비용 부담")],
}

FORWARD_SECTOR_RULES: dict[str, dict[str, Any]] = {
    "ai_semi": {
        "takeaway": "AI capex가 유지될 때 HBM·전력·네트워크 chain이 가장 먼저 확인돼야 한다.",
        "positive": [
            ("copper", "uptrend", "구리 상승/견조 -> 데이터센터 전력망·케이블 capex proxy"),
            ("aluminum", "uptrend", "알루미늄 견조 -> 전력기기·서버/냉각 설비 소재 수요 proxy"),
            ("silver", "uptrend", "은 상승 -> 태양광·전장·반도체 소재 수요 proxy"),
        ],
        "negative": [
            ("gallium", "surge", "갈륨 급등 -> GaN/RF/전력반도체 소재 병목"),
            ("germanium", "surge", "게르마늄 급등 -> 광통신/방산 소재 병목"),
        ],
        "next": ["HBM/DRAM 가격", "TSMC 월매출", "ASML 수주", "빅테크 capex 가이던스"],
    },
    "smr_nuclear": {
        "takeaway": "AI 전력 병목과 에너지 안보가 동시에 커질수록 원전/SMR 옵션 가치가 커진다.",
        "positive": [
            ("uranium_u3o8", "uptrend", "우라늄 상승/견조 -> 원전 연료·SMR 관심 proxy"),
            ("crude_brent", "uptrend", "유가 강세 -> 에너지 안보/대체 전원 수요"),
            ("copper", "uptrend", "구리 견조 -> 송전망 병목 투자 proxy"),
        ],
        "negative": [],
        "next": ["U3O8 spot/term", "PPA 계약", "원전 인허가", "PJM interconnection queue"],
    },
    "aerospace": {
        "takeaway": "전쟁·수출통제·방산 예산이 가격보다 중요하고 티타늄/희토류는 비용 병목이다.",
        "positive": [
            ("crude_brent", "surge", "유가 급등 -> 중동 지정학/방산 예산 기대"),
            ("titanium", "uptrend", "티타늄 견조 -> 항공·방산 소재 수요 proxy"),
            ("neodymium", "uptrend", "희토류 견조 -> 미사일/모터/방산 공급망 proxy"),
        ],
        "negative": [("titanium", "surge", "티타늄 급등 -> 항공기/미사일 원가 부담")],
        "next": ["국방예산", "미사일/탄약 book-to-bill", "항공기 인도량", "티타늄 공급 뉴스"],
    },
    "shipbuilding": {
        "takeaway": "유가·LNG 운송 수요는 호재지만 후판/HRC 급등은 마진을 깎는다.",
        "positive": [
            ("crude_brent", "uptrend", "Brent 강세 -> LNG선·탱커·해양플랜트 수요 proxy"),
            ("natgas_henry_hub", "surge", "가스 급등 -> LNG 운송/저장 수요 기대"),
        ],
        "negative": [("hrc_steel", "surge", "HRC 급등 -> 후판 원가 부담")],
        "next": ["Clarksons 신조선가", "LNG선 발주", "후판 가격", "원/달러"],
    },
    "battery": {
        "takeaway": "리튬·니켈 급락은 원가 완화지만 수요 부진 신호일 수도 있어 재고 소진을 확인해야 한다.",
        "positive": [
            ("lithium_carbonate", "plunge", "리튬 급락 -> 셀/양극재 원가 부담 완화"),
            ("nickel_lme", "plunge", "니켈 급락 -> 원가 부담 완화"),
        ],
        "negative": [
            ("lithium_carbonate", "surge", "리튬 급등 -> 판가 전가 전까지 마진 부담"),
            ("natural_graphite", "surge", "흑연 급등 -> 음극재/중국 통제 리스크"),
        ],
        "next": ["중국 리튬 재고", "ESS 수주", "EV 판매/재고일수", "양극재 가동률"],
    },
    "ev_materials": {
        "takeaway": "핵심은 원료 가격보다 고객사 가동률·스프레드다.",
        "positive": [
            ("lithium_carbonate", "plunge", "리튬 급락 -> 소재 원가 완화"),
            ("natural_graphite", "uptrend", "흑연 견조 -> 음극재/공급망 국산화 관심"),
        ],
        "negative": [
            ("lithium_carbonate", "surge", "리튬 급등 -> 양극재 원가/운전자본 부담"),
            ("nickel_lme", "surge", "니켈 급등 -> 고니켈 양극재 원가 부담"),
        ],
        "next": ["전구체 spread", "고객사 가동률", "장기공급계약", "중국 덤핑 여부"],
    },
    "food": {
        "takeaway": "곡물·설탕·커피가 오르면 판가 전가 전까지 마진이 먼저 눌린다.",
        "positive": [],
        "negative": [
            ("corn", "uptrend", "옥수수 상승 -> 원가 부담"),
            ("wheat", "uptrend", "밀 상승 -> 원가 부담"),
            ("coffee", "uptrend", "커피 상승 -> 원가 부담"),
            ("sugar", "uptrend", "설탕 상승 -> 원가 부담"),
        ],
        "next": ["USDA WASDE", "작황/날씨", "판가 인상", "재고 평가손익"],
    },
    "hotel_leisure": {
        "takeaway": "유가·환율이 비용과 여행 수요를 동시에 압박한다.",
        "positive": [],
        "negative": [
            ("crude_wti", "uptrend", "유가 강세 -> 항공유/여행 비용 부담"),
            ("crude_brent", "uptrend", "Brent 강세 -> 항공/여행 비용 부담"),
        ],
        "next": ["항공유 crack", "환율", "입국자 수", "RevPAR"],
    },
    "steel": {
        "takeaway": "철광석/HRC는 중국 경기와 조선·인프라 수요를 같이 봐야 한다.",
        "positive": [("hrc_steel", "uptrend", "HRC 견조 -> 철강 가격/스프레드 확인")],
        "negative": [("iron_ore", "surge", "철광석 급등 -> 원가 부담")],
        "next": ["중국 steel PMI", "rebar/HRC spread", "조선 후판 협상", "철광석 재고"],
    },
    "construction": {
        "takeaway": "금리와 PF 신용이 1순위, 구리/철근은 비용 확인 지표다.",
        "positive": [],
        "negative": [
            ("copper", "uptrend", "구리 강세 -> 전선/설비 원가 부담"),
            ("hrc_steel", "uptrend", "철강 강세 -> 건자재 비용 부담"),
        ],
        "next": ["PF 스프레드", "미분양", "착공/인허가", "시멘트/철근 가격"],
    },
}


def _commodity_signal(item: dict[str, Any], rule: str, label: str) -> tuple[str, str] | None:
    is_surge = item.get("is_surge")
    is_plunge = item.get("is_plunge")
    if not (is_surge or is_plunge):
        return None

    name = item["name"]
    if rule == "bullish_on_surge":
        return ("bullish", label) if is_surge else ("bearish", f"{name} 급락 -> 관련 수요 proxy 약화")
    if rule == "bearish_on_surge":
        return ("bearish", label) if is_surge else ("bullish", f"{name} 급락 -> 원가 부담 완화")
    return None


def compute_sentiment(sector_id: str, feed_dict: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bullish: list[str] = []
    bearish: list[str] = []
    leading: list[str] = []

    for cid, rule, label in DIRECT_COMMODITY_RULES.get(sector_id, []):
        item = feed_dict.get(cid)
        if not item:
            continue
        signal = _commodity_signal(item, rule, label)
        if not signal:
            continue
        direction, reason = signal
        if direction == "bullish":
            bullish.append(reason)
        else:
            bearish.append(reason)

    rule_set = FORWARD_SECTOR_RULES.get(sector_id, {})
    for cid, rule, label in rule_set.get("positive", []):
        item = feed_dict.get(cid)
        if not item:
            continue
        if _matches_forward(item, rule):
            bullish.append(label)
            leading.append(label)
    for cid, rule, label in rule_set.get("negative", []):
        item = feed_dict.get(cid)
        if not item:
            continue
        if _matches_forward(item, rule):
            bearish.append(label)
            leading.append(label)

    score = len(bullish) - len(bearish)
    if score > 0:
        sentiment = "bullish"
    elif score < 0:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    assessments = _indicator_assessments(
        CORE_WATCH_SIGNALS.get(sector_id, []),
        bullish,
        bearish,
        rule_set.get("next", []),
        feed_dict,
    )

    return {
        "sector_id": sector_id,
        "sentiment": sentiment,
        "score": score,
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "watch_signals": CORE_WATCH_SIGNALS.get(sector_id, []),
        "leading_signals": leading[:6],
        "key_takeaway": rule_set.get("takeaway", "가격 신호보다 섹터 고유 선행지표 확인이 우선"),
        "next_checks": rule_set.get("next", CORE_WATCH_SIGNALS.get(sector_id, [])[:4]),
        "indicator_assessments": assessments,
        "verdict": _verdict(score),
        "data_coverage": "core_watchlist" if sector_id in CORE_WATCH_SIGNALS else "no_data",
    }


INDICATOR_SOURCE_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("u3o8", "uranium", "우라늄"), "uranium_u3o8"),
    (("iridium", "이리듐"), "iridium"),
    (("platinum", "백금"), "platinum"),
    (("palladium", "팔라듐"), "palladium"),
    (("gold", "금 "), "gold"),
    (("silver", "은 "), "silver"),
    (("lithium", "리튬"), "lithium_carbonate"),
    (("nickel", "니켈"), "nickel_lme"),
    (("cobalt", "코발트"), "cobalt"),
    (("graphite", "흑연"), "natural_graphite"),
    (("copper", "구리"), "copper"),
    (("aluminum", "알루미늄"), "aluminum"),
    (("iron ore", "철광석"), "iron_ore"),
    (("hrc", "steel", "후판", "철강"), "hrc_steel"),
    (("brent",), "crude_brent"),
    (("wti", "oil price", "유가", "원유"), "crude_wti"),
    (("lng", "gas", "천연가스"), "natgas_henry_hub"),
    (("cotton", "면화"), "cotton"),
    (("corn", "옥수수"), "corn"),
    (("wheat", "밀"), "wheat"),
    (("sugar", "설탕"), "sugar"),
    (("coffee", "커피"), "coffee"),
    (("grain", "곡물"), "corn"),
    (("gallium", "갈륨"), "gallium"),
    (("germanium", "게르마늄"), "germanium"),
    (("neodymium", "희토류", "rare earth"), "neodymium"),
    (("titanium", "티타늄"), "titanium"),
    (("helium", "헬륨"), "helium"),
]


def _source_status(signal: str, feed_dict: dict[str, dict[str, Any]]) -> dict[str, str]:
    s = signal.lower()
    for keywords, item_id in INDICATOR_SOURCE_KEYWORDS:
        if not any(k.lower() in s for k in keywords):
            continue
        item = feed_dict.get(item_id)
        if not item:
            return {"source_status": "missing", "source_name": item_id, "updated_at": ""}
        status = item.get("coverage_status") or "unknown"
        if item.get("price") is None:
            status = "missing"
        return {
            "source_status": status,
            "source_name": item.get("name") or item_id,
            "updated_at": (item.get("data_as_of") or item.get("fetched_at") or "")[:10],
        }
    return {"source_status": "not_connected", "source_name": "수동/외부 지표", "updated_at": ""}


def _indicator_assessments(
    watch_signals: list[str],
    bullish: list[str],
    bearish: list[str],
    next_checks: list[str],
    feed_dict: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for signal in bullish:
        out.append({
            "name": signal.split("->")[0].strip(),
            "direction": "bullish",
            "reason": signal,
            **_source_status(signal, feed_dict),
        })
    for signal in bearish:
        out.append({
            "name": signal.split("->")[0].strip(),
            "direction": "bearish",
            "reason": signal,
            **_source_status(signal, feed_dict),
        })
    seen = {x["name"] for x in out}
    for signal in [*next_checks, *watch_signals]:
        name = signal.strip()
        if name in seen:
            continue
        seen.add(name)
        source = _source_status(name, feed_dict)
        out.append({
            "name": name,
            "direction": "watch",
            "reason": (
                "실시간/프록시 데이터 연결됨. 방향성은 원자료와 함께 확인 필요"
                if source["source_status"] not in {"not_connected", "missing"}
                else "아직 자동 수집 미연결. 원자료/API 연결 필요"
            ),
            **source,
        })
    return out[:10]


def _matches_forward(item: dict[str, Any], rule: str) -> bool:
    if rule == "surge":
        return bool(item.get("is_surge"))
    if rule == "plunge":
        return bool(item.get("is_plunge"))
    if rule == "uptrend":
        return bool(item.get("is_multi_month_uptrend") or (item.get("change_pct_60d") or 0) >= 8)
    if rule == "downtrend":
        return bool(item.get("is_multi_month_downtrend") or (item.get("change_pct_60d") or 0) <= -8)
    return False


def _verdict(score: int) -> str:
    if score >= 3:
        return "유망"
    if score >= 1:
        return "관심"
    if score <= -3:
        return "부담"
    if score <= -1:
        return "주의"
    return "중립"


def all_sector_sentiments() -> list[dict[str, Any]]:
    """Return conservative sentiment plus core watch signals for all sectors."""
    feed = fetch_feed()
    feed_dict = {
        f.id: {
            "id": f.id,
            "name": f.name,
            "price": f.price,
            "is_surge": f.is_surge,
            "is_plunge": f.is_plunge,
            "is_multi_month_uptrend": f.is_multi_month_uptrend,
            "is_multi_month_downtrend": f.is_multi_month_downtrend,
            "change_pct_60d": f.change_pct_60d,
            "surge_reasons": f.surge_reasons,
            "coverage_status": f.coverage_status,
            "data_as_of": f.data_as_of,
            "fetched_at": f.fetched_at,
        }
        for f in feed
    }
    return [compute_sentiment(sid, feed_dict) for sid in CORE_WATCH_SIGNALS.keys()]


def top_sectors(top_n: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Only rank sectors when direct live signals exist."""
    sentiments = all_sector_sentiments()
    bullish = sorted(
        [s for s in sentiments if s["sentiment"] == "bullish"],
        key=lambda x: x["score"],
        reverse=True,
    )[:top_n]
    bearish = sorted(
        [s for s in sentiments if s["sentiment"] == "bearish"],
        key=lambda x: x["score"],
    )[:top_n]
    return {"bullish_sectors": bullish, "bearish_sectors": bearish}
