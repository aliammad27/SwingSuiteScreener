from __future__ import annotations

from scanner.indicators import ema, sma
from scanner.models import Candle, MarketContext
from scanner.providers.base import MarketDataProvider
from scanner.strategy_profile import StrategyProfile


def classify_market_regime(score: int, profile: StrategyProfile) -> str:
    if score >= profile.supportive_market_minimum:
        return "Supportive"
    if score >= profile.mixed_market_minimum:
        return "Mixed"
    return "Hostile"


def _daily_trend_pass(candles: list[Candle]) -> bool:
    closes = [candle.close for candle in candles]
    if len(closes) < 210:
        return False
    current_sma50 = sma(closes, 50)
    current_sma200 = sma(closes, 200)
    prior_sma200 = sum(closes[-210:-10]) / 200
    return closes[-1] > current_sma50 > current_sma200 and current_sma200 > prior_sma200


def _weekly_pass(candles: list[Candle]) -> bool:
    closes = [candle.close for candle in candles]
    return len(closes) >= 21 and closes[-1] > ema(closes, 21)


def calculate_market_context(
    market: MarketDataProvider,
    breadth_symbols: list[str],
    profile: StrategyProfile,
) -> MarketContext:
    spy_daily = market.daily("SPY")
    qqq_daily = market.daily("QQQ")
    spy_pass = _daily_trend_pass(spy_daily)
    qqq_pass = _daily_trend_pass(qqq_daily)
    weekly_alignment = _weekly_pass(market.weekly("SPY")) and _weekly_pass(
        market.weekly("QQQ")
    )
    above_50 = 0
    above_21 = 0
    valid = 0
    for symbol in breadth_symbols:
        candles = market.daily(symbol)
        closes = [candle.close for candle in candles]
        if len(closes) < 50:
            continue
        valid += 1
        above_50 += int(closes[-1] > sma(closes, 50))
        above_21 += int(closes[-1] > ema(closes, 21))
    breadth_50 = (above_50 / valid * 100) if valid else 0.0
    breadth_21 = (above_21 / valid * 100) if valid else 0.0
    components = {
        "spy_daily": 20 if spy_pass else 0,
        "qqq_daily": 20 if qqq_pass else 0,
        "weekly_alignment": 20 if weekly_alignment else 0,
        "breadth_above_sma50": round(20 * breadth_50 / 100),
        "breadth_above_ema21": round(20 * breadth_21 / 100),
    }
    score = min(sum(components.values()), 100)
    regime = classify_market_regime(score, profile)
    return MarketContext(
        score=score,
        regime=regime,
        spy_daily_pass=spy_pass,
        qqq_daily_pass=qqq_pass,
        weekly_alignment=weekly_alignment,
        breadth_above_sma50=breadth_50,
        breadth_above_ema21=breadth_21,
        breadth_symbol_count=valid,
        components=components,
    )
