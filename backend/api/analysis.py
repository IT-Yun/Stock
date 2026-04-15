import pandas as pd
import numpy as np
import yfinance as yf
from fastapi import APIRouter
from models.schemas import AnalysisResult, TechnicalIndicators, CommodityPrice
from services.stock_data import StockDataService
from services.technical_analysis import TechnicalAnalysisService
from services.commodity_data import CommodityDataService
from services.news_crawler import NewsCrawlerService

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
    """OHLCV data with ALL indicator overlays inlined per data point."""
    df = StockDataService.get_stock_history(ticker, period=period)

    if df.empty:
        return {"ticker": ticker, "data": []}

    close = df["Close"]

    # SMA overlays
    sma_20 = close.rolling(window=20).mean()
    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()

    # Bollinger Bands
    bb_middle = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_middle + (bb_std * 2)
    bb_lower = bb_middle - (bb_std * 2)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_histogram = macd_line - macd_signal

    # Build inline data
    data = []
    for i, (idx, row) in enumerate(df.iterrows()):
        point = {
            "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        # Inline indicators (None if not enough data)
        for name, series in [
            ("sma_20", sma_20), ("sma_50", sma_50), ("sma_200", sma_200),
            ("bollinger_upper", bb_upper), ("bollinger_middle", bb_middle), ("bollinger_lower", bb_lower),
            ("rsi", rsi), ("macd", macd_line), ("macd_signal", macd_signal), ("macd_histogram", macd_histogram),
        ]:
            v = series.iloc[i]
            point[name] = round(float(v), 2) if not pd.isna(v) else None
        data.append(point)

    return {"ticker": ticker.upper(), "data": data}


@router.get("/analysis/{ticker}/earnings")
async def get_earnings(ticker: str) -> dict:
    """Get earnings data (quarterly EPS, revenue) from yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Quarterly earnings
        quarterly_earnings = []
        try:
            qe = stock.quarterly_earnings
            if qe is not None and not qe.empty:
                for idx, row in qe.iterrows():
                    quarterly_earnings.append({
                        "date": str(idx),
                        "revenue": float(row.get("Revenue", 0)) if not pd.isna(row.get("Revenue", None)) else None,
                        "earnings": float(row.get("Earnings", 0)) if not pd.isna(row.get("Earnings", None)) else None,
                    })
        except Exception:
            pass

        # Quarterly financials
        quarterly_revenue = []
        try:
            qf = stock.quarterly_financials
            if qf is not None and not qf.empty:
                for col in qf.columns:
                    rev = qf.loc["Total Revenue", col] if "Total Revenue" in qf.index else None
                    net = qf.loc["Net Income", col] if "Net Income" in qf.index else None
                    quarterly_revenue.append({
                        "date": str(col.date()) if hasattr(col, "date") else str(col),
                        "revenue": float(rev) if rev is not None and not pd.isna(rev) else None,
                        "net_income": float(net) if net is not None and not pd.isna(net) else None,
                    })
        except Exception:
            pass

        return {
            "ticker": ticker.upper(),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "quarterly_earnings": quarterly_earnings,
            "quarterly_revenue": quarterly_revenue,
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


@router.get("/analysis/{ticker}/pattern")
async def get_pattern_analysis(ticker: str) -> dict:
    """
    Historical pattern analysis:
    - Find significant price moves in history
    - Analyze what indicators looked like before each major move
    - Compare current setup to historical patterns
    - Return pattern matches with similarity scores
    """
    try:
        # Get 2 years of data for pattern analysis
        df = StockDataService.get_stock_history(ticker, period="2y")
        if df.empty or len(df) < 60:
            return {"ticker": ticker.upper(), "patterns": [], "current_setup": {}, "events": []}

        close = df["Close"]
        dates = df.index

        # Calculate all indicators for the full history
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))

        sma_20 = close.rolling(window=20).mean()
        sma_50 = close.rolling(window=50).mean()

        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()

        bb_middle = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)

        # Find significant price moves (>5% in 10 trading days)
        events = []
        for i in range(50, len(df) - 10):
            future_return = (float(close.iloc[i + 10]) - float(close.iloc[i])) / float(close.iloc[i]) * 100
            if abs(future_return) >= 5:
                date_str = str(dates[i].date()) if hasattr(dates[i], "date") else str(dates[i])

                # Capture indicator snapshot before the move
                rsi_val = float(rsi_series.iloc[i]) if not pd.isna(rsi_series.iloc[i]) else None
                macd_val = float(macd_line.iloc[i]) if not pd.isna(macd_line.iloc[i]) else None
                macd_sig = float(macd_signal.iloc[i]) if not pd.isna(macd_signal.iloc[i]) else None
                sma20_val = float(sma_20.iloc[i]) if not pd.isna(sma_20.iloc[i]) else None
                sma50_val = float(sma_50.iloc[i]) if not pd.isna(sma_50.iloc[i]) else None
                price_val = float(close.iloc[i])
                bb_pos = None
                if not pd.isna(bb_upper.iloc[i]) and not pd.isna(bb_lower.iloc[i]):
                    bb_range = float(bb_upper.iloc[i]) - float(bb_lower.iloc[i])
                    if bb_range > 0:
                        bb_pos = round((price_val - float(bb_lower.iloc[i])) / bb_range, 2)

                events.append({
                    "date": date_str,
                    "price": round(price_val, 2),
                    "return_10d": round(future_return, 2),
                    "direction": "up" if future_return > 0 else "down",
                    "indicators": {
                        "rsi": round(rsi_val, 1) if rsi_val else None,
                        "macd_above_signal": (macd_val > macd_sig) if macd_val and macd_sig else None,
                        "price_above_sma20": (price_val > sma20_val) if sma20_val else None,
                        "price_above_sma50": (price_val > sma50_val) if sma50_val else None,
                        "bb_position": bb_pos,
                    },
                })

        # Deduplicate events (keep max abs return within 10-day windows)
        filtered_events = []
        used_dates = set()
        sorted_events = sorted(events, key=lambda e: abs(e["return_10d"]), reverse=True)
        for ev in sorted_events:
            date_val = pd.Timestamp(ev["date"])
            too_close = False
            for used in used_dates:
                if abs((date_val - used).days) < 10:
                    too_close = True
                    break
            if not too_close:
                used_dates.add(date_val)
                filtered_events.append(ev)
            if len(filtered_events) >= 20:
                break

        filtered_events.sort(key=lambda e: e["date"])

        # Current setup
        current_rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None
        current_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None
        current_macd_sig = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None
        current_sma20 = float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None
        current_sma50 = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else None
        current_price = float(close.iloc[-1])
        current_bb_pos = None
        if not pd.isna(bb_upper.iloc[-1]) and not pd.isna(bb_lower.iloc[-1]):
            bb_range = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
            if bb_range > 0:
                current_bb_pos = round((current_price - float(bb_lower.iloc[-1])) / bb_range, 2)

        current_setup = {
            "price": round(current_price, 2),
            "rsi": round(current_rsi, 1) if current_rsi else None,
            "macd_above_signal": (current_macd > current_macd_sig) if current_macd and current_macd_sig else None,
            "price_above_sma20": (current_price > current_sma20) if current_sma20 else None,
            "price_above_sma50": (current_price > current_sma50) if current_sma50 else None,
            "bb_position": current_bb_pos,
        }

        # Find similar historical setups (pattern matching)
        patterns = []
        for ev in filtered_events:
            ind = ev["indicators"]
            similarity = 0
            checks = 0

            if current_rsi and ind["rsi"]:
                checks += 1
                if abs(current_rsi - ind["rsi"]) < 10:
                    similarity += 1
                elif abs(current_rsi - ind["rsi"]) < 20:
                    similarity += 0.5

            if ind["macd_above_signal"] is not None and current_setup["macd_above_signal"] is not None:
                checks += 1
                if ind["macd_above_signal"] == current_setup["macd_above_signal"]:
                    similarity += 1

            if ind["price_above_sma20"] is not None and current_setup["price_above_sma20"] is not None:
                checks += 1
                if ind["price_above_sma20"] == current_setup["price_above_sma20"]:
                    similarity += 1

            if ind["price_above_sma50"] is not None and current_setup["price_above_sma50"] is not None:
                checks += 1
                if ind["price_above_sma50"] == current_setup["price_above_sma50"]:
                    similarity += 1

            if ind["bb_position"] is not None and current_bb_pos is not None:
                checks += 1
                if abs(ind["bb_position"] - current_bb_pos) < 0.15:
                    similarity += 1
                elif abs(ind["bb_position"] - current_bb_pos) < 0.3:
                    similarity += 0.5

            score = (similarity / checks * 100) if checks > 0 else 0
            if score >= 40:
                patterns.append({
                    **ev,
                    "similarity": round(score, 0),
                })

        patterns.sort(key=lambda p: p["similarity"], reverse=True)

        # Summary stats from similar patterns
        if patterns:
            similar_ups = [p for p in patterns if p["direction"] == "up"]
            similar_downs = [p for p in patterns if p["direction"] == "down"]
            avg_up = sum(p["return_10d"] for p in similar_ups) / len(similar_ups) if similar_ups else 0
            avg_down = sum(p["return_10d"] for p in similar_downs) / len(similar_downs) if similar_downs else 0
            up_probability = len(similar_ups) / len(patterns) * 100
        else:
            avg_up = 0
            avg_down = 0
            up_probability = 50

        return {
            "ticker": ticker.upper(),
            "current_setup": current_setup,
            "patterns": patterns[:10],
            "events": filtered_events,
            "summary": {
                "total_similar_patterns": len(patterns),
                "up_probability": round(up_probability, 1),
                "avg_up_return": round(avg_up, 2),
                "avg_down_return": round(avg_down, 2),
            },
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "patterns": [], "current_setup": {}, "events": [], "error": str(e)}


@router.get("/analysis/{ticker}/prediction")
async def get_prediction(ticker: str) -> dict:
    """
    Comprehensive 50+ technical indicator analysis with future price prediction.
    Analyses: trend, momentum, volatility, volume, oscillators, pattern, support/resistance.
    Returns aggregated scores per category and an overall prediction.
    """
    try:
        df = StockDataService.get_stock_history(ticker, period="1y")
        if df.empty or len(df) < 60:
            return {"ticker": ticker.upper(), "error": "Insufficient data"}

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        price = float(close.iloc[-1])

        indicators = {}
        scores = {}  # each indicator → score -1 to +1

        # ═══ TREND INDICATORS ═══

        # 1-8: SMA family
        for p in [5, 10, 20, 50, 100, 200]:
            sma = close.rolling(window=p).mean()
            if not pd.isna(sma.iloc[-1]):
                val = float(sma.iloc[-1])
                indicators[f"sma_{p}"] = round(val, 2)
                scores[f"sma_{p}"] = 1.0 if price > val else -1.0

        # 9-14: EMA family
        for p in [5, 10, 12, 20, 26, 50]:
            ema = close.ewm(span=p, adjust=False).mean()
            if not pd.isna(ema.iloc[-1]):
                val = float(ema.iloc[-1])
                indicators[f"ema_{p}"] = round(val, 2)
                scores[f"ema_{p}"] = 1.0 if price > val else -1.0

        # 15: SMA 20/50 cross
        if "sma_20" in indicators and "sma_50" in indicators:
            indicators["sma_20_50_cross"] = "golden" if indicators["sma_20"] > indicators["sma_50"] else "dead"
            scores["sma_20_50_cross"] = 1.0 if indicators["sma_20"] > indicators["sma_50"] else -1.0

        # 16: SMA 50/200 cross
        if "sma_50" in indicators and "sma_200" in indicators:
            indicators["sma_50_200_cross"] = "golden" if indicators["sma_50"] > indicators["sma_200"] else "dead"
            scores["sma_50_200_cross"] = 1.0 if indicators["sma_50"] > indicators["sma_200"] else -1.0

        # 17: Price vs SMA200 distance
        if "sma_200" in indicators:
            dist = (price - indicators["sma_200"]) / indicators["sma_200"] * 100
            indicators["sma200_distance_pct"] = round(dist, 2)
            scores["sma200_distance"] = max(-1, min(1, -dist / 20))  # far above = bearish, far below = bullish

        # 18-19: DEMA, TEMA
        ema1 = close.ewm(span=20, adjust=False).mean()
        ema2 = ema1.ewm(span=20, adjust=False).mean()
        dema = 2 * ema1 - ema2
        if not pd.isna(dema.iloc[-1]):
            indicators["dema_20"] = round(float(dema.iloc[-1]), 2)
            scores["dema_20"] = 1.0 if price > float(dema.iloc[-1]) else -1.0
        ema3 = ema2.ewm(span=20, adjust=False).mean()
        tema = 3 * ema1 - 3 * ema2 + ema3
        if not pd.isna(tema.iloc[-1]):
            indicators["tema_20"] = round(float(tema.iloc[-1]), 2)
            scores["tema_20"] = 1.0 if price > float(tema.iloc[-1]) else -1.0

        # 20: Ichimoku
        nine_high = high.rolling(window=9).max()
        nine_low = low.rolling(window=9).min()
        tenkan = (nine_high + nine_low) / 2
        twentysix_high = high.rolling(window=26).max()
        twentysix_low = low.rolling(window=26).min()
        kijun = (twentysix_high + twentysix_low) / 2
        if not pd.isna(tenkan.iloc[-1]) and not pd.isna(kijun.iloc[-1]):
            indicators["ichimoku_tenkan"] = round(float(tenkan.iloc[-1]), 2)
            indicators["ichimoku_kijun"] = round(float(kijun.iloc[-1]), 2)
            scores["ichimoku_tk_cross"] = 1.0 if float(tenkan.iloc[-1]) > float(kijun.iloc[-1]) else -1.0
            scores["ichimoku_price_kijun"] = 1.0 if price > float(kijun.iloc[-1]) else -1.0

        # 22: VWAP (approximated from daily data)
        cum_vol = volume.cumsum()
        cum_pv = (close * volume).cumsum()
        vwap = cum_pv / cum_vol
        if not pd.isna(vwap.iloc[-1]) and float(cum_vol.iloc[-1]) > 0:
            indicators["vwap"] = round(float(vwap.iloc[-1]), 2)
            scores["vwap"] = 1.0 if price > float(vwap.iloc[-1]) else -1.0

        # 23: Parabolic SAR (simplified)
        psar_val = float(close.rolling(5).min().iloc[-1]) if not pd.isna(close.rolling(5).min().iloc[-1]) else None
        if psar_val:
            indicators["psar_approx"] = round(psar_val, 2)
            scores["psar"] = 1.0 if price > psar_val else -1.0

        # ═══ MOMENTUM INDICATORS ═══

        # 24-26: RSI family
        for period in [7, 14, 21]:
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss_s = (-delta.where(delta < 0, 0.0))
            avg_g = gain.rolling(window=period, min_periods=period).mean()
            avg_l = loss_s.rolling(window=period, min_periods=period).mean()
            rs = avg_g / avg_l
            rsi = 100 - (100 / (1 + rs))
            if not pd.isna(rsi.iloc[-1]):
                val = float(rsi.iloc[-1])
                indicators[f"rsi_{period}"] = round(val, 1)
                if val < 30: scores[f"rsi_{period}"] = 1.0
                elif val < 40: scores[f"rsi_{period}"] = 0.5
                elif val > 70: scores[f"rsi_{period}"] = -1.0
                elif val > 60: scores[f"rsi_{period}"] = -0.5
                else: scores[f"rsi_{period}"] = 0.0

        # 27-28: Stochastic %K, %D
        low_14 = low.rolling(window=14).min()
        high_14 = high.rolling(window=14).max()
        stoch_k = 100 * (close - low_14) / (high_14 - low_14)
        stoch_d = stoch_k.rolling(window=3).mean()
        if not pd.isna(stoch_k.iloc[-1]):
            indicators["stoch_k"] = round(float(stoch_k.iloc[-1]), 1)
            indicators["stoch_d"] = round(float(stoch_d.iloc[-1]), 1) if not pd.isna(stoch_d.iloc[-1]) else None
            sk = float(stoch_k.iloc[-1])
            if sk < 20: scores["stoch_k"] = 1.0
            elif sk > 80: scores["stoch_k"] = -1.0
            else: scores["stoch_k"] = 0.0
            # K/D cross
            if indicators["stoch_d"] is not None:
                scores["stoch_kd_cross"] = 1.0 if sk > indicators["stoch_d"] else -1.0

        # 29: Williams %R
        wr = -100 * (high_14 - close) / (high_14 - low_14)
        if not pd.isna(wr.iloc[-1]):
            val = float(wr.iloc[-1])
            indicators["williams_r"] = round(val, 1)
            if val < -80: scores["williams_r"] = 1.0
            elif val > -20: scores["williams_r"] = -1.0
            else: scores["williams_r"] = 0.0

        # 30: MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - macd_signal
        if not pd.isna(macd_line.iloc[-1]):
            indicators["macd"] = round(float(macd_line.iloc[-1]), 4)
            indicators["macd_signal"] = round(float(macd_signal.iloc[-1]), 4)
            indicators["macd_histogram"] = round(float(macd_hist.iloc[-1]), 4)
            scores["macd_cross"] = 1.0 if float(macd_line.iloc[-1]) > float(macd_signal.iloc[-1]) else -1.0
            # 31: MACD histogram trend
            hist_3 = macd_hist.iloc[-3:]
            if len(hist_3) == 3 and all(not pd.isna(v) for v in hist_3):
                if float(hist_3.iloc[2]) > float(hist_3.iloc[1]) > float(hist_3.iloc[0]):
                    scores["macd_hist_trend"] = 1.0
                elif float(hist_3.iloc[2]) < float(hist_3.iloc[1]) < float(hist_3.iloc[0]):
                    scores["macd_hist_trend"] = -1.0
                else:
                    scores["macd_hist_trend"] = 0.0

        # 32: CCI (Commodity Channel Index)
        tp = (high + low + close) / 3
        cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
        if not pd.isna(cci.iloc[-1]):
            val = float(cci.iloc[-1])
            indicators["cci"] = round(val, 1)
            if val < -100: scores["cci"] = 1.0
            elif val > 100: scores["cci"] = -1.0
            else: scores["cci"] = val / 200  # mild signal

        # 33: MFI (Money Flow Index)
        tp_s = (high + low + close) / 3
        raw_mf = tp_s * volume
        mf_sign = tp_s.diff().apply(lambda x: 1 if x > 0 else -1)
        pos_mf = (raw_mf * (mf_sign == 1)).rolling(14).sum()
        neg_mf = (raw_mf * (mf_sign == -1)).rolling(14).sum()
        mfi = 100 - (100 / (1 + pos_mf / neg_mf.replace(0, 1)))
        if not pd.isna(mfi.iloc[-1]):
            val = float(mfi.iloc[-1])
            indicators["mfi"] = round(val, 1)
            if val < 20: scores["mfi"] = 1.0
            elif val > 80: scores["mfi"] = -1.0
            else: scores["mfi"] = 0.0

        # 34-36: Rate of Change
        for p in [5, 10, 20]:
            if len(close) > p:
                roc = (float(close.iloc[-1]) - float(close.iloc[-1-p])) / float(close.iloc[-1-p]) * 100
                indicators[f"roc_{p}"] = round(roc, 2)
                scores[f"roc_{p}"] = max(-1, min(1, roc / 10))

        # 37: Momentum (10-period)
        if len(close) > 10:
            mom = float(close.iloc[-1]) - float(close.iloc[-11])
            indicators["momentum_10"] = round(mom, 2)
            scores["momentum_10"] = 1.0 if mom > 0 else -1.0

        # 38: Ultimate Oscillator
        bp = close - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        tr_uo = pd.concat([high, close.shift(1)], axis=1).max(axis=1) - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        avg7 = bp.rolling(7).sum() / tr_uo.rolling(7).sum()
        avg14 = bp.rolling(14).sum() / tr_uo.rolling(14).sum()
        avg28 = bp.rolling(28).sum() / tr_uo.rolling(28).sum()
        uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
        if not pd.isna(uo.iloc[-1]):
            val = float(uo.iloc[-1])
            indicators["ultimate_oscillator"] = round(val, 1)
            if val < 30: scores["ultimate_osc"] = 1.0
            elif val > 70: scores["ultimate_osc"] = -1.0
            else: scores["ultimate_osc"] = 0.0

        # ═══ VOLATILITY INDICATORS ═══

        # 39-40: Bollinger Bands
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        if not pd.isna(bb_upper.iloc[-1]):
            bb_range = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
            if bb_range > 0:
                bb_pos = (price - float(bb_lower.iloc[-1])) / bb_range
                indicators["bb_position"] = round(bb_pos, 2)
                indicators["bb_width"] = round(bb_range / float(bb_mid.iloc[-1]) * 100, 2)
                if bb_pos < 0.2: scores["bb_position"] = 1.0
                elif bb_pos < 0.35: scores["bb_position"] = 0.5
                elif bb_pos > 0.8: scores["bb_position"] = -1.0
                elif bb_pos > 0.65: scores["bb_position"] = -0.5
                else: scores["bb_position"] = 0.0

        # 41: ATR (Average True Range)
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        if not pd.isna(atr.iloc[-1]):
            indicators["atr"] = round(float(atr.iloc[-1]), 2)
            indicators["atr_pct"] = round(float(atr.iloc[-1]) / price * 100, 2)

        # 42: Keltner Channel
        kc_mid = close.ewm(span=20, adjust=False).mean()
        kc_upper = kc_mid + 2 * atr
        kc_lower = kc_mid - 2 * atr
        if not pd.isna(kc_upper.iloc[-1]):
            indicators["kc_upper"] = round(float(kc_upper.iloc[-1]), 2)
            indicators["kc_lower"] = round(float(kc_lower.iloc[-1]), 2)
            scores["keltner"] = 1.0 if price < float(kc_lower.iloc[-1]) else (-1.0 if price > float(kc_upper.iloc[-1]) else 0.0)

        # 43: Donchian Channel
        dc_high = high.rolling(20).max()
        dc_low = low.rolling(20).min()
        if not pd.isna(dc_high.iloc[-1]):
            indicators["donchian_high"] = round(float(dc_high.iloc[-1]), 2)
            indicators["donchian_low"] = round(float(dc_low.iloc[-1]), 2)
            dc_mid = (float(dc_high.iloc[-1]) + float(dc_low.iloc[-1])) / 2
            scores["donchian"] = 1.0 if price > dc_mid else -1.0

        # ═══ VOLUME INDICATORS ═══

        # 44: OBV trend
        obv = (volume * close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()
        obv_sma = obv.rolling(20).mean()
        if not pd.isna(obv_sma.iloc[-1]):
            scores["obv_trend"] = 1.0 if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]) else -1.0

        # 45: Volume SMA ratio
        vol_sma = volume.rolling(20).mean()
        if not pd.isna(vol_sma.iloc[-1]) and float(vol_sma.iloc[-1]) > 0:
            vol_ratio = float(volume.iloc[-1]) / float(vol_sma.iloc[-1])
            indicators["volume_ratio"] = round(vol_ratio, 2)
            price_up = float(close.iloc[-1]) > float(close.iloc[-2]) if len(close) > 1 else True
            if vol_ratio > 1.5 and price_up: scores["volume_confirm"] = 1.0
            elif vol_ratio > 1.5 and not price_up: scores["volume_confirm"] = -1.0
            else: scores["volume_confirm"] = 0.0

        # 46: Chaikin Money Flow
        mfv = ((close - low) - (high - close)) / (high - low + 1e-10) * volume
        cmf = mfv.rolling(20).sum() / volume.rolling(20).sum()
        if not pd.isna(cmf.iloc[-1]):
            val = float(cmf.iloc[-1])
            indicators["cmf"] = round(val, 4)
            scores["cmf"] = max(-1, min(1, val * 5))

        # 47: A/D line trend
        ad = ((close - low) - (high - close)) / (high - low + 1e-10) * volume
        ad_cum = ad.cumsum()
        ad_sma = ad_cum.rolling(20).mean()
        if not pd.isna(ad_sma.iloc[-1]):
            scores["ad_line"] = 1.0 if float(ad_cum.iloc[-1]) > float(ad_sma.iloc[-1]) else -1.0

        # ═══ PATTERN/STRUCTURE ═══

        # 48: 52-week high/low position
        if len(close) >= 252:
            yr_high = float(high.iloc[-252:].max())
            yr_low = float(low.iloc[-252:].min())
        else:
            yr_high = float(high.max())
            yr_low = float(low.min())
        yr_range = yr_high - yr_low
        if yr_range > 0:
            yr_pos = (price - yr_low) / yr_range
            indicators["52w_position"] = round(yr_pos * 100, 1)
            if yr_pos < 0.2: scores["52w_position"] = 1.0
            elif yr_pos < 0.35: scores["52w_position"] = 0.5
            elif yr_pos > 0.9: scores["52w_position"] = -0.5
            else: scores["52w_position"] = 0.0

        # 49: ADX (trend strength)
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        atr14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / (atr14 + 1e-10))
        minus_di = 100 * (minus_dm.rolling(14).mean() / (atr14 + 1e-10))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
        adx = dx.rolling(14).mean()
        if not pd.isna(adx.iloc[-1]):
            indicators["adx"] = round(float(adx.iloc[-1]), 1)
            indicators["plus_di"] = round(float(plus_di.iloc[-1]), 1)
            indicators["minus_di"] = round(float(minus_di.iloc[-1]), 1)
            # ADX > 25 = strong trend, direction from DI
            if float(adx.iloc[-1]) > 25:
                scores["adx"] = 1.0 if float(plus_di.iloc[-1]) > float(minus_di.iloc[-1]) else -1.0
            else:
                scores["adx"] = 0.0

        # 50: Fibonacci retracement (from recent swing)
        lookback = min(60, len(close))
        swing_high = float(high.iloc[-lookback:].max())
        swing_low = float(low.iloc[-lookback:].min())
        fib_range = swing_high - swing_low
        if fib_range > 0:
            fib_382 = swing_high - fib_range * 0.382
            fib_500 = swing_high - fib_range * 0.500
            fib_618 = swing_high - fib_range * 0.618
            indicators["fib_382"] = round(fib_382, 2)
            indicators["fib_500"] = round(fib_500, 2)
            indicators["fib_618"] = round(fib_618, 2)
            # Near support levels = bullish
            for lvl in [fib_618, fib_500, fib_382]:
                if abs(price - lvl) / price < 0.02:
                    scores["fibonacci"] = 0.5 if price >= lvl else -0.5
                    break
            else:
                scores["fibonacci"] = 0.0

        # 51: Linear regression slope (20-day)
        if len(close) >= 20:
            x = np.arange(20)
            y = close.iloc[-20:].values.astype(float)
            slope = np.polyfit(x, y, 1)[0]
            indicators["lr_slope_20"] = round(slope, 4)
            scores["lr_slope"] = max(-1, min(1, slope / (price * 0.01)))

        # 52: Standard deviation position
        std_20 = float(close.rolling(20).std().iloc[-1]) if not pd.isna(close.rolling(20).std().iloc[-1]) else None
        if std_20 and std_20 > 0:
            mean_20 = float(close.rolling(20).mean().iloc[-1])
            z_score = (price - mean_20) / std_20
            indicators["z_score"] = round(z_score, 2)
            if z_score < -2: scores["z_score"] = 1.0
            elif z_score < -1: scores["z_score"] = 0.5
            elif z_score > 2: scores["z_score"] = -1.0
            elif z_score > 1: scores["z_score"] = -0.5
            else: scores["z_score"] = 0.0

        # ═══ AGGREGATE SCORES ═══
        total_indicators = len(scores)
        if total_indicators == 0:
            return {"ticker": ticker.upper(), "error": "No indicators computed"}

        bullish = sum(1 for v in scores.values() if v > 0)
        bearish = sum(1 for v in scores.values() if v < 0)
        neutral = sum(1 for v in scores.values() if v == 0)
        avg_score = sum(scores.values()) / total_indicators

        # Category breakdowns
        categories = {
            "trend": ["sma_", "ema_", "dema", "tema", "ichimoku", "vwap", "psar", "lr_slope"],
            "momentum": ["rsi_", "stoch_", "williams", "macd", "cci", "mfi", "roc_", "momentum", "ultimate"],
            "volatility": ["bb_", "keltner", "donchian", "z_score", "atr"],
            "volume": ["obv", "volume_", "cmf", "ad_line"],
            "structure": ["52w_", "fibonacci", "adx", "sma200_distance"],
        }

        category_scores = {}
        for cat, prefixes in categories.items():
            cat_scores = []
            for k, v in scores.items():
                if any(k.startswith(p) or p in k for p in prefixes):
                    cat_scores.append(v)
            if cat_scores:
                category_scores[cat] = {
                    "score": round(sum(cat_scores) / len(cat_scores) * 100, 1),
                    "bullish": sum(1 for v in cat_scores if v > 0),
                    "bearish": sum(1 for v in cat_scores if v < 0),
                    "neutral": sum(1 for v in cat_scores if v == 0),
                    "total": len(cat_scores),
                }

        # Overall prediction
        overall_score = round(avg_score * 100, 1)  # -100 to +100
        if overall_score >= 40: prediction = "strong_buy"
        elif overall_score >= 15: prediction = "buy"
        elif overall_score <= -40: prediction = "strong_sell"
        elif overall_score <= -15: prediction = "sell"
        else: prediction = "neutral"

        # Confidence based on agreement
        agreement = max(bullish, bearish) / total_indicators * 100
        confidence = round(agreement, 1)

        # Price targets (simple projection based on ATR and score direction)
        atr_val = indicators.get("atr", price * 0.02)
        if avg_score > 0:
            target_1w = round(price + atr_val * avg_score * 3, 2)
            target_1m = round(price + atr_val * avg_score * 8, 2)
        else:
            target_1w = round(price + atr_val * avg_score * 3, 2)
            target_1m = round(price + atr_val * avg_score * 8, 2)
        stop_loss = round(price - atr_val * 2, 2)

        return {
            "ticker": ticker.upper(),
            "price": round(price, 2),
            "prediction": prediction,
            "overall_score": overall_score,
            "confidence": confidence,
            "total_indicators": total_indicators,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "categories": category_scores,
            "targets": {
                "target_1w": target_1w,
                "target_1m": target_1m,
                "stop_loss": stop_loss,
            },
            "key_indicators": indicators,
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


@router.get("/analysis/{ticker}/move-reasons")
async def get_move_reasons(ticker: str, period: str = "3mo") -> dict:
    """
    Find significant price moves and attempt to find news/reasons for each.
    Returns big moves with potential catalysts from news search.
    """
    try:
        df = StockDataService.get_stock_history(ticker, period=period)
        if df.empty or len(df) < 5:
            return {"ticker": ticker.upper(), "moves": []}

        close = df["Close"]
        volume_s = df["Volume"]
        vol_sma = volume_s.rolling(10).mean()

        # Pre-fetch ticker info and news ONCE (not per-move)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            name = info.get("shortName", ticker).split(" ")[0]
        except Exception:
            name = ticker

        all_articles = []
        try:
            all_articles = NewsCrawlerService.get_sector_news(name)
        except Exception:
            pass

        moves = []
        for i in range(1, len(df)):
            pct = (float(close.iloc[i]) - float(close.iloc[i-1])) / float(close.iloc[i-1]) * 100
            if abs(pct) < 2.5:
                continue
            date_str = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            vol_ratio = float(volume_s.iloc[i]) / float(vol_sma.iloc[i]) if not pd.isna(vol_sma.iloc[i]) and float(vol_sma.iloc[i]) > 0 else 1.0

            # Match pre-fetched news to this date
            reasons = []
            for art in all_articles:
                if art.published_at and date_str[:7] in art.published_at:
                    reasons.append(art.title)

            # Classify the move type
            if pct > 5:
                move_type = "급등"
                reason_guess = "실적 서프라이즈 / 호재성 뉴스" if not reasons else reasons[0]
            elif pct > 2.5:
                move_type = "상승"
                reason_guess = "섹터 모멘텀 / 수급 개선" if not reasons else reasons[0]
            elif pct < -5:
                move_type = "급락"
                reason_guess = "실적 쇼크 / 악재성 뉴스" if not reasons else reasons[0]
            else:
                move_type = "하락"
                reason_guess = "차익실현 / 시장 조정" if not reasons else reasons[0]

            # Add context about volume
            vol_note = ""
            if vol_ratio > 2.0:
                vol_note = "거래량 폭증"
            elif vol_ratio > 1.5:
                vol_note = "거래량 증가"

            moves.append({
                "date": date_str,
                "change_pct": round(pct, 2),
                "price": round(float(close.iloc[i]), 2),
                "volume_ratio": round(vol_ratio, 2),
                "move_type": move_type,
                "reason": reason_guess,
                "vol_note": vol_note,
                "news": reasons[:3],
            })

        # Keep top moves by magnitude — more for longer periods
        moves.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
        limit = 25 if period in ("1y", "2y", "5y", "max") else 15
        return {"ticker": ticker.upper(), "moves": moves[:limit]}

    except Exception as e:
        return {"ticker": ticker.upper(), "moves": [], "error": str(e)}


# ── Static checklist data sources per ticker ──

CHECKLIST_SOURCES = {
    "NVDA": [
        {"item": "데이터센터 매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "HBM/GPU 수요 (SOX지수)", "type": "commodity", "symbol": "SOXX", "positive_if": "up"},
        {"item": "AI 캡엑스 (MSFT 추이)", "type": "commodity", "symbol": "MSFT", "positive_if": "up"},
        {"item": "경쟁사 AMD 추이", "type": "commodity", "symbol": "AMD", "positive_if": "down"},
        {"item": "구리 가격 (공급망)", "type": "commodity", "symbol": "HG=F", "positive_if": "stable"},
        {"item": "영업이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.2},
    ],
    "TSM": [
        {"item": "웨이퍼 수요 (SOX지수)", "type": "commodity", "symbol": "SOXX", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "구리 가격 (원자재)", "type": "commodity", "symbol": "HG=F", "positive_if": "stable"},
        {"item": "대만 달러 (환율)", "type": "commodity", "symbol": "TWD=X", "positive_if": "down"},
        {"item": "영업이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.3},
    ],
    "AVGO": [
        {"item": "AI 네트워킹 수요 (SOX)", "type": "commodity", "symbol": "SOXX", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "배당수익률", "type": "earnings_metric", "metric": "dividend_yield", "positive_if": "above", "threshold": 0.01},
        {"item": "VMware 시너지 (이익률)", "type": "earnings_metric", "metric": "operating_margin", "positive_if": "above", "threshold": 0.3},
    ],
    "000660.KS": [
        {"item": "DRAM 현물가격", "type": "commodity", "symbol": "SOXX", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "영업이익률 추이", "type": "earnings_metric", "metric": "operating_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
        {"item": "구리 가격 (수요)", "type": "commodity", "symbol": "HG=F", "positive_if": "up"},
    ],
    "005930.KS": [
        {"item": "DRAM/NAND 가격 추이", "type": "commodity", "symbol": "SOXX", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "영업이익률", "type": "earnings_metric", "metric": "operating_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    "TSLA": [
        {"item": "차량 인도량 (매출)", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "리튬 가격 (원가)", "type": "commodity", "symbol": "LIT", "positive_if": "down"},
        {"item": "이익률 추이", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.05},
        {"item": "EV 섹터 추이", "type": "commodity", "symbol": "DRIV", "positive_if": "up"},
        {"item": "에너지저장 수요 (ICLN)", "type": "commodity", "symbol": "ICLN", "positive_if": "up"},
    ],
    "ISRG": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "이익률 추이", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.15},
        {"item": "헬스케어 섹터 (XLV)", "type": "commodity", "symbol": "XLV", "positive_if": "up"},
        {"item": "ROE", "type": "earnings_metric", "metric": "roe", "positive_if": "above", "threshold": 0.15},
    ],
    "CEG": [
        {"item": "우라늄 가격 (URA)", "type": "commodity", "symbol": "URA", "positive_if": "up"},
        {"item": "천연가스 가격", "type": "commodity", "symbol": "NG=F", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "전력수요 (유틸리티 XLU)", "type": "commodity", "symbol": "XLU", "positive_if": "up"},
    ],
    "CCJ": [
        {"item": "우라늄 가격 (URA)", "type": "commodity", "symbol": "URA", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.05},
    ],
    "CRWD": [
        {"item": "매출 성장률 (ARR)", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.2},
        {"item": "사이버보안 섹터 (BUG)", "type": "commodity", "symbol": "BUG", "positive_if": "up"},
        {"item": "이익률 추이", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
    ],
    "CRSP": [
        {"item": "바이오텍 섹터 (XBI)", "type": "commodity", "symbol": "XBI", "positive_if": "up"},
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.0},
        {"item": "현금 보유 (P/B)", "type": "earnings_metric", "metric": "price_to_book", "positive_if": "below", "threshold": 10.0},
    ],
    "LLY": [
        {"item": "매출 성장률 (GLP-1)", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.15},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.15},
        {"item": "바이오 섹터 (IBB)", "type": "commodity", "symbol": "IBB", "positive_if": "up"},
        {"item": "경쟁사 NVO 추이", "type": "commodity", "symbol": "NVO", "positive_if": "down"},
    ],
    "IONQ": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.2},
        {"item": "양자컴퓨팅 (QTUM)", "type": "commodity", "symbol": "QTUM", "positive_if": "up"},
        {"item": "현금소진율 (이익률)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": -0.5},
    ],
    "RKLB": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.2},
        {"item": "우주산업 (UFO ETF)", "type": "commodity", "symbol": "UFO", "positive_if": "up"},
        {"item": "항공방산 (ITA ETF)", "type": "commodity", "symbol": "ITA", "positive_if": "up"},
    ],
    "BE": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "클린에너지 (ICLN)", "type": "commodity", "symbol": "ICLN", "positive_if": "up"},
        {"item": "이익률 (흑자전환)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "수소 관련 (백금)", "type": "commodity", "symbol": "PL=F", "positive_if": "up"},
    ],
    # ── 로봇 섹터 추가 ──
    "454910.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.15},
        {"item": "로봇/자동화 (ROBO ETF)", "type": "commodity", "symbol": "ROBO", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    "FANUY": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "로봇/자동화 (ROBO)", "type": "commodity", "symbol": "ROBO", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "일본 엔화 (수출경쟁)", "type": "commodity", "symbol": "JPY=X", "positive_if": "down"},
    ],
    "267250.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "로봇/자동화 (ROBO)", "type": "commodity", "symbol": "ROBO", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    # ── 원자력 섹터 추가 ──
    "BWXT": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "우라늄 (URA ETF)", "type": "commodity", "symbol": "URA", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "방산 (ITA ETF)", "type": "commodity", "symbol": "ITA", "positive_if": "up"},
    ],
    "034020.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "우라늄 (URA ETF)", "type": "commodity", "symbol": "URA", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    "015760.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.0},
        {"item": "전력 유틸리티 (XLU)", "type": "commodity", "symbol": "XLU", "positive_if": "up"},
        {"item": "이익률 (흑자전환)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "천연가스 가격", "type": "commodity", "symbol": "NG=F", "positive_if": "down"},
    ],
    # ── 사이버보안 섹터 추가 ──
    "PANW": [
        {"item": "매출 성장률 (ARR)", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.15},
        {"item": "사이버보안 (BUG ETF)", "type": "commodity", "symbol": "BUG", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "경쟁사 CRWD 추이", "type": "commodity", "symbol": "CRWD", "positive_if": "down"},
    ],
    "FTNT": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "사이버보안 (BUG ETF)", "type": "commodity", "symbol": "BUG", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.15},
    ],
    "ZS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.25},
        {"item": "사이버보안 (BUG ETF)", "type": "commodity", "symbol": "BUG", "positive_if": "up"},
        {"item": "이익률 (흑자전환)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
    ],
    "S": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.3},
        {"item": "사이버보안 (BUG ETF)", "type": "commodity", "symbol": "BUG", "positive_if": "up"},
        {"item": "이익률 (적자폭)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": -0.2},
    ],
    # ── 우주항공 섹터 추가 ──
    "LMT": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.03},
        {"item": "방산 (ITA ETF)", "type": "commodity", "symbol": "ITA", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "배당수익률", "type": "earnings_metric", "metric": "dividend_yield", "positive_if": "above", "threshold": 0.02},
    ],
    "LHX": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.03},
        {"item": "방산 (ITA ETF)", "type": "commodity", "symbol": "ITA", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.08},
        {"item": "우주산업 (UFO ETF)", "type": "commodity", "symbol": "UFO", "positive_if": "up"},
    ],
    "047810.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "방산 (ITA ETF)", "type": "commodity", "symbol": "ITA", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.05},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    "BA": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "항공 (JETS ETF)", "type": "commodity", "symbol": "JETS", "positive_if": "up"},
        {"item": "이익률 (흑자전환)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "방산 (ITA ETF)", "type": "commodity", "symbol": "ITA", "positive_if": "up"},
    ],
    # ── 바이오 섹터 추가 ──
    "ILMN": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "유전체/바이오 (XBI)", "type": "commodity", "symbol": "XBI", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
    ],
    "207940.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.15},
        {"item": "바이오 (IBB ETF)", "type": "commodity", "symbol": "IBB", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.15},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    "068270.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "바이오시밀러 (IBB)", "type": "commodity", "symbol": "IBB", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    # ── 양자컴퓨팅 섹터 추가 ──
    "GOOG": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "양자컴퓨팅 (QTUM)", "type": "commodity", "symbol": "QTUM", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.2},
        {"item": "빅테크 (QQQ)", "type": "commodity", "symbol": "QQQ", "positive_if": "up"},
    ],
    "IBM": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.03},
        {"item": "양자컴퓨팅 (QTUM)", "type": "commodity", "symbol": "QTUM", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.1},
        {"item": "배당수익률", "type": "earnings_metric", "metric": "dividend_yield", "positive_if": "above", "threshold": 0.03},
    ],
    "RGTI": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.2},
        {"item": "양자컴퓨팅 (QTUM)", "type": "commodity", "symbol": "QTUM", "positive_if": "up"},
        {"item": "현금소진율 (이익률)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": -0.5},
    ],
    "MSFT": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "클라우드 (SKYY ETF)", "type": "commodity", "symbol": "SKYY", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.3},
        {"item": "빅테크 (QQQ)", "type": "commodity", "symbol": "QQQ", "positive_if": "up"},
    ],
    # ── 수소 섹터 추가 ──
    "PLUG": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "클린에너지 (ICLN)", "type": "commodity", "symbol": "ICLN", "positive_if": "up"},
        {"item": "이익률 (적자폭)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": -0.3},
        {"item": "수소 관련 (백금)", "type": "commodity", "symbol": "PL=F", "positive_if": "up"},
    ],
    "ENPH": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "태양광 (TAN ETF)", "type": "commodity", "symbol": "TAN", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.2},
        {"item": "클린에너지 (ICLN)", "type": "commodity", "symbol": "ICLN", "positive_if": "up"},
    ],
    "005380.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
        {"item": "EV/자동차 (DRIV)", "type": "commodity", "symbol": "DRIV", "positive_if": "up"},
        {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.05},
        {"item": "환율 (USD/KRW)", "type": "commodity", "symbol": "KRW=X", "positive_if": "up"},
    ],
    "336260.KS": [
        {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.1},
        {"item": "클린에너지 (ICLN)", "type": "commodity", "symbol": "ICLN", "positive_if": "up"},
        {"item": "이익률 (흑자전환)", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
        {"item": "수소 관련 (백금)", "type": "commodity", "symbol": "PL=F", "positive_if": "up"},
    ],
}


@router.get("/analysis/{ticker}/checklist-live")
async def get_checklist_live(ticker: str) -> dict:
    """
    Return live checklist data with:
    - Real price data & sparklines for each item
    - Stock price overlay for correlation visualization
    - Correlation coefficient (how much this item affects the stock)
    - Danger/safety threshold lines
    - Items sorted by importance (correlation strength)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    try:
        sources = CHECKLIST_SOURCES.get(ticker, CHECKLIST_SOURCES.get(ticker.replace(".KS", "").replace(".KQ", ""), []))
        if not sources:
            sources = [
                {"item": "매출 성장률", "type": "earnings_metric", "metric": "revenue_growth", "positive_if": "above", "threshold": 0.05},
                {"item": "이익률", "type": "earnings_metric", "metric": "profit_margin", "positive_if": "above", "threshold": 0.0},
                {"item": "ROE", "type": "earnings_metric", "metric": "roe", "positive_if": "above", "threshold": 0.1},
            ]

        # Fetch earnings data once
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        earnings_data = {
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "dividend_yield": info.get("dividendYield"),
            "price_to_book": info.get("priceToBook"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
        }

        # Fetch stock's own 1-year price history for correlation analysis
        stock_hist = pd.DataFrame()
        try:
            stock_hist = stock.history(period="1y")
        except Exception:
            pass

        # Pre-fetch all commodity data in parallel (1 year for correlation)
        commodity_symbols = list(set(s["symbol"] for s in sources if s["type"] == "commodity"))
        commodity_cache = {}

        def fetch_commodity(sym):
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="1y")
                return sym, hist
            except Exception:
                return sym, pd.DataFrame()

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_commodity, sym): sym for sym in commodity_symbols}
            for future in as_completed(futures, timeout=20):
                try:
                    sym, hist = future.result(timeout=12)
                    commodity_cache[sym] = hist
                except Exception:
                    pass

        # Pre-crawl preliminary earnings from news (once per request)
        company_name = info.get("shortName") or info.get("longName") or ticker
        preliminary_earnings = {}
        try:
            preliminary_earnings = NewsCrawlerService.crawl_preliminary_earnings(company_name, ticker)
        except Exception:
            pass

        # Normalize stock price to 0-100 scale for overlay on each chart
        stock_overlay = []
        if not stock_hist.empty and len(stock_hist) > 5:
            s_min = float(stock_hist["Close"].min())
            s_max = float(stock_hist["Close"].max())
            s_range = s_max - s_min if s_max > s_min else 1.0
            step_s = max(1, len(stock_hist) // 60)
            for idx, row in stock_hist.iloc[::step_s].iterrows():
                d = str(idx.date()) if hasattr(idx, "date") else str(idx)
                stock_overlay.append({
                    "date": d,
                    "stock_price": round(float(row["Close"]), 2),
                    "stock_norm": round((float(row["Close"]) - s_min) / s_range * 100, 1),
                })

        def compute_correlation(commodity_hist: pd.DataFrame) -> float:
            """Compute Pearson correlation between commodity and stock price."""
            if stock_hist.empty or commodity_hist.empty:
                return 0.0
            try:
                # Align dates
                merged = pd.DataFrame({
                    "stock": stock_hist["Close"],
                    "commodity": commodity_hist["Close"],
                }).dropna()
                if len(merged) < 20:
                    return 0.0
                corr = float(np.corrcoef(merged["stock"].values, merged["commodity"].values)[0, 1])
                return round(corr, 3) if not np.isnan(corr) else 0.0
            except Exception:
                return 0.0

        def compute_thresholds(hist: pd.DataFrame, positive_if: str) -> dict:
            """Compute danger/safety threshold lines — tighter thresholds to catch early warning."""
            if hist.empty or len(hist) < 20:
                return {}
            try:
                closes = hist["Close"].dropna().values.astype(float)
                mean_val = float(np.mean(closes))
                std_val = float(np.std(closes))
                p25 = float(np.percentile(closes, 25))
                p75 = float(np.percentile(closes, 75))
                current = float(closes[-1])

                # Recent trend: compare last 20 days avg vs full avg
                recent_avg = float(np.mean(closes[-20:])) if len(closes) >= 20 else current
                trend_declining = recent_avg < mean_val  # recent trend is below average

                if positive_if == "up":
                    # Danger = 25th percentile (tighter than mean-std)
                    # If recent trend is already declining, raise the danger line to recent support
                    danger_line = round(max(p25, recent_avg * 0.95) if trend_declining else p25, 2)
                    safe_line = round(p75, 2)
                    danger_label = f"${danger_line} 이하 → 매도 신호"
                    safe_label = f"${safe_line} 이상 → 매수 신호"
                elif positive_if == "down":
                    # For "down is good" (e.g., competitor price, cost items)
                    danger_line = round(min(p75, recent_avg * 1.05) if not trend_declining else p75, 2)
                    safe_line = round(p25, 2)
                    danger_label = f"${danger_line} 이상 → 매도 신호"
                    safe_label = f"${safe_line} 이하 → 매수 신호"
                else:  # stable
                    danger_line = round(mean_val + std_val, 2)
                    safe_line = round(mean_val, 2)
                    danger_label = f"${danger_line} 이상 → 불안정"
                    safe_label = f"${safe_line} 부근 → 안정"

                # Trend warning
                trend_warn = ""
                if positive_if == "up" and len(closes) >= 10:
                    last5 = float(np.mean(closes[-5:]))
                    last20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else mean_val
                    if last5 < last20 * 0.97:
                        trend_warn = "최근 하락 추세 — 주의 필요"
                elif positive_if == "down" and len(closes) >= 10:
                    last5 = float(np.mean(closes[-5:]))
                    last20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else mean_val
                    if last5 > last20 * 1.03:
                        trend_warn = "최근 상승 추세 — 비용 압박"

                return {
                    "danger_line": danger_line,
                    "safe_line": safe_line,
                    "danger_label": danger_label,
                    "safe_label": safe_label,
                    "danger_dir": "below" if positive_if == "up" else "above",
                    "mean": round(mean_val, 2),
                    "current": round(current, 2),
                    "p25": round(p25, 2),
                    "p75": round(p75, 2),
                    "trend_warn": trend_warn,
                }
            except Exception:
                return {}

        results = []
        for src in sources:
            item = {
                "name": src["item"],
                "status": "neutral",
                "value": None,
                "detail": "",
                "trend_data": [],
                "stock_overlay": [],
                "correlation": 0.0,
                "corr_label": "",
                "thresholds": {},
                "source": "",
                "importance": 0,
            }

            if src["type"] == "earnings_metric":
                metric = src["metric"]
                val = earnings_data.get(metric)
                if val is not None:
                    threshold = src.get("threshold", 0)
                    positive_if = src.get("positive_if", "above")
                    # Build quarterly chart data
                    quarterly_trend = ""
                    quarterly_chart = []  # [{quarter: "2024Q3", value: 66.1}, ...]
                    try:
                        financials = stock.quarterly_financials
                        if financials is not None and not financials.empty:
                            if metric == "revenue_growth":
                                rev = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else None
                                if rev is not None and len(rev.dropna()) >= 2:
                                    vals = rev.dropna()
                                    # Build chart: QoQ growth for each quarter
                                    rev_vals = [(str(idx.date()) if hasattr(idx, "date") else str(idx), float(v)) for idx, v in vals.items()]
                                    rev_vals.reverse()  # oldest first
                                    for qi in range(1, len(rev_vals)):
                                        prev_v = rev_vals[qi - 1][1]
                                        cur_v = rev_vals[qi][1]
                                        if prev_v != 0:
                                            growth = (cur_v - prev_v) / abs(prev_v) * 100
                                            dt = rev_vals[qi][0]
                                            quarterly_chart.append({"quarter": dt[:7], "value": round(growth, 1)})
                                    # QoQ text
                                    if len(rev_vals) >= 2:
                                        latest_g = (rev_vals[-1][1] - rev_vals[-2][1]) / abs(rev_vals[-2][1]) * 100
                                        quarterly_trend = f"QoQ {'+'  if latest_g > 0 else ''}{latest_g:.1f}%"
                            elif "margin" in metric:
                                inc = financials
                                rev_row = "Total Revenue"
                                # Determine numerator row based on metric
                                if metric == "operating_margin" and "Operating Income" in inc.index:
                                    num_row = "Operating Income"
                                elif "Gross Profit" in inc.index and metric == "profit_margin":
                                    num_row = "Net Income" if "Net Income" in inc.index else "Gross Profit"
                                else:
                                    num_row = "Net Income" if "Net Income" in inc.index else None

                                if num_row and rev_row in inc.index and num_row in inc.index:
                                    rev_q = inc.loc[rev_row].dropna()
                                    num_q = inc.loc[num_row].dropna()
                                    # Build chart: margin % for each quarter
                                    common_cols = [c for c in rev_q.index if c in num_q.index]
                                    margin_pts = []
                                    for c in common_cols:
                                        r = float(rev_q[c])
                                        n = float(num_q[c])
                                        if r != 0:
                                            margin_pts.append((str(c.date()) if hasattr(c, "date") else str(c), round(n / r * 100, 1)))
                                    margin_pts.reverse()  # oldest first
                                    for mp in margin_pts:
                                        quarterly_chart.append({"quarter": mp[0][:7], "value": mp[1]})
                                    # QoQ delta text
                                    if len(margin_pts) >= 2:
                                        margin_delta = margin_pts[-1][1] - margin_pts[-2][1]
                                        quarterly_trend = f"전분기 대비 {'+'  if margin_delta > 0 else ''}{margin_delta:.1f}%p"
                    except Exception:
                        pass

                    if positive_if == "above":
                        item["status"] = "positive" if val > threshold else ("negative" if val < 0 else "neutral")
                    elif positive_if == "below":
                        item["status"] = "positive" if val < threshold else "negative"
                    if "margin" in metric or "growth" in metric or metric == "roe" or metric == "dividend_yield":
                        item["value"] = round(val * 100, 1)
                        pct_str = f"{round(val * 100, 1)}%"
                        item["detail"] = f"{pct_str} {quarterly_trend}" if quarterly_trend else pct_str
                        item["thresholds"] = {
                            "danger_line": round(threshold * 100 * 0.5, 1) if positive_if == "above" else round(threshold * 100 * 1.5, 1),
                            "safe_line": round(threshold * 100, 1),
                            "danger_label": f"{round(threshold * 100 * 0.5, 1)}% 이하 → 매도 신호" if positive_if == "above" else f"{round(threshold * 100 * 1.5, 1)}% 이상 → 매도 신호",
                            "safe_label": f"{round(threshold * 100, 1)}% 이상 → 긍정" if positive_if == "above" else f"{round(threshold * 100, 1)}% 이하 → 긍정",
                            "danger_dir": "below" if positive_if == "above" else "above",
                            "current": round(val * 100, 1),
                            "trend_warn": quarterly_trend if ("−" in quarterly_trend or "-" in quarterly_trend) and positive_if == "above" else "",
                        }
                    else:
                        item["value"] = round(val, 2)
                        item["detail"] = f"{round(val, 2)}"
                    # ── Inject preliminary earnings from news if available ──
                    if preliminary_earnings.get("found") and quarterly_chart:
                        pe_data = preliminary_earnings["data"]
                        last_q = quarterly_chart[-1] if quarterly_chart else {}
                        last_q_date = last_q.get("quarter", "2025-04")
                        # Compute next quarter date
                        try:
                            lq_parts = last_q_date.split("-")
                            lq_y, lq_m = int(lq_parts[0]), int(lq_parts[1])
                            nq_m = lq_m + 3
                            nq_y = lq_y + (1 if nq_m > 12 else 0)
                            nq_m = ((nq_m - 1) % 12) + 1
                            next_q = f"{nq_y}-{nq_m:02d}"
                        except Exception:
                            next_q = "잠정"

                        # For revenue_growth: compute growth from preliminary revenue
                        if metric == "revenue_growth" and "revenue_억" in pe_data:
                            # We have revenue in 억원, compare to last quarter's absolute revenue
                            try:
                                rev_row = stock.quarterly_financials.loc["Total Revenue"] if "Total Revenue" in stock.quarterly_financials.index else None
                                if rev_row is not None and len(rev_row.dropna()) >= 1:
                                    last_rev = float(rev_row.dropna().values[0])
                                    # Convert 억원 to same unit (yfinance uses raw currency)
                                    # Samsung: yfinance in KRW, 1억 = 100,000,000
                                    prelim_rev = pe_data["revenue_억"] * 1e8
                                    if last_rev > 0:
                                        prelim_growth = (prelim_rev - last_rev) / abs(last_rev) * 100
                                        quarterly_chart.append({
                                            "quarter": next_q,
                                            "value": round(prelim_growth, 1),
                                            "preliminary": True,
                                        })
                                        quarterly_trend = f"잠정 QoQ {'+'  if prelim_growth > 0 else ''}{prelim_growth:.1f}%"
                                        item["detail"] = f"{item.get('detail', '')} → 잠정 {'+' if prelim_growth > 0 else ''}{prelim_growth:.1f}%"
                            except Exception:
                                pass

                        # For margin metrics: compute from preliminary op_profit / revenue
                        elif "margin" in metric and "operating_profit_억" in pe_data and "revenue_억" in pe_data:
                            try:
                                prelim_margin = pe_data["operating_profit_억"] / pe_data["revenue_억"] * 100
                                quarterly_chart.append({
                                    "quarter": next_q,
                                    "value": round(prelim_margin, 1),
                                    "preliminary": True,
                                })
                                item["detail"] = f"{item.get('detail', '')} → 잠정 {prelim_margin:.1f}%"
                            except Exception:
                                pass

                    item["quarterly_chart"] = quarterly_chart
                    item["preliminary_data"] = preliminary_earnings.get("data", {}) if preliminary_earnings.get("found") else {}
                    item["source"] = f"Yahoo Finance ({ticker})" + (" + 뉴스 잠정실적" if preliminary_earnings.get("found") else "")
                    item["importance"] = 70
                else:
                    item["detail"] = "데이터 없음"

            elif src["type"] == "commodity":
                try:
                    sym = src["symbol"]
                    positive_if = src.get("positive_if", "up")
                    hist = commodity_cache.get(sym, pd.DataFrame())
                    if not hist.empty and len(hist) > 20:
                        closes = hist["Close"].values.astype(float)
                        last_price = float(closes[-1])
                        first_price = float(closes[0])
                        change_pct = (last_price - first_price) / first_price * 100

                        # ── TREND DETECTION — this is the key metric ──
                        ma5 = float(np.mean(closes[-5:])) if len(closes) >= 5 else last_price
                        ma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else last_price
                        ma50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else ma20
                        # Recent momentum: 5-day vs 20-day
                        short_trend = (ma5 - ma20) / ma20 * 100
                        # Medium momentum: 20-day vs 50-day
                        mid_trend = (ma20 - ma50) / ma50 * 100 if len(closes) >= 50 else short_trend
                        # 1-month change
                        month_ago = float(closes[-22]) if len(closes) >= 22 else first_price
                        month_change = (last_price - month_ago) / month_ago * 100

                        # Trend direction label
                        if short_trend > 2:
                            trend_dir = "급상승"
                            trend_emoji = "up_fast"
                        elif short_trend > 0.5:
                            trend_dir = "상승중"
                            trend_emoji = "up"
                        elif short_trend < -2:
                            trend_dir = "급하락"
                            trend_emoji = "down_fast"
                        elif short_trend < -0.5:
                            trend_dir = "하락중"
                            trend_emoji = "down"
                        else:
                            trend_dir = "보합"
                            trend_emoji = "flat"

                        # STATUS based on TREND DIRECTION (not just absolute level)
                        if positive_if == "up":
                            # "up is good" — declining trend = danger even if price is still high
                            if trend_emoji in ("down_fast", "down"):
                                item["status"] = "negative"  # 하락 추세 = 위험
                            elif trend_emoji in ("up_fast", "up"):
                                item["status"] = "positive"
                            else:
                                item["status"] = "neutral"
                        elif positive_if == "down":
                            # "down is good" — rising trend = danger
                            if trend_emoji in ("up_fast", "up"):
                                item["status"] = "negative"
                            elif trend_emoji in ("down_fast", "down"):
                                item["status"] = "positive"
                            else:
                                item["status"] = "neutral"
                        elif positive_if == "stable":
                            item["status"] = "positive" if abs(short_trend) < 2 else "negative"

                        item["value"] = round(change_pct, 1)
                        item["detail"] = f"${round(last_price, 2)} | {trend_dir} (1개월 {'+' if month_change > 0 else ''}{round(month_change, 1)}%)"
                        item["trend_dir"] = trend_dir
                        item["trend_emoji"] = trend_emoji
                        item["short_trend"] = round(short_trend, 2)

                        # Trend data
                        c_min = float(hist["Close"].min())
                        c_max = float(hist["Close"].max())
                        c_range = c_max - c_min if c_max > c_min else 1.0
                        step = max(1, len(hist) // 60)
                        item["trend_data"] = [
                            {
                                "date": str(idx.date()),
                                "close": round(float(row["Close"]), 2),
                                "norm": round((float(row["Close"]) - c_min) / c_range * 100, 1),
                            }
                            for idx, row in hist.iloc[::step].iterrows()
                        ]

                        # Correlation with stock price
                        corr = compute_correlation(hist)
                        item["correlation"] = corr
                        abs_corr = abs(corr)
                        if positive_if == "down":
                            # For "down is good", negative correlation with stock = positive influence
                            effective_corr = -corr
                        else:
                            effective_corr = corr
                        if abs_corr >= 0.7:
                            item["corr_label"] = "매우 강한 연관" if effective_corr > 0 else "매우 강한 역연관"
                        elif abs_corr >= 0.4:
                            item["corr_label"] = "강한 연관" if effective_corr > 0 else "강한 역연관"
                        elif abs_corr >= 0.2:
                            item["corr_label"] = "약한 연관" if effective_corr > 0 else "약한 역연관"
                        else:
                            item["corr_label"] = "연관 약함"
                        item["importance"] = round(abs_corr * 100)

                        # Threshold / danger lines
                        item["thresholds"] = compute_thresholds(hist, positive_if)

                        # Stock overlay data (merged by nearest date)
                        item["stock_overlay"] = stock_overlay

                        item["source"] = f"Yahoo Finance ({sym})"
                except Exception:
                    item["detail"] = "조회 실패"

            results.append(item)

        # ── NEWS-BASED EARNINGS ALERT ──
        # Crawl latest earnings/results news for the stock
        try:
            company_name = info.get("shortName") or info.get("longName") or ticker
            # Search both Korean and English news for earnings info
            news_keywords_ko = [f"{company_name} 실적", f"{ticker} 실적 발표"]
            news_keywords_en = [f"{company_name} earnings results", f"{ticker} quarterly earnings"]

            all_news = []
            for kw in news_keywords_ko:
                try:
                    articles = NewsCrawlerService.crawl_naver_news(kw)
                    all_news.extend(articles)
                except Exception:
                    pass
            for kw in news_keywords_en:
                try:
                    articles = NewsCrawlerService.crawl_google_news_rss(kw, lang="en")
                    all_news.extend(articles)
                except Exception:
                    pass
            for kw in news_keywords_ko[:1]:
                try:
                    articles = NewsCrawlerService.crawl_google_news_rss(kw, lang="ko")
                    all_news.extend(articles)
                except Exception:
                    pass

            # Deduplicate
            seen = set()
            unique_news = []
            for a in all_news:
                if a.title not in seen:
                    seen.add(a.title)
                    unique_news.append(a)

            # Filter for earnings-related keywords
            earnings_keywords = ["실적", "잠정", "매출", "영업이익", "순이익", "가이던스",
                                "earnings", "revenue", "profit", "guidance", "beat", "miss",
                                "quarterly", "results", "forecast", "outlook", "EPS"]
            earnings_news = []
            for a in unique_news:
                title_lower = (a.title or "").lower()
                if any(kw.lower() in title_lower for kw in earnings_keywords):
                    earnings_news.append(a)

            if earnings_news:
                # Determine sentiment from headlines
                positive_words = ["호실적", "어닝서프라이즈", "사상최대", "성장", "beat", "surge",
                                  "record", "strong", "exceeded", "outperform", "상향", "증가"]
                negative_words = ["어닝쇼크", "부진", "하락", "감소", "miss", "decline", "weak",
                                  "below", "disappoint", "하향", "적자", "손실"]

                pos_count = 0
                neg_count = 0
                for a in earnings_news[:5]:
                    t = (a.title or "").lower()
                    pos_count += sum(1 for w in positive_words if w.lower() in t)
                    neg_count += sum(1 for w in negative_words if w.lower() in t)

                if pos_count > neg_count:
                    news_status = "positive"
                    news_detail = f"최근 실적 뉴스 {len(earnings_news)}건 — 호실적 신호"
                elif neg_count > pos_count:
                    news_status = "negative"
                    news_detail = f"최근 실적 뉴스 {len(earnings_news)}건 — 부진 신호"
                else:
                    news_status = "neutral"
                    news_detail = f"최근 실적 뉴스 {len(earnings_news)}건"

                # Top 3 headlines as summary
                top_headlines = [a.title for a in earnings_news[:3]]

                results.append({
                    "name": "📰 최신 실적 뉴스",
                    "status": news_status,
                    "detail": news_detail,
                    "value": None,
                    "trend_data": [],
                    "trend_dir": None,
                    "trend_emoji": None,
                    "short_trend": 0,
                    "thresholds": {},
                    "quarterly_chart": [],
                    "source": "Naver + Google News",
                    "importance": 65,
                    "correlation": 0,
                    "corr_label": "",
                    "stock_overlay": [],
                    "news_headlines": top_headlines,
                })
        except Exception:
            pass

        # Sort by importance (highest correlation first)
        results.sort(key=lambda r: r.get("importance", 0), reverse=True)

        return {"ticker": ticker.upper(), "checklist": results}

    except Exception as e:
        return {"ticker": ticker.upper(), "checklist": [], "error": str(e)}


@router.get("/commodities/history/{symbol}")
async def get_commodity_history(symbol: str, period: str = "6mo") -> dict:
    """Get commodity price history for charting."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            return {"symbol": symbol, "data": []}

        data = []
        for idx, row in hist.iterrows():
            data.append({
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
            })
        return {"symbol": symbol, "data": data}
    except Exception:
        return {"symbol": symbol, "data": []}


@router.get("/commodities")
async def get_commodities() -> list[CommodityPrice]:
    """Get all tracked commodity prices."""
    return CommodityDataService.get_commodity_prices()


@router.get("/commodities/{sector_name}")
async def get_sector_commodities(sector_name: str) -> list[CommodityPrice]:
    """Get commodities related to a specific sector."""
    return CommodityDataService.get_related_commodities(sector_name)
