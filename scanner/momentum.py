from __future__ import annotations

from scanner.indicators import ema, macd, rsi_series
from scanner.models import Candle, MomentumResult
from scanner.structure import latest_resistance


def momentum_score(
    rsi: float,
    rsi_rising: bool,
    macd_above_signal: bool,
    macd_above_zero: bool,
    histogram_rising: bool,
    bullish_divergence: bool = False,
    bearish_divergence: bool = False,
    warning_recent: bool = False,
) -> int:
    if rsi >= 75:
        score = 20
    elif rsi >= 60:
        score = 30
    elif rsi >= 50:
        score = 22
    elif rsi >= 40:
        score = 10
    else:
        score = 0
    score += 10 if rsi_rising else 0
    score += 25 if macd_above_signal else 0
    score += 20 if macd_above_zero else 0
    score += 15 if histogram_rising else 0
    score += 5 if bullish_divergence else 0
    score -= 5 if bearish_divergence else 0
    score -= 10 if warning_recent else 0
    score = max(0, min(score, 100))
    if not macd_above_signal:
        score = min(score, 74)
    if rsi >= 75:
        score = min(score, 84)
    return score


def calculate_momentum(
    symbol: str,
    candles: list[Candle],
    timeframe: str,
    higher_timeframe_passed: bool,
) -> MomentumResult:
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    rsis = rsi_series(closes, 14)
    rsi = rsis[-1]
    rsi_rising = rsis[-1] > rsis[-2]
    macd_line, signal_line, histogram, prev_histogram = macd(closes)
    histogram_rising = histogram > prev_histogram
    macd_above_signal = macd_line > signal_line
    macd_above_zero = macd_line > 0
    warning_recent = rsi < 50 or not macd_above_signal
    score = momentum_score(
        rsi,
        rsi_rising,
        macd_above_signal,
        macd_above_zero,
        histogram_rising,
        warning_recent=warning_recent,
    )
    bullish_confirmation = (
        rsi >= 50 and macd_above_signal and histogram_rising and higher_timeframe_passed
    )
    if warning_recent:
        state = "Warning active"
    elif rsi >= 75:
        state = "Extended"
    elif score >= 85 and bullish_confirmation:
        state = "Strong bullish"
    elif score >= 70 and bullish_confirmation:
        state = "Bullish"
    elif not higher_timeframe_passed:
        state = "HTF blocked"
    elif macd_above_signal or rsi_rising:
        state = "Improving"
    else:
        state = "Neutral"
    ema21 = ema(closes, 21)
    trigger = max(highs[-5:])
    support = min(lows[-5:])
    warning = min(support, ema21)
    _ = latest_resistance(highs)
    return MomentumResult(
        symbol=symbol,
        timeframe=timeframe,
        score=score,
        state=state,
        rsi=rsi,
        rsi_rising=rsi_rising,
        macd=macd_line,
        macd_signal=signal_line,
        histogram=histogram,
        histogram_rising=histogram_rising,
        daily_filter_passed=higher_timeframe_passed,
        bullish_confirmation=bullish_confirmation,
        trigger=trigger,
        support=support,
        warning=warning,
    )


def strict_daily_filter(daily_momentum: MomentumResult) -> bool:
    return daily_momentum.rsi >= 50 and daily_momentum.macd > daily_momentum.macd_signal
