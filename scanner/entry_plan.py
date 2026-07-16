from __future__ import annotations

from scanner.models import EntryPlan, PatternSignal, PatternStatus, TrendAnalysis
from scanner.strategy_profile import LaneProfile


def build_entry_plan(
    trend: TrendAnalysis,
    pattern: PatternSignal,
    lane: LaneProfile,
) -> EntryPlan:
    trigger = pattern.trigger
    invalidation = max(pattern.invalidation, 0.01)
    support = max(trend.pullback_support, invalidation)
    target = max(pattern.target, trigger + 0.01)
    risk = trend.close - invalidation
    reward = target - trend.close
    reward_to_risk = reward / risk if risk > 0 else None
    target_gain_percent = ((target - trend.close) / trend.close) * 100
    status = {
        PatternStatus.CONFIRMED: "valid now",
        PatternStatus.READY: "approaching",
        PatternStatus.FORMING: "waiting",
        PatternStatus.STALE: "stale",
        PatternStatus.FAILED: "invalidated",
    }[pattern.status]
    return EntryPlan(
        entry_mode=pattern.pattern_type,
        trigger=trigger,
        support=support,
        invalidation=invalidation,
        resistance_level=trend.resistance_level,
        target_price=target,
        target_basis=f"{pattern.pattern_type.replace('_', ' ')} measured objective",
        target_gain_percent=target_gain_percent,
        distance_to_trigger=trigger - trend.close,
        distance_to_support=trend.close - support,
        reward_to_risk=reward_to_risk,
        status=status,
        intended_hold_sessions=lane.intended_hold_sessions,
        requalify_dte=lane.requalify_dte,
    )
