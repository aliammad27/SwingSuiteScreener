"""Movement-capability filter (aggressive contract profile v2).

A short-dated OTM contract only works when the underlying can realistically
travel from the current close, past the research strike, and on toward the
target within the hold window. Candidates that fail either check cannot be
S tier or A Plus; they may still appear as B tier / watch.
"""

from __future__ import annotations

PREMIUM_CUSHION_PERCENT = 1.0
TARGET_GAIN_MULTIPLE = 1.5
ATR_PERCENT_FLOOR = 2.0

INSUFFICIENT_MOVEMENT = "insufficient_movement_capability"
ATR_BELOW_FLOOR = "atr_percent_below_floor"


def required_move_percent(close: float, research_strike: float, *, bearish: bool = False) -> float:
    """Percent move from close to the research strike plus a premium cushion.

    Calls measure close up to strike; puts measure close down to strike. When
    price has already passed the strike the raw move clamps at zero, leaving
    only the cushion.
    """
    if bearish:
        raw = (close - research_strike) / close * 100
    else:
        raw = (research_strike - close) / close * 100
    return max(raw, 0.0) + PREMIUM_CUSHION_PERCENT


def movement_filter_reasons(
    close: float,
    research_strike: float,
    target_gain_percent: float,
    atr_percent: float,
    *,
    bearish: bool = False,
) -> list[str]:
    """Return rejection reason codes when the movement-capability filter fails."""
    reasons: list[str] = []
    required = required_move_percent(close, research_strike, bearish=bearish)
    if target_gain_percent < TARGET_GAIN_MULTIPLE * required:
        reasons.append(INSUFFICIENT_MOVEMENT)
    if atr_percent < ATR_PERCENT_FLOOR:
        reasons.append(ATR_BELOW_FLOOR)
    return reasons
