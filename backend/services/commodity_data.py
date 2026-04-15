import time
from models.schemas import CommodityPrice
from services.stock_data import StockDataService


COMMODITIES = {
    "금": {"symbol": "GC=F", "unit": "달러/온스"},
    "은": {"symbol": "SI=F", "unit": "달러/온스"},
    "원유 (WTI)": {"symbol": "CL=F", "unit": "달러/배럴"},
    "구리": {"symbol": "HG=F", "unit": "달러/파운드"},
    "우라늄 ETF": {"symbol": "URA", "unit": "달러"},
    "천연가스": {"symbol": "NG=F", "unit": "달러/MMBtu"},
    "리튬 ETF": {"symbol": "LIT", "unit": "달러"},
}

SECTOR_COMMODITY_MAP = {
    "반도체": ["은", "금"],
    "로봇": ["구리", "리튬 ETF"],
    "생명공학/유전자": [],
    "smr 소형원전": ["우라늄 ETF", "천연가스"],
    "smr": ["우라늄 ETF", "천연가스"],
    "energy": ["원유 (WTI)", "천연가스"],
    "materials": ["금", "구리"],
}

# Cache for commodity prices
_commodity_cache: dict[str, tuple[float, CommodityPrice]] = {}
_all_cache: tuple[float, list[CommodityPrice]] | None = None
CACHE_TTL = 1800  # 30 minutes — minimize yfinance calls to avoid rate limiting


def _fetch_single(name: str, info: dict) -> CommodityPrice | None:
    """Fetch a single commodity price with caching."""
    cached = _commodity_cache.get(name)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]

    try:
        hist = StockDataService.get_stock_history(info["symbol"], period="5d")
        if hist.empty:
            return None

        current_price = float(hist["Close"].iloc[-1])
        if len(hist) >= 2:
            prev_price = float(hist["Close"].iloc[-2])
            change_percent = ((current_price - prev_price) / prev_price) * 100
        else:
            change_percent = 0.0

        result = CommodityPrice(
            name=name,
            symbol=info["symbol"],
            price=round(current_price, 2),
            change_percent=round(change_percent, 2),
            unit=info["unit"],
        )
        _commodity_cache[name] = (time.time(), result)
        return result
    except Exception:
        return None


class CommodityDataService:
    """Service for fetching commodity prices via yfinance with caching."""

    @staticmethod
    def get_commodity_prices() -> list[CommodityPrice]:
        """Fetch prices for all tracked commodities (cached 30 min)."""
        global _all_cache
        if _all_cache and time.time() - _all_cache[0] < CACHE_TTL:
            return _all_cache[1]

        results = []
        for name, info in COMMODITIES.items():
            price = _fetch_single(name, info)
            if price:
                results.append(price)

        _all_cache = (time.time(), results)
        return results

    @staticmethod
    def get_related_commodities(sector_name: str) -> list[CommodityPrice]:
        """Return commodities related to a given sector."""
        sector_lower = sector_name.lower()
        related_names: list[str] = []

        for key, commodities in SECTOR_COMMODITY_MAP.items():
            if key in sector_lower or sector_lower in key:
                related_names.extend(commodities)
                break

        if not related_names:
            return CommodityDataService.get_commodity_prices()

        related_names = list(dict.fromkeys(related_names))

        results = []
        for name in related_names:
            if name not in COMMODITIES:
                continue
            price = _fetch_single(name, COMMODITIES[name])
            if price:
                results.append(price)

        return results
