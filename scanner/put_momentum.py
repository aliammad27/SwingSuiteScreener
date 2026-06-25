from __future__ import annotations

from scanner.indicators import ema, macd, rsi_series
from scanner.models import Candle, MomentumResult


def put_momentum_score(
    rsi: float,
    rsi_falling: bool,
    macd_below_signal: bool,
    macd_below_zero: bool,
    histogram_falling: bool,
    bearish_divergence: bool = False,
    bullish_divergence: bool = False,
    warning_recent: bool = False,
) -> int:
    """Score bearish put momentum (mirror of call momentum_score).

    Low RSI and bearish MACD are positive signals for puts.
    Fields stored in MomentumResult use inverted semantics when returned by
    calculate_put_momentum:
      rsi_rising      -> True means RSI is falling (bearish)
      macd_above_signal -> True means MACD is below signal (bearish)
      macd_above_zero -> True means MACD is below zero
      histogram_rising -> True means histogram is falling (bearish)
      bullish_confirmation -> True means bearish confirmation is active
    """
    if rsi <= 25:
        score = 20
    elif rsi <= 40:
        score = 30
    elif rsi <= 50:
        score = 22
    elif rsi <= 60:
        score = 10
    else:
        score = 0
    score += 10 if rsi_falling else 0
    score += 25 if macd_below_signal else 0
    score += 20 if macd_below_zero else 0
    score += 15 if histogram_falling else 0
    score += 5 if bearish_divergence else 0
    score -= 5 if bullish_divergence else 0
    score -= 10 if warning_recent else 0
    score = max(0, min(score, 100))
    if not macd_below_signal:
        score = min(score, 74)
    if rsi <= 25:
        score = min(score, 84)
    return score


def calculate_put_momentum(
    symbol: str,
    candles: list[Candle],
    timeframe: str,
    higher_timeframe_passed: bool,
) -> MomentumResult:
    """Calculate bearish momentum for put candidates.

    Returns a MomentumResult where boolean fields carry inverted semantics:
      rsi_rising      -> actually rsi_falling
      macd_above_signal -> actually macd_below_signal
      macd_above_zero -> actually macd_below_zero
      histogram_rising -> actually histogram_falling
      bullish_confirmation -> actually bearish_confirmation
      trigger -> min(lows[-5:])  — put breakdown trigger
      support -> max(highs[-5:])  — overhead resistance / invalidation
      warning -> max(support, ema21) — level above which put is threatened
    """
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    rsis = rsi_series(closes, 14)
    rsi = rsis[-1]
    rsi_falling = rsis[-1] < rsis[-2]
    macd_line, signal_line, histogram, prev_histogram = macd(closes)
    histogram_falling = histogram < prev_histogram
    macd_below_signal = macd_line < signal_line
    macd_below_zero = macd_line < 0
    # Warning: bullish reversal signals (put threatens to fail)
    warning_recent = rsi > 50 or macd_line > signal_line
    score = put_momentum_score(
        rsi,
        rsi_falling=rsi_falling,
        macd_below_signal=macd_below_signal,
        macd_below_zero=macd_below_zero,
        histogram_falling=histogram_falling,
        warning_recent=warning_recent,
    )
    bearish_confirmation = (
        rsi < 50 and macd_below_signal and histogram_falling and higher_timeframe_passed
    )
    if warning_recent:
        state = "Warning active"
    elif score >= 85 and bearish_confirmation:
        state = "Strong bearish"
    elif score >= 70 and bearish_confirmation:
        state = "Bearish"
    elif not higher_timeframe_passed:
        state = "HTF blocked"
    elif macd_below_signal or rsi_falling:
        state = "Improving"
    else:
        state = "Neutral"
    ema21 = ema(closes, 21)
    # For puts: trigger = breakdown level (min lows); support = overhead resistance (max highs)
    trigger = min(lows[-5:])
    support = max(highs[-5:])
    warning = max(support, ema21)
    return MomentumResult(
        symbol=symbol,
        timeframe=timeframe,
        score=score,
        state=state,
        rsi=rsi,
        rsi_rising=rsi_falling,
        macd=macd_line,
        macd_signal=signal_line,
        histogram=histogram,
        histogram_rising=histogram_falling,
        daily_filter_passed=higher_timeframe_passed,
        bullish_confirmation=bearish_confirmation,
        trigger=trigger,
        support=support,
        warning=warning,
    )


def strict_bearish_daily_filter(daily_momentum: MomentumResult) -> bool:
    """Pass when the daily chart confirms a bearish setup for put entry timing.

    Requires daily RSI below 50 and MACD line below signal line.
    """
    return daily_momentum.rsi < 50 and daily_momentum.macd < daily_momentum.macd_signal
