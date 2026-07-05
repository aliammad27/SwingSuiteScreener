from __future__ import annotations

from scanner.models import OptionQuote

# Aggressive contract profile v2: 14-21 DTE, 0.25-0.35 absolute delta.
DELTA_HARD_FLOOR = 0.20
DTE_TARGET_CENTER = 17.5
DELTA_TARGET_CENTER = 0.30


def classify_option_liquidity(quotes: list[OptionQuote]) -> str:
    if not quotes:
        return "Unknown"
    best = min(
        quotes,
        key=lambda q: abs(q.dte - DTE_TARGET_CENTER) + abs(q.delta - DELTA_TARGET_CENTER) * 100,
    )
    if abs(best.delta) < DELTA_HARD_FLOOR:
        return "Poor"
    mid = (best.bid + best.ask) / 2
    if mid <= 0:
        return "Poor"
    spread_pct = ((best.ask - best.bid) / mid) * 100
    requirements = [
        14 <= best.dte <= 21,
        0.25 <= best.delta <= 0.35,
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
            10 <= best.dte <= 25
            and 0.20 <= best.delta <= 0.42
            and spread_pct <= 12
            and best.open_interest >= 400
            and best.volume >= 80
        )
        return "Acceptable" if near else "Poor"
    return "Poor"


def classify_put_option_liquidity(quotes: list[OptionQuote]) -> str:
    """Classify option liquidity for put contracts.

    Targets puts with absolute delta 0.25 to 0.35 and 14-21 DTE (aggressive v2).
    Falls back to absolute-delta heuristic when no negative-delta quotes are present.
    """
    put_quotes = [q for q in quotes if q.delta < 0]
    if not put_quotes:
        if not quotes:
            return "Unknown"
        best = min(
            quotes,
            key=lambda q: abs(q.dte - DTE_TARGET_CENTER)
            + abs(abs(q.delta) - DELTA_TARGET_CENTER) * 100,
        )
    else:
        best = min(
            put_quotes,
            key=lambda q: abs(q.dte - DTE_TARGET_CENTER)
            + abs(abs(q.delta) - DELTA_TARGET_CENTER) * 100,
        )
    abs_delta = abs(best.delta)
    if abs_delta < DELTA_HARD_FLOOR:
        return "Poor"
    mid = (best.bid + best.ask) / 2
    if mid <= 0:
        return "Poor"
    spread_pct = ((best.ask - best.bid) / mid) * 100
    requirements = [
        14 <= best.dte <= 21,
        0.25 <= abs_delta <= 0.35,
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
            10 <= best.dte <= 25
            and 0.20 <= abs_delta <= 0.42
            and spread_pct <= 12
            and best.open_interest >= 400
            and best.volume >= 80
        )
        return "Acceptable" if near else "Poor"
    return "Poor"
