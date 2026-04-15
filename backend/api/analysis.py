import pandas as pd
from fastapi import APIRouter
from models.schemas import AnalysisResult, TechnicalIndicators, CommodityPrice
from services.stock_data import StockDataService
from services.technical_analysis import TechnicalAnalysisService
from services.commodity_data import CommodityDataService

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/analysis/{ticker}")
async def get_analysis(ticker: str) -> AnalysisResult:
    """Full technical analysis with buy/sell signal for a ticker."""
    df = StockDataService.get_stock_history(ticker, period="6mo")

    rsi = TechnicalAnalysisService.calculate_rsi(df)
    macd_val, macd_signal, _ = TechnicalAnalysisService.calculate_macd(df)
    bb_upper, bb_middle, bb_lower = TechnicalAnalysisService.calculate_bollinger_bands(df)
    smas = TechnicalAnalysisService.calculate_sma(df)
    recommendation, confidence = TechnicalAnalysisService.generate_buy_sell_signal(df)

    signal_str = recommendation

    indicators = TechnicalIndicators(
        rsi=rsi,
        macd=macd_val,
        macd_signal=macd_signal,
        bollinger_upper=bb_upper,
        bollinger_middle=bb_middle,
        bollinger_lower=bb_lower,
        sma_20=smas.get(20),
        sma_50=smas.get(50),
        sma_200=smas.get(200),
        buy_sell_signal=signal_str,
    )

    return AnalysisResult(
        ticker=ticker.upper(),
        indicators=indicators,
        recommendation=recommendation,
        confidence_score=confidence,
    )


@router.get("/analysis/{ticker}/chart-data")
async def get_chart_data(ticker: str, period: str = "3mo") -> dict:
    """OHLCV data with indicator overlays for charting."""
    df = StockDataService.get_stock_history(ticker, period=period)

    if df.empty:
        return {"ticker": ticker, "data": [], "indicators": {}}

    # OHLCV data
    ohlcv = []
    for idx, row in df.iterrows():
        ohlcv.append({
            "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })

    # Calculate indicator overlays
    close = df["Close"]

    # SMA overlays
    sma_20 = close.rolling(window=20).mean()
    sma_50 = close.rolling(window=50).mean()

    # Bollinger Bands
    bb_middle = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_middle + (bb_std * 2)
    bb_lower = bb_middle - (bb_std * 2)
    rsi_series = close.diff()
    gain = rsi_series.where(rsi_series > 0, 0.0)
    loss = -rsi_series.where(rsi_series < 0, 0.0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    relative_strength = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + relative_strength))
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()

    sma_20_list = [round(float(v), 2) if not pd.isna(v) else None for v in sma_20]
    sma_50_list = [round(float(v), 2) if not pd.isna(v) else None for v in sma_50]
    bb_upper_list = [round(float(v), 2) if not pd.isna(v) else None for v in bb_upper]
    bb_middle_list = [round(float(v), 2) if not pd.isna(v) else None for v in bb_middle]
    bb_lower_list = [round(float(v), 2) if not pd.isna(v) else None for v in bb_lower]
    rsi_list = [round(float(v), 2) if not pd.isna(v) else None for v in rsi]
    macd_list = [round(float(v), 4) if not pd.isna(v) else None for v in macd_line]
    macd_signal_list = [round(float(v), 4) if not pd.isna(v) else None for v in macd_signal]

    return {
        "ticker": ticker.upper(),
        "data": ohlcv,
        "indicators": {
            "sma_20": sma_20_list,
            "sma_50": sma_50_list,
            "bollinger_upper": bb_upper_list,
            "bollinger_middle": bb_middle_list,
            "bollinger_lower": bb_lower_list,
            "rsi": rsi_list,
            "macd": macd_list,
            "macd_signal": macd_signal_list,
        },
    }


@router.get("/commodities")
async def get_commodities() -> list[CommodityPrice]:
    """Get all tracked commodity prices."""
    return CommodityDataService.get_commodity_prices()


@router.get("/commodities/{sector_name}")
async def get_sector_commodities(sector_name: str) -> list[CommodityPrice]:
    """Get commodities related to a specific sector."""
    return CommodityDataService.get_related_commodities(sector_name)
