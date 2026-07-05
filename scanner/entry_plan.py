from __future__ import annotations

from math import ceil

from scanner.models import CommandResult, EntryPlan, MomentumResult

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


def research_call_strike(trigger: float, target: float) -> float:
    """Return an OTM research strike halfway between trigger and target, rounded UP.

    Research strike only. It must be validated against a 0.25-0.35 absolute
    delta band in the broker before entry; the delta band is primary and the
    computed strike is a sanity check.
    """
    raw = trigger + 0.5 * (target - trigger)
    increment = _strike_increment(raw)
    return round(ceil(raw / increment) * increment, 2)


def build_entry_plan(command: CommandResult, four_hour: MomentumResult) -> EntryPlan:
    trigger = max(command.breakout_level, four_hour.trigger)
    support = max(min(command.pullback_support, four_hour.support), 0.01)
    invalidation = min(support, four_hour.warning)
    nearest_resistance = max(trigger + (command.close - support) * 2, trigger + 0.01)
    target_price = nearest_resistance
    target_gain_percent = ((target_price - command.close) / command.close) * 100
    distance_to_trigger = trigger - command.close
    distance_to_support = command.close - support
    risk = command.close - invalidation
    reward = nearest_resistance - command.close
    reward_to_risk = reward / risk if risk > 0 else None
    if command.pullback_setup:
        status = "valid now"
        mode = "pullback"
    elif command.close >= trigger:
        status = "valid now"
        mode = "breakout"
    elif distance_to_trigger <= max(command.close * 0.01, 0.01):
        status = "approaching"
        mode = "breakout"
    else:
        status = "waiting"
        mode = "pullback" if command.pullback_setup else "breakout"
    return EntryPlan(
        entry_mode=mode,
        trigger=trigger,
        support=support,
        invalidation=invalidation,
        nearest_resistance=nearest_resistance,
        target_price=target_price,
        target_gain_percent=target_gain_percent,
        research_call_strike=research_call_strike(trigger, target_price),
        preferred_dte_minimum=PREFERRED_DTE_MINIMUM,
        preferred_dte_maximum=PREFERRED_DTE_MAXIMUM,
        intended_hold_days_minimum=INTENDED_HOLD_DAYS_MINIMUM,
        intended_hold_days_maximum=INTENDED_HOLD_DAYS_MAXIMUM,
        distance_to_trigger=distance_to_trigger,
        distance_to_support=distance_to_support,
        reward_to_risk=reward_to_risk,
        status=status,
    )
