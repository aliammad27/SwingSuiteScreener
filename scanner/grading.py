from __future__ import annotations

from datetime import datetime

from scanner.models import (
    ContractSelection,
    EntryPlan,
    EventRisk,
    EventRiskStatus,
    EvidenceScores,
    MarketContext,
    MomentumResult,
    PatternSignal,
    PatternStatus,
    ReviewState,
    StrategyLane,
    TrendAnalysis,
)
from scanner.strategy_profile import StrategyProfile


def event_is_inside_blackout(
    event: EventRisk, as_of: datetime, blackout_calendar_days: int
) -> bool:
    if event.earnings_date is None:
        return False
    days = (event.earnings_date - as_of.date()).days
    return 0 <= days <= blackout_calendar_days


def calculate_risk_score(
    trend: TrendAnalysis,
    pattern: PatternSignal,
    entry: EntryPlan,
    event: EventRisk,
) -> int:
    reward_to_risk = entry.reward_to_risk or 0.0
    geometry = 30 if reward_to_risk >= 2 else 22 if reward_to_risk >= 1.5 else 10 if reward_to_risk >= 1 else 0
    extension = 25 if not trend.extended and pattern.status != PatternStatus.STALE else 0
    recency = 15 if pattern.status in {PatternStatus.FORMING, PatternStatus.READY} or pattern.age_bars <= 3 else 0
    event_score = {
        EventRiskStatus.CLEAR: 20,
        EventRiskStatus.UNKNOWN: 10,
        EventRiskStatus.BLOCKED: 0,
    }[event.status]
    data_quality = 10
    return min(geometry + extension + recency + event_score + data_quality, 100)


def classify_candidate(
    *,
    lane: StrategyLane,
    scores: EvidenceScores,
    trend: TrendAnalysis,
    pattern: PatternSignal,
    four_hour: MomentumResult,
    market: MarketContext,
    event: EventRisk,
    contracts: ContractSelection,
    profile: StrategyProfile,
    as_of: datetime,
) -> tuple[ReviewState, tuple[str, ...]]:
    hard_failures = list(trend.hard_failures)
    if market.regime == "Hostile":
        hard_failures.append("hostile_market_regime")
    if event.status == EventRiskStatus.BLOCKED:
        hard_failures.append("event_risk_blocked")
    if event_is_inside_blackout(event, as_of, profile.earnings_blackout_calendar_days):
        hard_failures.append("earnings_inside_blackout")
    if pattern.status == PatternStatus.FAILED:
        hard_failures.append("pattern_failed")
    if pattern.status == PatternStatus.STALE:
        hard_failures.append("pattern_stale")
    if hard_failures:
        return ReviewState.REJECTED, tuple(sorted(set(hard_failures)))

    thresholds = profile.thresholds
    chart_requirements = {
        "trend_below_ready_threshold": scores.trend >= thresholds.trend,
        "setup_below_ready_threshold": scores.setup >= thresholds.setup,
        "pattern_not_ready": pattern.status in {PatternStatus.READY, PatternStatus.CONFIRMED},
        "momentum_below_ready_threshold": scores.momentum >= thresholds.momentum,
        "four_hour_not_confirmed": four_hour.bullish_confirmation,
        "market_below_ready_threshold": scores.market >= thresholds.market,
        "risk_below_ready_threshold": scores.risk >= thresholds.risk,
    }
    if lane == StrategyLane.LEADER_SWING:
        chart_requirements["leadership_below_ready_threshold"] = (
            scores.leadership is not None and scores.leadership >= thresholds.leadership
        )
    chart_failures = [reason for reason, passed in chart_requirements.items() if not passed]
    if not chart_failures:
        if not contracts.trustworthy:
            return ReviewState.VERIFY_CONTRACT, ("option_feed_not_opra",)
        if contracts.primary is None:
            return ReviewState.REJECTED, contracts.rejection_reasons or (
                "no_eligible_call_contract",
            )
        if (
            scores.contract >= thresholds.contract
            and event.status == EventRiskStatus.CLEAR
        ):
            return ReviewState.READY, ()
        if (
            scores.contract >= thresholds.ready_verify_contract_minimum
            and event.status in {EventRiskStatus.CLEAR, EventRiskStatus.UNKNOWN}
        ):
            reasons: list[str] = []
            if scores.contract < thresholds.contract:
                reasons.append("contract_score_requires_verification")
            if event.status == EventRiskStatus.UNKNOWN:
                reasons.append("event_calendar_requires_verification")
            return ReviewState.READY_VERIFY, tuple(reasons)
        return ReviewState.REJECTED, contracts.rejection_reasons or (
            "contract_score_below_minimum",
        )

    bullish_development = (
        scores.trend >= 60
        and market.regime != "Hostile"
        and pattern.status in {PatternStatus.FORMING, PatternStatus.READY, PatternStatus.CONFIRMED}
    )
    if bullish_development:
        return ReviewState.DEVELOPING, tuple(chart_failures)
    return ReviewState.REJECTED, tuple(chart_failures or ["bullish_structure_not_qualified"])
