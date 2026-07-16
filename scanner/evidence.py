from __future__ import annotations

from math import log, sqrt
from statistics import pstdev

from scanner.indicators import anchored_vwap, atr, ema, sma
from scanner.models import Candle, TrendAnalysis
from scanner.strategy_profile import StrategyProfile
from scanner.structure import (
    classify_structure,
    confirmed_pivot_highs,
    confirmed_pivot_lows,
    nearest_support_below,
)


def analyze_trend(
    daily: list[Candle],
    weekly: list[Candle],
    profile: StrategyProfile,
) -> TrendAnalysis:
    if len(daily) < 220 or len(weekly) < 30:
        raise ValueError("Trend analysis requires 220 daily bars and 30 weekly bars.")
    closes = [candle.close for candle in daily]
    highs = [candle.high for candle in daily]
    lows = [candle.low for candle in daily]
    volumes = [candle.volume for candle in daily]
    ema21 = ema(closes, 21)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    sma200_previous = sum(closes[-210:-10]) / 200
    current_atr = atr(highs, lows, closes, 14)
    vwap = anchored_vwap(highs, lows, closes, volumes, max(0, len(closes) - 21))
    weekly_ema21 = ema([candle.close for candle in weekly], 21)
    weekly_aligned = weekly[-1].close > weekly_ema21
    structure = classify_structure(highs, lows, 5, 3)
    volume_average = sma([float(volume) for volume in volumes], 20)
    relative_volume = volumes[-1] / volume_average if volume_average > 0 else 0.0

    breakout_level = max(highs[-21:-1])
    breakout_confirmed = daily[-2].close <= breakout_level < daily[-1].close
    pivot_lows = confirmed_pivot_lows(lows, 5, 3)
    latest_pivot_low = pivot_lows[-1][1] if pivot_lows else min(lows[-20:])
    support = nearest_support_below(daily[-1].close, [ema21, sma50, vwap, latest_pivot_low])
    pullback_touched = daily[-1].low <= support + (0.30 * current_atr)
    pullback_held = daily[-1].close > support and daily[-1].close >= daily[-1].open
    pullback_setup = pullback_touched and pullback_held
    pivot_highs = confirmed_pivot_highs(highs, 5, 3)
    overhead = [value for _, value in pivot_highs if value > daily[-1].close]
    resistance = min(overhead) if overhead else None
    extended = daily[-1].close > breakout_level + (
        profile.maximum_confirmed_extension_atr * current_atr
    )

    score = 0
    score += 15 if closes[-1] > ema21 else 0
    score += 15 if ema21 > sma50 else 0
    score += 10 if closes[-1] > sma50 else 0
    score += 20 if sma50 > sma200 else 0
    score += 15 if closes[-1] > sma200 else 0
    score += 10 if sma200 > sma200_previous else 0
    score += 15 if weekly_aligned else 0
    failures: list[str] = []
    if closes[-1] < sma200:
        failures.append("below_sma200")
    if extended:
        failures.append("extended_beyond_configured_atr_limit")
    return TrendAnalysis(
        score=min(score, 100),
        close=closes[-1],
        ema21=ema21,
        sma50=sma50,
        sma200=sma200,
        anchored_vwap=vwap,
        atr=current_atr,
        atr_percent=(current_atr / closes[-1]) * 100,
        weekly_aligned=weekly_aligned,
        structure=structure,
        relative_volume=relative_volume,
        breakout_level=breakout_level,
        breakout_confirmed=breakout_confirmed,
        pullback_support=support,
        pullback_setup=pullback_setup,
        resistance_level=resistance,
        extended=extended,
        hard_failures=tuple(failures),
    )


def _relative_ratio(closes: list[float], benchmark: list[float]) -> list[float]:
    length = min(len(closes), len(benchmark))
    return [
        stock / peer
        for stock, peer in zip(closes[-length:], benchmark[-length:], strict=True)
        if peer > 0
    ]


def calculate_leadership(
    stock_daily: list[Candle], peer_daily: list[Candle], spy_daily: list[Candle]
) -> int:
    stock = [candle.close for candle in stock_daily]
    peer = [candle.close for candle in peer_daily]
    spy = [candle.close for candle in spy_daily]
    if min(len(stock), len(peer), len(spy)) < 64:
        raise ValueError("Leadership analysis requires at least 64 daily bars.")
    stock_peer = _relative_ratio(stock, peer)
    peer_spy = _relative_ratio(peer, spy)
    score = 0
    if stock_peer[-1] > ema(stock_peer, 21) and stock_peer[-1] > stock_peer[-6]:
        score += 50
    elif stock_peer[-1] > ema(stock_peer, 21) or stock_peer[-1] > stock_peer[-6]:
        score += 25
    if peer_spy[-1] > ema(peer_spy, 21) and peer_spy[-1] > peer_spy[-6]:
        score += 25
    elif peer_spy[-1] > ema(peer_spy, 21) or peer_spy[-1] > peer_spy[-6]:
        score += 12
    stock_return = (stock[-1] / stock[-64]) - 1
    peer_return = (peer[-1] / peer[-64]) - 1
    if stock_return >= peer_return + 0.03:
        score += 50
    elif stock_return > peer_return:
        score += 25
    return min(score, 100)


def annualized_realized_volatility(candles: list[Candle], lookback: int = 20) -> float | None:
    closes = [candle.close for candle in candles]
    if len(closes) < lookback + 1:
        return None
    returns = [
        log(current / previous)
        for previous, current in zip(closes[-lookback - 1 : -1], closes[-lookback:], strict=True)
        if previous > 0 and current > 0
    ]
    if len(returns) < 2:
        return None
    return pstdev(returns) * sqrt(252)
