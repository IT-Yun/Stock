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

    score = len(bullish) - len(bearish)
    if score > 0:
        sentiment = "bullish"
    elif score < 0:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    return {
        "sector_id": sector_id,
        "sentiment": sentiment,
        "score": score,
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "watch_signals": CORE_WATCH_SIGNALS.get(sector_id, []),
        "data_coverage": "core_watchlist" if sector_id in CORE_WATCH_SIGNALS else "no_data",
    }


def all_sector_sentiments() -> list[dict[str, Any]]:
    """Return conservative sentiment plus core watch signals for all sectors."""
    feed = fetch_feed()
    feed_dict = {
        f.id: {
            "id": f.id,
            "name": f.name,
            "is_surge": f.is_surge,
            "is_plunge": f.is_plunge,
            "surge_reasons": f.surge_reasons,
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
