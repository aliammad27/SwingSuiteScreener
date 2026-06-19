from __future__ import annotations

from scanner.indicators import anchored_vwap, atr, bollinger, ema, sma
from scanner.models import Candle, CommandResult
from scanner.structure import classify_structure, confirmed_pivot_lows, nearest_support_below


def _relative_strength(stock_closes: list[float], benchmark_closes: list[float]) -> str:
    ratios = [s / b for s, b in zip(stock_closes[-len(benchmark_closes) :], benchmark_closes, strict=True)]
    avg = ema(ratios, 21)
    rising = ratios[-1] > ratios[-6]
    if ratios[-1] > avg and rising:
        return "Leading"
    if ratios[-1] > avg:
        return "Strong"
    if rising:
        return "Improving"
    return "Lagging"


def calculate_command(
    symbol: str,
    daily: list[Candle],
    benchmark_daily: list[Candle],
    weekly: list[Candle],
) -> CommandResult:
    closes = [c.close for c in daily]
    highs = [c.high for c in daily]
    lows = [c.low for c in daily]
    volumes = [c.volume for c in daily]
    benchmark_closes = [c.close for c in benchmark_daily[-len(daily) :]]

    ema21 = ema(closes, 21)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    sma200_prev = sum(closes[-210:-10]) / 200
    current_atr = atr(highs, lows, closes, 14)
    _, upper_band, _, width = bollinger(closes, 20, 2)
    widths = [bollinger(closes[:idx], 20, 2)[3] for idx in range(20, len(closes) + 1)]
    width_avg = sum(widths[-50:]) / 50
    atr_percent = current_atr / closes[-1] * 100
    atr_values = [
        atr(highs[:idx], lows[:idx], closes[:idx], 14) / closes[idx - 1] * 100
        for idx in range(15, len(closes) + 1)
    ]
    atr_percent_avg = sum(atr_values[-50:]) / 50
    volatility_state = "Normal"
    if width < 0.75 * width_avg:
        volatility_state = "Squeeze"
    elif atr_percent > 1.25 * atr_percent_avg:
        volatility_state = "High"
    elif atr_percent < 0.80 * atr_percent_avg:
        volatility_state = "Low"

    month_anchor = max(0, len(closes) - 21)
    vwap = anchored_vwap(highs, lows, closes, volumes, month_anchor)
    above_vwap = closes[-1] > vwap
    rs = _relative_strength(closes, benchmark_closes)
    rel_volume = volumes[-1] / sma([float(v) for v in volumes], 20)
    bullish_candle = closes[-1] >= daily[-1].open
    if rel_volume >= 1.30:
        volume_state = "Expansion"
    elif rel_volume >= 1.0:
        volume_state = "Above average"
    elif rel_volume >= 0.70:
        volume_state = "Normal"
    else:
        volume_state = "Light"
    structure = classify_structure(highs, lows, 5, 3)
    weekly_ema21 = ema([c.close for c in weekly], 21)
    weekly_alignment = weekly[-1].close > weekly_ema21
    breakout_level = max(highs[-21:-1])
    breakout_confirmed = daily[-2].close <= breakout_level < closes[-1]
    breakout_watch = closes[-1] < breakout_level and breakout_level - closes[-1] <= 0.5 * current_atr
    pivot_lows = confirmed_pivot_lows(lows, 5, 3)
    latest_pivot_low = pivot_lows[-1][1] if pivot_lows else min(lows[-20:])
    support = nearest_support_below(closes[-1], [ema21, sma50, vwap, latest_pivot_low])
    pullback_touched = daily[-1].low <= support + (0.30 * current_atr)
    pullback_held = closes[-1] > support and closes[-1] >= daily[-1].open
    pullback_setup = pullback_touched and pullback_held
    extended = closes[-1] > upper_band and (closes[-1] - ema21) > (1.50 * current_atr)

    score = 0
    score += 10 if closes[-1] > ema21 else 0
    score += 10 if ema21 > sma50 else 0
    score += 10 if closes[-1] > sma50 else 0
    score += 15 if sma50 > sma200 else 0
    score += 10 if closes[-1] > sma200 else 0
    score += 5 if sma200 > sma200_prev else 0
    score += 15 if rs == "Leading" else 8 if rs == "Strong" else 0
    score += 10 if above_vwap else 0
    score += 10 if volume_state == "Expansion" and bullish_candle else 5 if rel_volume >= 1 else 0
    score += 5 if structure == "Bullish" else 3 if structure == "Improving" else 0
    score += 5 if weekly_alignment else 0

    trend = "Uptrend" if closes[-1] > ema21 and ema21 > sma50 and sma50 > sma200 else "Weak"
    if closes[-1] < sma200 or score < 45:
        call_bias = "Avoid"
    elif extended:
        call_bias = "Extended"
    elif breakout_confirmed and trend == "Uptrend":
        call_bias = "Breakout confirmed"
    elif score >= 70 and pullback_setup and above_vwap:
        call_bias = "Pullback setup"
    elif breakout_watch and score >= 65:
        call_bias = "Breakout watch"
    elif score >= 75:
        call_bias = "Bullish"
    elif score >= 60:
        call_bias = "Watch"
    else:
        call_bias = "Mixed"

    rejection_reasons: list[str] = []
    if closes[-1] < sma200:
        rejection_reasons.append("below_sma200")
    if score < 60:
        rejection_reasons.append("command_score_below_60")
    if extended:
        rejection_reasons.append("extended")

    return CommandResult(
        symbol=symbol,
        score=min(score, 100),
        call_bias=call_bias,
        trend=trend,
        relative_strength=rs,
        relative_volume=rel_volume,
        volume_state=volume_state,
        volatility_state=volatility_state,
        structure=structure,
        above_vwap=above_vwap,
        anchored_vwap=vwap,
        weekly_alignment=weekly_alignment,
        breakout_level=breakout_level,
        breakout_confirmed=breakout_confirmed,
        breakout_watch=breakout_watch,
        pullback_support=support,
        pullback_setup=pullback_setup,
        extended=extended,
        close=closes[-1],
        ema21=ema21,
        sma50=sma50,
        sma200=sma200,
        rejection_reasons=rejection_reasons,
    )
