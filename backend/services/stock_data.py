import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf
from services.runtime_controls import limit_yfinance

try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False

from config import settings


# Simple in-memory cache: {key: (timestamp, data)}
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 1800  # 30 minutes — minimize yfinance calls to avoid rate limiting
DISK_CACHE_TTL = 21600  # 6 hours
_default_cache_dir = Path(settings.SECTOR_DATA_PATH).resolve().parent.parent / ".cache" / "market"
_render_cache_root = Path("/var/data/stock-cache")
_CACHE_DIR = Path(settings.CACHE_DIR) if settings.CACHE_DIR else (_render_cache_root if _render_cache_root.exists() else _default_cache_dir)
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _last_index_iso(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    idx = df.index[-1]
    if hasattr(idx, "isoformat"):
        return idx.isoformat()
    return str(idx)


def _with_info_meta(
    data: dict,
    *,
    source: str,
    fetched_at: str | None = None,
    data_as_of: str | None = None,
    is_stale: bool = False,
) -> dict:
    result = dict(data)
    result.setdefault("source", source)
    result.setdefault("fetched_at", fetched_at or _now_iso())
    if data_as_of is not None:
        result.setdefault("data_as_of", data_as_of)
    result["is_stale"] = is_stale
    result["cache_ttl_sec"] = CACHE_TTL
    return result


def _set_frame_meta(
    df: pd.DataFrame,
    *,
    source: str,
    fetched_at: str | None = None,
    is_stale: bool = False,
) -> pd.DataFrame:
    df.attrs["source"] = source
    df.attrs["fetched_at"] = fetched_at or _now_iso()
    df.attrs["data_as_of"] = _last_index_iso(df)
    df.attrs["is_stale"] = is_stale
    df.attrs["cache_ttl_sec"] = CACHE_TTL
    return df


def frame_metadata(df: pd.DataFrame) -> dict:
    """Return compact source/freshness metadata for API responses."""
    return {
        "source": df.attrs.get("source", "unknown"),
        "fetched_at": df.attrs.get("fetched_at"),
        "data_as_of": df.attrs.get("data_as_of", _last_index_iso(df)),
        "is_stale": bool(df.attrs.get("is_stale", False)),
        "cache_ttl_sec": df.attrs.get("cache_ttl_sec", CACHE_TTL),
    }


def _get_cached(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _set_cached(key: str, data: object):
    _cache[key] = (time.time(), data)


# ═══ curl_cffi browser-impersonation session for yfinance ═══
# Bypasses Yahoo Finance bot detection by mimicking real browser TLS fingerprint
_yf_session = None
try:
    from curl_cffi.requests import Session as CffiSession
    _yf_session = CffiSession(impersonate="chrome")
    # Patch yfinance to use curl_cffi session globally where supported.
    _original_yf_get_json = getattr(yf.utils, "get_json", None)
    if _original_yf_get_json is not None:
        yf.utils.get_json = lambda *a, **kw: _original_yf_get_json(*a, **{**kw, "session": _yf_session})
except (ImportError, Exception):
    pass


def _make_yf_ticker(ticker: str):
    """Create yfinance Ticker with browser-impersonation session if available."""
    if _yf_session:
        return yf.Ticker(ticker, session=_yf_session)
    return yf.Ticker(ticker)


# ═══ Global yfinance object cache ═══
# Prevents duplicate yfinance API calls across multiple endpoints for the same ticker.
# When /earnings, /checklist-live, /move-reasons all need stock.info for the same ticker,
# this ensures yfinance is only called ONCE per 30 minutes.

_yf_info_cache: dict[str, tuple[float, dict]] = {}
_yf_financials_cache: dict[str, tuple[float, object]] = {}
_yf_lock = __import__("threading").Lock()
_YF_CACHE_TTL = 1800  # 30 min


def get_yf_info(ticker: str) -> dict:
    """Get yfinance .info with global 30-min cache. Thread-safe."""
    with _yf_lock:
        cached = _yf_info_cache.get(ticker)
        if cached and time.time() - cached[0] < _YF_CACHE_TTL:
            return cached[1]

    # Not cached or expired — fetch (outside lock to allow parallel fetches for different tickers)
    try:
        with limit_yfinance():
            stock = _make_yf_ticker(ticker)
            info = stock.info or {}
        with _yf_lock:
            _yf_info_cache[ticker] = (time.time(), info)
        return info
    except Exception:
        # Return stale cache if available
        with _yf_lock:
            cached = _yf_info_cache.get(ticker)
            if cached:
                return cached[1]
        return {}


def get_yf_financials(ticker: str) -> tuple:
    """Get yfinance quarterly_financials + balance_sheet with global 30-min cache.
    Returns (quarterly_financials_df, quarterly_balance_sheet_df)."""
    cache_key = f"fin:{ticker}"
    with _yf_lock:
        cached = _yf_financials_cache.get(cache_key)
        if cached and time.time() - cached[0] < _YF_CACHE_TTL:
            return cached[1]

    try:
        with limit_yfinance():
            stock = _make_yf_ticker(ticker)
            qf = stock.quarterly_financials
            qbs = stock.quarterly_balance_sheet
        result = (qf, qbs)
        with _yf_lock:
            _yf_financials_cache[cache_key] = (time.time(), result)
        return result
    except Exception:
        with _yf_lock:
            cached = _yf_financials_cache.get(cache_key)
            if cached:
                return cached[1]
        return (pd.DataFrame(), pd.DataFrame())


def _cache_path(prefix: str, key: str, suffix: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{prefix}-{digest}.{suffix}"


def _load_disk_json(key: str, max_age: int = DISK_CACHE_TTL, allow_stale: bool = False) -> dict | None:
    path = _cache_path("json", key, "json")
    if not path.exists():
        return None
    if not allow_stale and time.time() - path.stat().st_mtime > max_age:
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _save_disk_json(key: str, data: object):
    path = _cache_path("json", key, "json")
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


def _load_disk_frame(key: str, max_age: int = DISK_CACHE_TTL, allow_stale: bool = False) -> pd.DataFrame | None:
    path = _cache_path("frame", key, "pkl")
    if not path.exists():
        return None
    if not allow_stale and time.time() - path.stat().st_mtime > max_age:
        return None
    try:
        df = pd.read_pickle(path)
        if isinstance(df, pd.DataFrame):
            return df
    except Exception:
        return None
    return None


def _save_disk_frame(key: str, df: pd.DataFrame):
    path = _cache_path("frame", key, "pkl")
    try:
        df.to_pickle(path)
    except Exception:
        pass


def _lookup_stock_name(ticker: str) -> str:
    normalized = ticker.upper().strip()
    for sector in StockDataService._load_sectors():
        for stock in sector.get("stocks", []):
            if str(stock.get("ticker", "")).upper().strip() == normalized:
                return str(stock.get("name", ticker))
    return ticker


class StockDataService:
    """Stock data service using FinanceDataReader (primary) + yfinance (fallback).

    FinanceDataReader is faster and more reliable for KRX stocks.
    yfinance is used as fallback and for US stocks when FDR is unavailable.
    All results are cached for 30 minutes to avoid API rate limits.
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

        disk_cached = _load_disk_json(f"info:{ticker}")
        disk_cache_source = str((disk_cached or {}).get("source", ""))
        prefer_fdr = FDR_AVAILABLE and StockDataService._is_krx(ticker)
        use_disk_info = (
            disk_cached is not None
            and disk_cached.get("source")
            and disk_cached.get("data_as_of")
            and (not prefer_fdr or disk_cache_source.startswith("FinanceDataReader"))
        )
        if use_disk_info:
            disk_cached = _with_info_meta(
                disk_cached,
                source=disk_cached.get("source", "disk-cache"),
                fetched_at=disk_cached.get("fetched_at"),
                data_as_of=disk_cached.get("data_as_of"),
                is_stale=False,
            )
            _set_cached(f"info:{ticker}", disk_cached)
            return disk_cached

        result = {"ticker": ticker, "price": 0.0, "change_percent": 0.0, "name": _lookup_stock_name(ticker)}

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
                        "name": _lookup_stock_name(ticker),
                        "price": round(current_price, 2),
                        "change_percent": round(change_pct, 2),
                    }
                    result = _with_info_meta(
                        result,
                        source="FinanceDataReader/KRX",
                        data_as_of=_last_index_iso(df),
                    )
                    _set_cached(f"info:{ticker}", result)
                    _save_disk_json(f"info:{ticker}", result)
                    return result
            except Exception:
                pass

        # Fallback to yfinance
        try:
            with limit_yfinance():
                stock = _make_yf_ticker(ticker)
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

            with limit_yfinance():
                info = stock.info
            name = info.get("shortName", info.get("longName", ticker))

            result = {
                "ticker": ticker,
                "name": name,
                "price": round(current_price, 2),
                "change_percent": round(change_percent, 2),
            }
            result = _with_info_meta(
                result,
                source="Yahoo Finance/yfinance",
                data_as_of=_last_index_iso(hist),
            )
        except Exception:
            stale = _load_disk_json(f"info:{ticker}", allow_stale=True)
            if stale is not None:
                stale = _with_info_meta(
                    stale,
                    source=stale.get("source", "stale-disk-cache"),
                    fetched_at=stale.get("fetched_at"),
                    data_as_of=stale.get("data_as_of"),
                    is_stale=True,
                )
                _set_cached(f"info:{ticker}", stale)
                return stale

        result = _with_info_meta(
            result,
            source=result.get("source", "unavailable"),
            data_as_of=result.get("data_as_of"),
            is_stale=result.get("source") is None,
        )
        _set_cached(f"info:{ticker}", result)
        _save_disk_json(f"info:{ticker}", result)
        return result

    @staticmethod
    def get_stock_history(ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Returns OHLCV DataFrame for a ticker."""
        cache_key = f"hist:{ticker}:{period}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        disk_cached = _load_disk_frame(cache_key)
        disk_source = str(disk_cached.attrs.get("source", "")) if disk_cached is not None else ""
        prefer_fdr = FDR_AVAILABLE and StockDataService._is_krx(ticker)
        if disk_cached is not None and disk_source and (not prefer_fdr or disk_source.startswith("FinanceDataReader")):
            _set_cached(cache_key, disk_cached)
            return disk_cached

        # Try FinanceDataReader for KRX
        if FDR_AVAILABLE and StockDataService._is_krx(ticker):
            try:
                code = StockDataService._krx_code(ticker)
                period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}.get(period, 90)
                end = datetime.now()
                start = end - timedelta(days=period_days)
                df = fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                if not df.empty:
                    _set_frame_meta(df, source="FinanceDataReader/KRX")
                    _set_cached(cache_key, df)
                    _save_disk_frame(cache_key, df)
                    return df
            except Exception:
                pass

        # Fallback to yfinance
        try:
            with limit_yfinance():
                stock = _make_yf_ticker(ticker)
                hist = stock.history(period=period)
            if not hist.empty:
                _set_frame_meta(hist, source="Yahoo Finance/yfinance")
            _set_cached(cache_key, hist)
            if not hist.empty:
                _save_disk_frame(cache_key, hist)
            return hist
        except Exception:
            stale = _load_disk_frame(cache_key, allow_stale=True)
            if stale is not None:
                _set_frame_meta(
                    stale,
                    source=stale.attrs.get("source", "stale-disk-cache"),
                    fetched_at=stale.attrs.get("fetched_at"),
                    is_stale=True,
                )
                _set_cached(cache_key, stale)
                return stale
            empty = pd.DataFrame()
            _set_frame_meta(empty, source="unavailable", is_stale=True)
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
