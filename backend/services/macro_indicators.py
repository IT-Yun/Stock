"""거시 매크로 지표 라이브 fetch (yfinance).

대상:
- VIX (^VIX) — 변동성
- US 10Y Treasury (^TNX) — 장기금리 (값 ÷ 100 = % yield)
- US 3M T-Bill (^IRX)
- DXY (DX-Y.NYB) — 달러 인덱스
- USD/KRW (KRW=X) — 환율
- KOSPI (^KS11)
- S&P 500 (^GSPC)
- 금 (GC=F), 은 (SI=F) — 안전자산 헷지

60일 history → 가격, 1d/5d/60d 변동률, Z-score.
캐시 30분.
"""

from __future__ import annotations
import time
import math
from dataclasses import dataclass, asdict
from typing import Any
from services.stock_data import StockDataService


MACRO_TICKERS: list[dict[str, Any]] = [
    {"id": "vix", "name": "VIX", "ticker": "^VIX", "category": "변동성", "unit": "pt"},
    {"id": "treasury_10y", "name": "US 10Y Treasury", "ticker": "^TNX", "category": "금리", "unit": "% (×0.01)"},
    {"id": "treasury_3m", "name": "US 3M T-Bill", "ticker": "^IRX", "category": "금리", "unit": "% (×0.01)"},
    {"id": "dxy", "name": "DXY (달러 인덱스)", "ticker": "DX-Y.NYB", "category": "환율", "unit": "pt"},
    {"id": "usd_krw", "name": "USD/KRW", "ticker": "KRW=X", "category": "환율", "unit": "원"},
    {"id": "usd_jpy", "name": "USD/JPY", "ticker": "JPY=X", "category": "환율", "unit": "엔"},
    {"id": "eur_usd", "name": "EUR/USD", "ticker": "EURUSD=X", "category": "환율", "unit": "USD"},
    {"id": "kospi", "name": "KOSPI", "ticker": "^KS11", "category": "주가지수", "unit": "pt"},
    {"id": "sp500", "name": "S&P 500", "ticker": "^GSPC", "category": "주가지수", "unit": "pt"},
    {"id": "nasdaq", "name": "NASDAQ", "ticker": "^IXIC", "category": "주가지수", "unit": "pt"},
]


@dataclass
class MacroIndicator:
    id: str
    name: str
    ticker: str
    category: str
    unit: str
    price: float | None = None
    change_pct_1d: float | None = None
    change_pct_5d: float | None = None
    change_pct_60d: float | None = None
    zscore_60d: float | None = None
    error: str | None = None


_CACHE: tuple[float, list[MacroIndicator]] | None = None
_TTL = 1800


def _compute(history) -> dict[str, Any]:
    if history is None or history.empty:
        return {}
    closes = history["Close"].dropna()
    if len(closes) < 2:
        return {}

    price = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    out: dict[str, Any] = {"price": round(price, 4), "change_pct_1d": round((price - prev) / prev * 100, 2) if prev else None}

    if len(closes) >= 6:
        p5 = float(closes.iloc[-6])
        if p5:
            out["change_pct_5d"] = round((price - p5) / p5 * 100, 2)
    if len(closes) >= 60:
        p60 = float(closes.iloc[-60])
        if p60:
            out["change_pct_60d"] = round((price - p60) / p60 * 100, 2)
        rets = closes.pct_change().dropna().iloc[-60:]
        if len(rets) >= 30:
            mean, std = float(rets.mean()), float(rets.std())
            if std and not math.isnan(std):
                latest = (price - prev) / prev if prev else 0.0
                out["zscore_60d"] = round((latest - mean) / std, 2)
    return out


def fetch_macro_indicators(force: bool = False) -> list[MacroIndicator]:
    global _CACHE
    now = time.time()
    if not force and _CACHE and (now - _CACHE[0] < _TTL):
        return _CACHE[1]

    out: list[MacroIndicator] = []
    for spec in MACRO_TICKERS:
        ind = MacroIndicator(id=spec["id"], name=spec["name"], ticker=spec["ticker"],
                             category=spec["category"], unit=spec["unit"])
        try:
            hist = StockDataService.get_stock_history(spec["ticker"], period="3mo")
            for k, v in _compute(hist).items():
                setattr(ind, k, v)
        except Exception as e:
            ind.error = str(e)[:100]
        out.append(ind)

    _CACHE = (now, out)
    return out


def macro_dict() -> dict[str, MacroIndicator]:
    return {i.id: i for i in fetch_macro_indicators()}


def macro_as_dicts() -> list[dict[str, Any]]:
    return [asdict(i) for i in fetch_macro_indicators()]
