from __future__ import annotations

from scanner.models import (
    ContractSelection,
    DataTrust,
    EntryPlan,
    EventRisk,
    EventRiskStatus,
    EvidenceScores,
    MarketContext,
    PatternSignal,
    PatternStatus,
    ReviewState,
    StrategyLane,
    TimingAnalysis,
    TrendAnalysis,
)
from scanner.strategy_profile import StrategyProfile


def calculate_risk_score(
    trend: TrendAnalysis,
    pattern: PatternSignal,
    entry: EntryPlan,
    event: EventRisk,
    profile: StrategyProfile,
) -> int:
    reward_to_risk = entry.reward_to_risk or 0.0
    geometry = (
        30
        if reward_to_risk >= 2
        else 22
        if reward_to_risk >= 1.5
        else 10
        if reward_to_risk >= 1
        else 0
    )
    extension = 25 if not trend.extended and pattern.status != PatternStatus.STALE else 0
    recency = (
        15
        if pattern.status in {PatternStatus.FORMING, PatternStatus.READY}
        or pattern.age_bars <= profile.maximum_confirmed_age_bars
        else 0
    )
    event_score = {
        EventRiskStatus.CLEAR: 20,
        EventRiskStatus.UNKNOWN: 0,
        EventRiskStatus.BLOCKED: 0,
    }[event.status]
    data_quality = 10
    return min(geometry + extension + recency + event_score + data_quality, 100)


def chart_qualification_failures(
    *,
    lane: StrategyLane,
    scores: EvidenceScores,
    trend: TrendAnalysis,
    pattern: PatternSignal,
    timing: TimingAnalysis,
    market: MarketContext,
    profile: StrategyProfile,
) -> tuple[str, ...]:
    failures = list(trend.hard_failures)
    if market.regime == "Hostile":
        failures.append("hostile_market_regime")
    if pattern.pattern_type not in profile.production_patterns:
        failures.append("pattern_not_promoted_for_production")
    if pattern.status == PatternStatus.FAILED:
        failures.append("pattern_failed")
    if pattern.status == PatternStatus.STALE:
        failures.append("pattern_stale")
    if failures:
        return tuple(sorted(set(failures)))

    thresholds = profile.thresholds
    requirements = {
        "trend_below_ready_threshold": scores.trend >= thresholds.trend,
        "setup_below_ready_threshold": scores.setup >= thresholds.setup,
        "pattern_not_ready": pattern.status
        in {PatternStatus.READY, PatternStatus.CONFIRMED},
        "timing_below_ready_threshold": scores.timing >= thresholds.timing,
        "hourly_timing_not_confirmed": timing.bullish_confirmation,
        "market_below_ready_threshold": scores.market >= thresholds.market,
        "risk_below_ready_threshold": scores.risk >= thresholds.risk,
    }
    if lane == StrategyLane.LEADER_WEEKLY:
        requirements["leadership_below_ready_threshold"] = (
            scores.leadership is not None
            and scores.leadership >= thresholds.leadership
        )
    return tuple(
        reason for reason, passed in requirements.items() if not passed
    )


def technical_qualification_failures(
    *,
    lane: StrategyLane,
    scores: EvidenceScores,
    trend: TrendAnalysis,
    pattern: PatternSignal,
    timing: TimingAnalysis,
    market: MarketContext,
    event: EventRisk,
    profile: StrategyProfile,
) -> tuple[str, ...]:
    failures = list(
        chart_qualification_failures(
            lane=lane,
            scores=scores,
            trend=trend,
            pattern=pattern,
            timing=timing,
            market=market,
            profile=profile,
        )
    )
    if event.status == EventRiskStatus.BLOCKED:
        failures.append("event_risk_blocked")
    if event.status == EventRiskStatus.UNKNOWN:
        failures.append("event_risk_unknown_fail_closed")
    return tuple(sorted(set(failures)))


def classify_candidate(
    *,
    lane: StrategyLane,
    scores: EvidenceScores,
    trend: TrendAnalysis,
    pattern: PatternSignal,
    timing: TimingAnalysis,
    market: MarketContext,
    event: EventRisk,
    contracts: ContractSelection,
    data_trust: DataTrust,
    profile: StrategyProfile,
) -> tuple[ReviewState, tuple[str, ...]]:
    chart_failures = technical_qualification_failures(
        lane=lane,
        scores=scores,
        trend=trend,
        pattern=pattern,
        timing=timing,
        market=market,
        event=event,
        profile=profile,
    )
    if not chart_failures:
        if contracts.primary is None:
            return ReviewState.VERIFY_CONTRACT, contracts.rejection_reasons or (
                "no_eligible_call_contract",
            )
        if not data_trust.event_trusted:
            return ReviewState.REJECTED, data_trust.reasons or (
                "event_data_not_trusted",
            )
        if not data_trust.stock_trusted or not data_trust.option_trusted:
            return ReviewState.VERIFY_CONTRACT, data_trust.reasons or (
                "live_data_requires_verification",
            )
        if scores.contract >= profile.thresholds.contract:
            if profile.validation_state == "research_default":
                return ReviewState.READY_VERIFY, (
                    "research_validation_required",
                )
            return ReviewState.READY, ()
        if scores.contract >= profile.thresholds.ready_verify_contract_minimum:
            return ReviewState.READY_VERIFY, (
                "contract_score_requires_verification",
            )
        return ReviewState.REJECTED, contracts.rejection_reasons or (
            "contract_score_below_minimum",
        )

    hard_failures = {
        "below_sma200",
        "extended_beyond_configured_atr_limit",
        "hostile_market_regime",
        "event_risk_blocked",
        "event_risk_unknown_fail_closed",
        "pattern_failed",
        "pattern_stale",
        "pattern_not_promoted_for_production",
    }
    if any(reason in hard_failures for reason in chart_failures):
        return ReviewState.REJECTED, chart_failures
    bullish_development = (
        scores.trend >= 60
        and market.regime != "Hostile"
        and pattern.status
        in {PatternStatus.FORMING, PatternStatus.READY, PatternStatus.CONFIRMED}
    )
    if bullish_development:
        return ReviewState.DEVELOPING, chart_failures
    return ReviewState.REJECTED, chart_failures or (
        "bullish_structure_not_qualified",
    )
