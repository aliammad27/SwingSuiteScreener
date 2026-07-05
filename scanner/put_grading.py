from __future__ import annotations

from scanner.catalyst_research import catalyst_allows_primary_grade
from scanner.models import (
    Catalyst,
    Grade,
    MomentumResult,
    PutCandidate,
    PutCommandResult,
    PutEntryPlan,
)
from scanner.movement_filter import movement_filter_reasons


def automatic_put_rejections(
    command: PutCommandResult,
    daily_momentum: MomentumResult,
    four_hour: MomentumResult,
    option_liquidity: str,
    catalyst: Catalyst,
    market_regime: str,
    entry_plan: PutEntryPlan | None = None,
) -> list[str]:
    """Return reasons that automatically prevent a primary put grade.

    For puts, "Supportive" market regime = hostile to bears, "Hostile" = put-supportive.
    daily_momentum.macd_above_signal = True means MACD is below signal (bearish) in put context.
    """
    reasons = list(command.rejection_reasons)
    if command.score < 60:
        reasons.append("put_command_score_below_60")
    if option_liquidity == "Poor":
        reasons.append("options_illiquid")
    if market_regime == "Supportive":
        reasons.append("supportive_market_blocks_puts")
    if not catalyst.verified and catalyst.summary != "Technical continuation only":
        reasons.append("unverified_catalyst")
    if catalyst.major_event_risk:
        reasons.append("major_event_risk")
    # Four-hour warning without daily filter = unreliable bearish signal
    if not four_hour.daily_filter_passed and four_hour.score >= 70:
        reasons.append("bearish_daily_filter_blocked")
    if daily_momentum.state == "Warning active":
        reasons.append("daily_momentum_warning")
    if entry_plan is not None:
        reasons.extend(
            movement_filter_reasons(
                command.close,
                entry_plan.research_put_strike,
                entry_plan.target_gain_percent,
                command.atr_percent,
                bearish=True,
            )
        )
    return sorted(set(reasons))


def grade_put_candidate(
    symbol: str,
    company: str,
    sector: str,
    benchmark: str,
    command: PutCommandResult,
    daily_momentum: MomentumResult,
    four_hour: MomentumResult,
    option_liquidity: str,
    catalyst: Catalyst,
    market_regime: str,
    entry_plan: PutEntryPlan,
    allow_technical_watch: bool = True,
) -> PutCandidate:
    base_rejection_reasons = automatic_put_rejections(
        command, daily_momentum, four_hour, option_liquidity, catalyst, market_regime
    )
    rejection_reasons = automatic_put_rejections(
        command,
        daily_momentum,
        four_hour,
        option_liquidity,
        catalyst,
        market_regime,
        entry_plan=entry_plan,
    )

    # S-Put tier: every condition must pass
    s_requirements = [
        command.score >= 85,
        command.put_bias in {"Bearish", "Breakdown confirmed", "Rejection setup"},
        daily_momentum.score >= 80,
        daily_momentum.state in {"Bearish", "Strong bearish"},
        four_hour.score >= 85,
        four_hour.bullish_confirmation,  # bearish confirmation in put context
        four_hour.daily_filter_passed,
        command.relative_weakness == "Leading",
        command.below_vwap,
        not command.extended_downside,
        command.weekly_alignment,
        option_liquidity == "Good",
        catalyst_allows_primary_grade(catalyst) or catalyst.summary == "Technical continuation only",
        market_regime != "Supportive",
        entry_plan.status in {"valid now", "approaching"},
        not rejection_reasons,
    ]
    if all(s_requirements):
        grade = Grade.S_TIER
        missing = None
        reason = None
    else:
        minor_missing = 0
        missing_labels: list[str] = []
        if not four_hour.bullish_confirmation:
            minor_missing += 1
            missing_labels.append("Waiting for four hour bearish close below breakdown")
        if daily_momentum.state == "Improving":
            minor_missing += 1
            missing_labels.append("Daily MACD improving bearish but not fully confirmed")

        a_requirements = [
            command.score >= 75,
            daily_momentum.score >= 70,
            four_hour.score >= 75,
            not command.extended_downside,
            command.relative_weakness in {"Leading", "Strong"},
            option_liquidity in {"Good", "Acceptable"},
            market_regime != "Supportive",
            not catalyst.major_event_risk,
            minor_missing <= 1,
            not rejection_reasons,
        ]
        if all(a_requirements):
            grade = Grade.A_PLUS
            missing = "; ".join(missing_labels) if missing_labels else "None"
            reason = "One or more S-Put tier requirements did not pass."
        elif allow_technical_watch and all(
            [
                command.score >= 75,
                daily_momentum.score >= 70,
                four_hour.score >= 75,
                not command.extended_downside,
                command.relative_weakness in {"Leading", "Strong"},
                option_liquidity in {"Unknown", "Indicative"},
                market_regime != "Supportive",
                not catalyst.major_event_risk,
                not base_rejection_reasons,
            ]
        ):
            grade = Grade.TECHNICAL_WATCH
            missing = "Current tradable put option liquidity is unavailable on the free data plan"
            reason = "Not S-Put or A+-Put because OPRA-quality option liquidity is unavailable."
        elif all(
            [
                command.score >= 65,
                daily_momentum.score >= 55,
                four_hour.score >= 60,
                not command.extended_downside,
                command.close < command.sma200,
                command.relative_weakness != "Lagging",
                market_regime != "Supportive",
                option_liquidity not in {"Poor"},
                not catalyst.major_event_risk,
                not base_rejection_reasons,
            ]
        ):
            grade = Grade.B_TIER
            missing = "Developing put setup — scores below A+ thresholds"
            reason = "Developing put setup: does not yet meet A+-Put command, momentum, or confirmation requirements."
        else:
            grade = Grade.REJECTED
            missing = None
            reason = "Rejected by deterministic put requirements."

    return PutCandidate(
        symbol=symbol,
        company=company,
        sector=sector,
        benchmark=benchmark,
        command=command,
        daily_momentum=daily_momentum,
        four_hour_momentum=four_hour,
        option_liquidity=option_liquidity,
        catalyst=catalyst,
        market_regime=market_regime,
        entry_plan=entry_plan,
        grade=grade,
        missing_confirmation=missing,
        not_s_tier_reason=reason,
        rejection_reasons=rejection_reasons,
    )
