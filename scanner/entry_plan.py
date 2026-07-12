from __future__ import annotations

from math import floor

from scanner.models import CommandResult, EntryPlan, MomentumResult
from scanner.strategy_profile import PROFILE

PREFERRED_DTE_MINIMUM = PROFILE.preferred_dte_minimum
PREFERRED_DTE_MAXIMUM = PROFILE.preferred_dte_maximum
INTENDED_HOLD_DAYS_MINIMUM = PROFILE.intended_hold_days_minimum
INTENDED_HOLD_DAYS_MAXIMUM = PROFILE.intended_hold_days_maximum


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


def research_call_strike(reference_price: float, target: float | None = None) -> float:
    """Return a near-the-money research strike for broker-chain validation.

    The live 0.45-0.65 delta band is primary. Rounding down keeps the research
    strike near or slightly in the money instead of assuming an explosive move.
    ``target`` remains accepted for compatibility with older callers.
    """
    increment = _strike_increment(reference_price)
    return round(floor(reference_price / increment) * increment, 2)


def build_entry_plan(command: CommandResult, four_hour: MomentumResult) -> EntryPlan:
    if command.pullback_setup:
        support = max(command.pullback_support, four_hour.support, 0.01)
    else:
        support = max(min(command.pullback_support, four_hour.support), 0.01)
    trigger = four_hour.trigger if command.pullback_setup else max(command.breakout_level, four_hour.trigger)
    atr_value = command.close * command.atr_percent / 100
    invalidation = max(support - (0.20 * atr_value), 0.01)
    structural_target = command.resistance_level
    risk = command.close - invalidation
    minimum_objective = max(command.close + (2 * risk), trigger + 0.01)
    structural_reward = structural_target - command.close
    if structural_target > max(command.close, trigger) and structural_reward >= 1.5 * risk:
        target_price = structural_target
        target_basis = "confirmed daily pivot resistance"
    else:
        target_price = minimum_objective
        target_basis = "2R planning objective; verify the path through nearby resistance"
    target_gain_percent = ((target_price - command.close) / command.close) * 100
    distance_to_trigger = trigger - command.close
    distance_to_support = command.close - support
    reward = target_price - command.close
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
        resistance_level=structural_target,
        target_price=target_price,
        target_basis=target_basis,
        target_gain_percent=target_gain_percent,
        research_call_strike=research_call_strike(command.close),
        preferred_dte_minimum=PREFERRED_DTE_MINIMUM,
        preferred_dte_maximum=PREFERRED_DTE_MAXIMUM,
        intended_hold_days_minimum=INTENDED_HOLD_DAYS_MINIMUM,
        intended_hold_days_maximum=INTENDED_HOLD_DAYS_MAXIMUM,
        distance_to_trigger=distance_to_trigger,
        distance_to_support=distance_to_support,
        reward_to_risk=reward_to_risk,
        status=status,
    )
