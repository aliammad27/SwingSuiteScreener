from __future__ import annotations

from scanner.models import OptionQuote
from scanner.strategy_profile import PROFILE

# Bullish Participation v3 uses more time and more directional exposure.
DELTA_HARD_FLOOR = PROFILE.delta_hard_floor
DTE_TARGET_CENTER = (PROFILE.preferred_dte_minimum + PROFILE.preferred_dte_maximum) / 2
DELTA_TARGET_CENTER = (PROFILE.preferred_delta_minimum + PROFILE.preferred_delta_maximum) / 2


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
        PROFILE.preferred_dte_minimum <= best.dte <= PROFILE.preferred_dte_maximum,
        PROFILE.preferred_delta_minimum <= best.delta <= PROFILE.preferred_delta_maximum,
        spread_pct <= PROFILE.maximum_spread_percent,
        best.open_interest >= PROFILE.minimum_open_interest,
        best.volume >= PROFILE.minimum_contract_volume,
        best.implied_volatility_rank is None or best.implied_volatility_rank <= PROFILE.maximum_iv_rank,
    ]
    if all(requirements):
        return "Good"
    misses = sum(1 for req in requirements if not req)
    if misses == 1:
        near = (
            PROFILE.hard_dte_minimum <= best.dte <= PROFILE.hard_dte_maximum
            and PROFILE.delta_hard_floor <= best.delta <= 0.72
            and spread_pct <= PROFILE.maximum_spread_percent + 2
            and best.open_interest >= int(PROFILE.minimum_open_interest * 0.8)
            and best.volume >= int(PROFILE.minimum_contract_volume * 0.8)
        )
        return "Acceptable" if near else "Poor"
    return "Poor"


def classify_put_option_liquidity(quotes: list[OptionQuote]) -> str:
    """Classify option liquidity for put contracts.

    Targets puts with absolute delta 0.25 to 0.35 and 14-21 DTE (aggressive v2).
    Falls back to absolute-delta heuristic when no negative-delta quotes are present.
    """
    legacy_dte_center = 17.5
    legacy_delta_center = 0.30
    put_quotes = [q for q in quotes if q.delta < 0]
    if not put_quotes:
        if not quotes:
            return "Unknown"
        best = min(
            quotes,
            key=lambda q: abs(q.dte - legacy_dte_center)
            + abs(abs(q.delta) - legacy_delta_center) * 100,
        )
    else:
        best = min(
            put_quotes,
            key=lambda q: abs(q.dte - legacy_dte_center)
            + abs(abs(q.delta) - legacy_delta_center) * 100,
        )
    abs_delta = abs(best.delta)
    if abs_delta < 0.20:
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
