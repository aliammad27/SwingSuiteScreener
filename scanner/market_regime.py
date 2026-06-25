from __future__ import annotations

from scanner.daily_command import calculate_command
from scanner.models import Candle


def classify_market_regime(
    spy_daily: list[Candle], qqq_daily: list[Candle], weekly: list[Candle]
) -> str:
    spy = calculate_command("SPY", spy_daily, spy_daily, weekly)
    qqq = calculate_command("QQQ", qqq_daily, qqq_daily, weekly)
    strong = sum(1 for item in [spy, qqq] if item.trend == "Uptrend" and item.score >= 70)
    if strong == 2:
        return "Supportive"
    if strong == 1:
        return "Mixed"
    return "Hostile"
