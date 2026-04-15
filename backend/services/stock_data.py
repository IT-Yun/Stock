import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False

from config import settings


# Simple in-memory cache: {key: (timestamp, data)}
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 1800  # 30 minutes — minimize yfinance calls to avoid rate limiting


def _get_cached(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _set_cached(key: str, data: object):
    _cache[key] = (time.time(), data)


class StockDataService:
    """Stock data service using FinanceDataReader (primary) + yfinance (fallback).

    FinanceDataReader is faster and more reliable for KRX stocks.
    yfinance is used as fallback and for US stocks when FDR is unavailable.
    All results are cached for 5 minutes to avoid API rate limits.
    """

    @staticmethod
    def _is_krx(ticker: str) -> bool:
        return ticker.endswith(".KS") or ticker.endswith(".KQ")

    @staticmethod
    def _krx_code(ticker: str) -> str:
        """Convert '005930.KS' to '005930' for FinanceDataReader."""
        return ticker.split(".")[0]

    @staticmethod
    def _load_sectors() -> list[dict]:
        """Load sector metadata from the configured JSON file."""
        try:
            with Path(settings.SECTOR_DATA_PATH).open("r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def get_stock_info(ticker: str) -> dict:
        """Returns current price and change percent for a ticker."""
        cached = _get_cached(f"info:{ticker}")
        if cached:
            return cached

        result = {"ticker": ticker, "price": 0.0, "change_percent": 0.0, "name": ticker}

        # Try FinanceDataReader first for KRX stocks
        if FDR_AVAILABLE and StockDataService._is_krx(ticker):
            try:
                code = StockDataService._krx_code(ticker)
                end = datetime.now()
                start = end - timedelta(days=5)
                df = fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                if not df.empty and len(df) >= 1:
                    current_price = float(df["Close"].iloc[-1])
                    if len(df) >= 2:
                        prev_price = float(df["Close"].iloc[-2])
                        change_pct = ((current_price - prev_price) / prev_price) * 100
                    else:
                        change_pct = 0.0
                    result = {
                        "ticker": ticker,
                        "name": ticker,
                        "price": round(current_price, 2),
                        "change_percent": round(change_pct, 2),
                    }
                    _set_cached(f"info:{ticker}", result)
                    return result
            except Exception:
                pass

        # Fallback to yfinance
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if hist.empty:
                _set_cached(f"info:{ticker}", result)
                return result

            current_price = float(hist["Close"].iloc[-1])
            if len(hist) >= 2:
                prev_price = float(hist["Close"].iloc[-2])
                change_percent = ((current_price - prev_price) / prev_price) * 100
            else:
                change_percent = 0.0

            info = stock.info
            name = info.get("shortName", info.get("longName", ticker))

            result = {
                "ticker": ticker,
                "name": name,
                "price": round(current_price, 2),
                "change_percent": round(change_percent, 2),
            }
        except Exception:
            pass

        _set_cached(f"info:{ticker}", result)
        return result

    @staticmethod
    def get_stock_history(ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Returns OHLCV DataFrame for a ticker."""
        cache_key = f"hist:{ticker}:{period}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        # Try FinanceDataReader for KRX
        if FDR_AVAILABLE and StockDataService._is_krx(ticker):
            try:
                code = StockDataService._krx_code(ticker)
                period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}.get(period, 90)
                end = datetime.now()
                start = end - timedelta(days=period_days)
                df = fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                if not df.empty:
                    _set_cached(cache_key, df)
                    return df
            except Exception:
                pass

        # Fallback to yfinance
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            _set_cached(cache_key, hist)
            return hist
        except Exception:
            empty = pd.DataFrame()
            _set_cached(cache_key, empty)
            return empty

    @staticmethod
    def get_sector_stocks(sector_name: str) -> list[dict]:
        """Reads sectors.json and fetches live data for top 3 stocks in a sector."""
        sectors_data = StockDataService._load_sectors()
        if not sectors_data:
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
        cached = _get_cached("all_sectors")
        if cached:
            return cached

        sectors_data = StockDataService._load_sectors()
        if not sectors_data:
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

        _set_cached("all_sectors", results)
        return results
