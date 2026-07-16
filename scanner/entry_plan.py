from __future__ import annotations

from scanner.models import (
    EntryPlan,
    PatternSignal,
    PatternStatus,
    TimingAnalysis,
    TrendAnalysis,
)
from scanner.strategy_profile import LaneProfile


def build_entry_plan(
    trend: TrendAnalysis,
    pattern: PatternSignal,
    timing: TimingAnalysis,
    lane: LaneProfile,
) -> EntryPlan:
    trigger = pattern.trigger
    invalidation = max(pattern.invalidation, 0.01)
    support = max(trend.pullback_support, invalidation)
    risk = trend.close - invalidation
    planning_objective = trend.close + max(2 * risk, 0.01)
    confirmed_pivot = (
        trend.resistance_level
        if trend.resistance_level is not None
        and trend.resistance_level > trend.close
        else None
    )
    pivot_reward_to_risk = (
        (confirmed_pivot - trend.close) / risk
        if confirmed_pivot is not None and risk > 0
        else None
    )
    if confirmed_pivot is not None and (pivot_reward_to_risk or 0.0) >= 1.5:
        target = confirmed_pivot
        target_basis = "nearest confirmed daily pivot"
    else:
        target = planning_objective
        target_basis = (
            "2R planning objective; review path through nearest confirmed daily pivot"
            if confirmed_pivot is not None
            else "2R planning objective; no confirmed overhead daily pivot"
        )
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
        tactical_warning=timing.tactical_warning,
        tactical_failure=timing.tactical_failure,
        resistance_level=trend.resistance_level,
        planning_objective_2r=planning_objective,
        target_price=target,
        target_basis=target_basis,
        target_gain_percent=target_gain_percent,
        distance_to_trigger=trigger - trend.close,
        distance_to_support=trend.close - support,
        reward_to_risk=reward_to_risk,
        status=status,
        intended_hold_sessions=lane.intended_hold_sessions,
        requalify_dte=lane.requalify_dte,
        no_progress_sessions=lane.no_progress_sessions,
    )
