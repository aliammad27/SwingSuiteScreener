from __future__ import annotations

from scanner.indicators import anchored_vwap, atr, bollinger, ema, sma
from scanner.models import Candle, PutCommandResult
from scanner.structure import (
    classify_structure,
    confirmed_pivot_highs,
    nearest_resistance_above,
)


def _relative_weakness(stock_closes: list[float], benchmark_closes: list[float]) -> str:
    """Classify relative weakness versus benchmark.

    Leading = stock falling faster than benchmark (best for puts).
    Strong = stock below its RS average but not accelerating down.
    Improving = RS ratio beginning to fall (stock weakening).
    Lagging = stock actually outperforming (bad for puts).
    """
    ratios = [
        s / b
        for s, b in zip(stock_closes[-len(benchmark_closes) :], benchmark_closes, strict=True)
    ]
    avg = ema(ratios, 21)
    falling = ratios[-1] < ratios[-6]
    if ratios[-1] < avg and falling:
        return "Leading"
    if ratios[-1] < avg:
        return "Strong"
    if falling:
        return "Improving"
    return "Lagging"


def calculate_put_command(
    symbol: str,
    daily: list[Candle],
    benchmark_daily: list[Candle],
    weekly: list[Candle],
) -> PutCommandResult:
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
    _, _, lower_band, width = bollinger(closes, 20, 2)
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
    below_vwap = closes[-1] < vwap

    rw = _relative_weakness(closes, benchmark_closes)
    rel_volume = volumes[-1] / sma([float(v) for v in volumes], 20)
    bearish_candle = closes[-1] < daily[-1].open
    if rel_volume >= 1.30:
        volume_state = "Expansion"
    elif rel_volume >= 1.0:
        volume_state = "Above average"
    elif rel_volume >= 0.70:
        volume_state = "Normal"
    else:
        volume_state = "Light"

    structure = classify_structure(highs, lows, 5, 3)

    # Weekly bearish alignment: close below weekly EMA 21
    weekly_ema21 = ema([c.close for c in weekly], 21)
    weekly_alignment = weekly[-1].close < weekly_ema21

    # Breakdown level: lowest low of previous 20 completed daily bars (excluding current)
    breakdown_level = min(lows[-21:-1])
    breakdown_confirmed = daily[-2].close >= breakdown_level > closes[-1]
    breakdown_watch = (
        closes[-1] > breakdown_level and closes[-1] - breakdown_level <= 0.5 * current_atr
    )

    # Rejection setup: price near overhead resistance then rejected lower
    pivot_highs = confirmed_pivot_highs(highs, 5, 3)
    latest_pivot_high = pivot_highs[-1][1] if pivot_highs else max(highs[-20:])
    rejection_resistance = nearest_resistance_above(
        closes[-1], [ema21, sma50, vwap, latest_pivot_high]
    )
    rejection_touched = daily[-1].high >= rejection_resistance - (0.30 * current_atr)
    rejection_fell = closes[-1] < rejection_resistance and closes[-1] <= daily[-1].open
    rejection_setup = rejection_touched and rejection_fell

    # Extended downside: already far below lower Bollinger Band — avoid new put entries
    extended_downside = closes[-1] < lower_band and (ema21 - closes[-1]) > (1.50 * current_atr)

    score = 0
    score += 10 if closes[-1] < ema21 else 0
    score += 10 if ema21 < sma50 else 0
    score += 10 if closes[-1] < sma50 else 0
    score += 15 if sma50 < sma200 else 0
    score += 10 if closes[-1] < sma200 else 0
    score += 5 if sma200 < sma200_prev else 0
    score += 15 if rw == "Leading" else 8 if rw == "Strong" else 0
    score += 10 if below_vwap else 0
    score += (
        10 if volume_state == "Expansion" and bearish_candle else 5 if rel_volume >= 1 else 0
    )
    score += 5 if structure == "Bearish" else 3 if structure == "Mixed" else 0
    score += 5 if weekly_alignment else 0

    trend = (
        "Downtrend"
        if closes[-1] < ema21 and ema21 < sma50 and sma50 < sma200
        else "Weak bearish"
    )

    if closes[-1] > sma200 or score < 45:
        put_bias = "Avoid"
    elif extended_downside:
        put_bias = "Extended downside"
    elif breakdown_confirmed and score >= 70 and rel_volume >= 1.0:
        put_bias = "Breakdown confirmed"
    elif score >= 70 and rejection_setup:
        put_bias = "Rejection setup"
    elif breakdown_watch and score >= 65:
        put_bias = "Breakdown watch"
    elif score >= 75:
        put_bias = "Bearish"
    elif score >= 60:
        put_bias = "Put watch"
    else:
        put_bias = "Mixed"

    rejection_reasons: list[str] = []
    if closes[-1] > sma200:
        rejection_reasons.append("above_sma200")
    if score < 60:
        rejection_reasons.append("put_command_score_below_60")
    if extended_downside:
        rejection_reasons.append("extended_downside")

    return PutCommandResult(
        symbol=symbol,
        score=min(score, 100),
        put_bias=put_bias,
        trend=trend,
        relative_weakness=rw,
        relative_volume=rel_volume,
        volume_state=volume_state,
        volatility_state=volatility_state,
        structure=structure,
        below_vwap=below_vwap,
        anchored_vwap=vwap,
        weekly_alignment=weekly_alignment,
        breakdown_level=breakdown_level,
        breakdown_confirmed=breakdown_confirmed,
        breakdown_watch=breakdown_watch,
        rejection_resistance=rejection_resistance,
        rejection_setup=rejection_setup,
        extended_downside=extended_downside,
        close=closes[-1],
        ema21=ema21,
        sma50=sma50,
        sma200=sma200,
        atr_percent=atr_percent,
        rejection_reasons=rejection_reasons,
    )
