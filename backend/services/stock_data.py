import json
import yfinance as yf
import pandas as pd
from config import settings


class StockDataService:
    """Service for fetching stock data via yfinance."""

    @staticmethod
    def get_stock_info(ticker: str) -> dict:
        """Returns current price and change percent for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if hist.empty:
                return {"ticker": ticker, "price": 0.0, "change_percent": 0.0, "name": ticker}

            current_price = float(hist["Close"].iloc[-1])
            if len(hist) >= 2:
                prev_price = float(hist["Close"].iloc[-2])
                change_percent = ((current_price - prev_price) / prev_price) * 100
            else:
                change_percent = 0.0

            info = stock.info
            name = info.get("shortName", info.get("longName", ticker))

            return {
                "ticker": ticker,
                "name": name,
                "price": round(current_price, 2),
                "change_percent": round(change_percent, 2),
            }
        except Exception:
            return {"ticker": ticker, "price": 0.0, "change_percent": 0.0, "name": ticker}

    @staticmethod
    def get_stock_history(ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Returns OHLCV DataFrame for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            return hist
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def get_sector_stocks(sector_name: str) -> list[dict]:
        """Reads sectors.json and fetches live data for top 3 stocks in a sector."""
        try:
            with open(settings.SECTOR_DATA_PATH, "r", encoding="utf-8") as f:
                sectors_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        sector = None
        for s in sectors_data:
            if s.get("name", "").lower() == sector_name.lower():
                sector = s
                break

        if not sector:
            return []

        stocks = sector.get("stocks", [])[:3]
        results = []
        for stock_info in stocks:
            ticker = stock_info.get("ticker", "")
            if not ticker:
                continue
            data = StockDataService.get_stock_info(ticker)
            data["sector"] = sector_name
            if "name" not in data or data["name"] == ticker:
                data["name"] = stock_info.get("name", ticker)
            results.append(data)

        return results

    @staticmethod
    def get_all_sectors() -> list[dict]:
        """Returns all sectors with their top 3 stocks."""
        try:
            with open(settings.SECTOR_DATA_PATH, "r", encoding="utf-8") as f:
                sectors_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        results = []
        for sector in sectors_data:
            sector_name = sector.get("name", "")
            description = sector.get("description", "")
            stocks = sector.get("stocks", [])[:3]

            stock_list = []
            for stock_info in stocks:
                ticker = stock_info.get("ticker", "")
                if not ticker:
                    continue
                data = StockDataService.get_stock_info(ticker)
                data["sector"] = sector_name
                if "name" not in data or data["name"] == ticker:
                    data["name"] = stock_info.get("name", ticker)
                stock_list.append(data)

            results.append({
                "name": sector_name,
                "description": description,
                "stocks": stock_list,
            })

        return results
