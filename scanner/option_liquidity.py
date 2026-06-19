from __future__ import annotations

from scanner.models import OptionQuote


def classify_option_liquidity(quotes: list[OptionQuote]) -> str:
    if not quotes:
        return "Unknown"
    best = min(quotes, key=lambda q: abs(q.dte - 38) + abs(q.delta - 0.55) * 100)
    mid = (best.bid + best.ask) / 2
    if mid <= 0:
        return "Poor"
    spread_pct = ((best.ask - best.bid) / mid) * 100
    requirements = [
        30 <= best.dte <= 60,
        0.45 <= best.delta <= 0.65,
        spread_pct <= 10,
        best.open_interest >= 500,
        best.volume >= 100,
        best.implied_volatility_rank is None or best.implied_volatility_rank <= 70,
    ]
    if all(requirements):
        return "Good"
    misses = sum(1 for req in requirements if not req)
    if misses == 1:
        near = (
            24 <= best.dte <= 72
            and 0.36 <= best.delta <= 0.78
            and spread_pct <= 12
            and best.open_interest >= 400
            and best.volume >= 80
        )
        return "Acceptable" if near else "Poor"
    return "Poor"
