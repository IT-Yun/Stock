import numpy as np
import pandas as pd


class TechnicalAnalysisService:
    """Service for calculating technical analysis indicators."""

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float | None:
        """Calculate RSI (Relative Strength Index). Range 0-100."""
        if df.empty or len(df) < period + 1:
            return None

        close = df["Close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        last_rsi = rsi.iloc[-1]
        if pd.isna(last_rsi):
            return None
        return round(float(last_rsi), 2)

    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
        """Calculate MACD (macd_line, signal_line, histogram)."""
        if df.empty or len(df) < 26:
            return None, None, None

        close = df["Close"]
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        macd_val = macd_line.iloc[-1]
        signal_val = signal_line.iloc[-1]
        hist_val = histogram.iloc[-1]

        if any(pd.isna(v) for v in [macd_val, signal_val, hist_val]):
            return None, None, None

        return round(float(macd_val), 4), round(float(signal_val), 4), round(float(hist_val), 4)

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20) -> tuple[float | None, float | None, float | None]:
        """Calculate Bollinger Bands (upper, middle, lower)."""
        if df.empty or len(df) < period:
            return None, None, None

        close = df["Close"]
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * 2)
        lower = middle - (std * 2)

        upper_val = upper.iloc[-1]
        middle_val = middle.iloc[-1]
        lower_val = lower.iloc[-1]

        if any(pd.isna(v) for v in [upper_val, middle_val, lower_val]):
            return None, None, None

        return round(float(upper_val), 2), round(float(middle_val), 2), round(float(lower_val), 2)

    @staticmethod
    def calculate_sma(df: pd.DataFrame, periods: list[int] | None = None) -> dict[int, float | None]:
        """Calculate Simple Moving Averages for given periods."""
        if periods is None:
            periods = [20, 50, 200]

        if df.empty:
            return {p: None for p in periods}

        close = df["Close"]
        result = {}
        for p in periods:
            if len(df) < p:
                result[p] = None
            else:
                sma = close.rolling(window=p).mean().iloc[-1]
                result[p] = round(float(sma), 2) if not pd.isna(sma) else None
        return result

    @staticmethod
    def generate_buy_sell_signal(df: pd.DataFrame) -> tuple[str, float]:
        """
        Combine all indicators into a recommendation with confidence score.
        Weighted: RSI (30%), MACD crossover (30%), Bollinger position (20%), SMA trend (20%).
        Returns (recommendation, confidence_score).
        """
        if df.empty or len(df) < 26:
            return "hold", 0.0

        score = 0.0
        weights_used = 0.0

        # RSI signal (30%)
        rsi = TechnicalAnalysisService.calculate_rsi(df)
        if rsi is not None:
            if rsi < 30:
                score += 0.30  # oversold = buy signal
            elif rsi < 40:
                score += 0.15
            elif rsi > 70:
                score -= 0.30  # overbought = sell signal
            elif rsi > 60:
                score -= 0.15
            weights_used += 0.30

        # MACD crossover signal (30%)
        macd_val, signal_val, hist_val = TechnicalAnalysisService.calculate_macd(df)
        if macd_val is not None and signal_val is not None:
            if macd_val > signal_val:
                score += 0.30  # bullish crossover
            else:
                score -= 0.30  # bearish crossover
            weights_used += 0.30

        # Bollinger position (20%)
        upper, middle, lower = TechnicalAnalysisService.calculate_bollinger_bands(df)
        if upper is not None and lower is not None:
            current_price = float(df["Close"].iloc[-1])
            bb_range = upper - lower
            if bb_range > 0:
                position = (current_price - lower) / bb_range
                if position < 0.2:
                    score += 0.20  # near lower band = buy
                elif position < 0.4:
                    score += 0.10
                elif position > 0.8:
                    score -= 0.20  # near upper band = sell
                elif position > 0.6:
                    score -= 0.10
            weights_used += 0.20

        # SMA trend (20%)
        smas = TechnicalAnalysisService.calculate_sma(df, [20, 50, 200])
        current_price = float(df["Close"].iloc[-1])
        sma_signals = 0
        sma_count = 0
        for period in [20, 50, 200]:
            if smas.get(period) is not None:
                if current_price > smas[period]:
                    sma_signals += 1
                else:
                    sma_signals -= 1
                sma_count += 1

        if sma_count > 0:
            sma_ratio = sma_signals / sma_count
            score += 0.20 * sma_ratio
            weights_used += 0.20

        # Normalize score to confidence
        if weights_used > 0:
            normalized = score / weights_used
        else:
            normalized = 0.0

        confidence = round(abs(normalized) * 100, 1)

        if normalized > 0.5:
            recommendation = "strong_buy"
        elif normalized > 0.15:
            recommendation = "buy"
        elif normalized < -0.5:
            recommendation = "strong_sell"
        elif normalized < -0.15:
            recommendation = "sell"
        else:
            recommendation = "hold"

        return recommendation, confidence
