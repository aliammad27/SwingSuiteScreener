from __future__ import annotations

from math import floor

from scanner.models import MomentumResult, PutCommandResult, PutEntryPlan

PREFERRED_DTE_MINIMUM = 14
PREFERRED_DTE_MAXIMUM = 21
INTENDED_HOLD_DAYS_MINIMUM = 3
INTENDED_HOLD_DAYS_MAXIMUM = 7


def _strike_increment(price: float) -> float:
    if price < 25:
        return 0.5
    if price < 100:
        return 1.0
    if price < 250:
        return 2.5
    if price < 500:
        return 5.0
    return 10.0


def research_put_strike(trigger: float, target: float) -> float:
    """Return an OTM research strike halfway between trigger and target, rounded DOWN.

    Research strike only. It must be validated against a 0.25-0.35 absolute
    delta band in the broker before entry; the delta band is primary and the
    computed strike is a sanity check.
    """
    raw = trigger - 0.5 * (trigger - target)
    increment = _strike_increment(raw)
    return round(floor(raw / increment) * increment, 2)


def build_put_entry_plan(command: PutCommandResult, four_hour: MomentumResult) -> PutEntryPlan:
    """Build a put entry plan from bearish command and four-hour momentum results.

    four_hour.trigger = min(lows[-5:])  — recent 4H breakdown level
    four_hour.support = max(highs[-5:]) — recent 4H overhead resistance
    four_hour.warning = max(support, ema21) — level above that invalidates put
    """
    # Trigger: the level price must close below to enter the put
    # Use the higher of the two breakdown references (closer to current price = more conservative)
    trigger = max(command.breakdown_level, four_hour.trigger)

    # Resistance / invalidation: closest resistance above current price
    resistance = min(command.rejection_resistance, four_hour.support)
    invalidation = max(resistance, command.ema21)

    # Downside target: always project below current close.
    # For rejection setups or breakdowns where price already passed the trigger,
    # use the distance from trigger to close as the expected further move;
    # floor at 5% of close so the target is always meaningful.
    distance_past = abs(trigger - command.close)
    approach_distance = max(distance_past, command.close * 0.05)
    target_price = command.close - approach_distance
    # Hard floor: never project more than 22% below trigger
    target_price = max(target_price, trigger * 0.78)

    target_gain_percent = (command.close - target_price) / command.close * 100
    distance_to_trigger = command.close - trigger
    distance_to_resistance = resistance - command.close
    risk = invalidation - command.close
    reward = command.close - target_price
    reward_to_risk = reward / risk if risk > 0 else None

    if command.rejection_setup:
        status = "valid now"
        mode = "rejection"
    elif command.close <= trigger:
        status = "valid now"
        mode = "breakdown"
    elif distance_to_trigger <= max(command.close * 0.01, 0.01):
        status = "approaching"
        mode = "breakdown"
    else:
        status = "waiting"
        mode = "rejection" if command.rejection_setup else "breakdown"

    nearest_support = min(command.sma200, trigger * 0.92) if command.sma200 < trigger else trigger * 0.92

    return PutEntryPlan(
        entry_mode=mode,
        trigger=trigger,
        resistance=resistance,
        invalidation=invalidation,
        nearest_support=nearest_support,
        target_price=target_price,
        target_gain_percent=target_gain_percent,
        research_put_strike=research_put_strike(trigger, target_price),
        preferred_dte_minimum=PREFERRED_DTE_MINIMUM,
        preferred_dte_maximum=PREFERRED_DTE_MAXIMUM,
        intended_hold_days_minimum=INTENDED_HOLD_DAYS_MINIMUM,
        intended_hold_days_maximum=INTENDED_HOLD_DAYS_MAXIMUM,
        distance_to_trigger=distance_to_trigger,
        distance_to_resistance=distance_to_resistance,
        reward_to_risk=reward_to_risk,
        status=status,
    )
