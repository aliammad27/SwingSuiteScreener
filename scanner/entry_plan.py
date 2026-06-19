from __future__ import annotations

from scanner.models import CommandResult, EntryPlan, MomentumResult


def build_entry_plan(command: CommandResult, four_hour: MomentumResult) -> EntryPlan:
    trigger = max(command.breakout_level, four_hour.trigger)
    support = max(min(command.pullback_support, four_hour.support), 0.01)
    invalidation = min(support, four_hour.warning)
    nearest_resistance = max(trigger + (command.close - support) * 2, trigger + 0.01)
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
        distance_to_trigger=distance_to_trigger,
        distance_to_support=distance_to_support,
        reward_to_risk=reward_to_risk,
        status=status,
    )
