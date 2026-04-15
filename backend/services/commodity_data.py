import yfinance as yf
from models.schemas import CommodityPrice


COMMODITIES = {
    "Gold": {"symbol": "GC=F", "unit": "USD/oz"},
    "Oil": {"symbol": "CL=F", "unit": "USD/barrel"},
    "Copper": {"symbol": "HG=F", "unit": "USD/lb"},
    "Uranium": {"symbol": "URA", "unit": "USD/share"},
    "Natural Gas": {"symbol": "NG=F", "unit": "USD/MMBtu"},
}

SECTOR_COMMODITY_MAP = {
    "energy": ["Oil", "Natural Gas"],
    "materials": ["Gold", "Copper"],
    "mining": ["Gold", "Copper", "Uranium"],
    "utilities": ["Natural Gas", "Uranium"],
    "technology": [],
    "healthcare": [],
    "financials": [],
    "industrials": ["Oil", "Copper"],
    "consumer": ["Oil"],
    "반도체": ["Copper"],
    "에너지": ["Oil", "Natural Gas"],
    "소재": ["Gold", "Copper"],
    "원자력": ["Uranium", "Natural Gas"],
}


class CommodityDataService:
    """Service for fetching commodity prices via yfinance."""

    @staticmethod
    def get_commodity_prices() -> list[CommodityPrice]:
        """Fetch prices for all tracked commodities."""
        results = []
        for name, info in COMMODITIES.items():
            try:
                ticker = yf.Ticker(info["symbol"])
                hist = ticker.history(period="2d")
                if hist.empty:
                    continue

                current_price = float(hist["Close"].iloc[-1])
                if len(hist) >= 2:
                    prev_price = float(hist["Close"].iloc[-2])
                    change_percent = ((current_price - prev_price) / prev_price) * 100
                else:
                    change_percent = 0.0

                results.append(CommodityPrice(
                    name=name,
                    symbol=info["symbol"],
                    price=round(current_price, 2),
                    change_percent=round(change_percent, 2),
                    unit=info["unit"],
                ))
            except Exception:
                continue

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

        # Deduplicate
        related_names = list(dict.fromkeys(related_names))

        results = []
        for name in related_names:
            if name not in COMMODITIES:
                continue
            info = COMMODITIES[name]
            try:
                ticker = yf.Ticker(info["symbol"])
                hist = ticker.history(period="2d")
                if hist.empty:
                    continue

                current_price = float(hist["Close"].iloc[-1])
                if len(hist) >= 2:
                    prev_price = float(hist["Close"].iloc[-2])
                    change_percent = ((current_price - prev_price) / prev_price) * 100
                else:
                    change_percent = 0.0

                results.append(CommodityPrice(
                    name=name,
                    symbol=info["symbol"],
                    price=round(current_price, 2),
                    change_percent=round(change_percent, 2),
                    unit=info["unit"],
                ))
            except Exception:
                continue

        return results
