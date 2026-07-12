from __future__ import annotations

from scanner.catalyst_research import catalyst_allows_primary_grade
from scanner.models import Candidate, Catalyst, CommandResult, EntryPlan, Grade, MomentumResult


def automatic_rejections(
    command: CommandResult,
    daily_momentum: MomentumResult,
    four_hour: MomentumResult,
    option_liquidity: str,
    catalyst: Catalyst,
    market_regime: str,
    entry_plan: EntryPlan | None = None,
) -> list[str]:
    reasons = list(command.rejection_reasons)
    if command.score < 60:
        reasons.append("daily_command_score_below_60")
    if option_liquidity == "Poor":
        reasons.append("options_illiquid")
    if market_regime == "Hostile":
        reasons.append("hostile_market_regime")
    if not catalyst.verified and catalyst.summary != "Technical continuation only":
        reasons.append("unverified_catalyst")
    if catalyst.major_event_risk:
        reasons.append("major_event_risk")
    if not four_hour.daily_filter_passed and four_hour.score >= 70:
        reasons.append("daily_filter_blocked_four_hour_only")
    if daily_momentum.state == "Warning active":
        reasons.append("daily_momentum_warning")
    return sorted(set(reasons))


def grade_candidate(
    symbol: str,
    company: str,
    sector: str,
    benchmark: str,
    command: CommandResult,
    daily_momentum: MomentumResult,
    four_hour: MomentumResult,
    option_liquidity: str,
    catalyst: Catalyst,
    market_regime: str,
    entry_plan: EntryPlan,
    allow_technical_watch: bool = True,
) -> Candidate:
    base_rejection_reasons = automatic_rejections(
        command, daily_momentum, four_hour, option_liquidity, catalyst, market_regime
    )
    rejection_reasons = automatic_rejections(
        command,
        daily_momentum,
        four_hour,
        option_liquidity,
        catalyst,
        market_regime,
        entry_plan=entry_plan,
    )
    s_requirements = [
        command.score >= 85,
        command.call_bias in {"Pullback setup", "Breakout confirmed"},
        daily_momentum.score >= 80,
        daily_momentum.state in {"Bullish", "Strong bullish"},
        four_hour.score >= 85,
        four_hour.bullish_confirmation,
        four_hour.daily_filter_passed,
        command.relative_strength == "Leading",
        command.above_vwap,
        not command.extended,
        command.weekly_alignment,
        option_liquidity == "Good",
        catalyst_allows_primary_grade(catalyst)
        or catalyst.summary == "Technical continuation only",
        market_regime != "Hostile",
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
            missing_labels.append("Waiting for four hour breakout close")
        if daily_momentum.state == "Improving":
            minor_missing += 1
            missing_labels.append("Daily MACD improving but not fully bullish")
        a_requirements = [
            command.score >= 75,
            daily_momentum.score >= 70,
            four_hour.score >= 75,
            not command.extended,
            command.relative_strength in {"Leading", "Improving"},
            option_liquidity in {"Good", "Acceptable"},
            market_regime != "Hostile",
            not catalyst.major_event_risk,
            minor_missing <= 1,
            not rejection_reasons,
        ]
        if all(a_requirements):
            grade = Grade.A_PLUS
            missing = "; ".join(missing_labels) if missing_labels else "None"
            reason = "Ready after the remaining confirmation is verified."
        elif allow_technical_watch and all(
            [
                command.score >= 75,
                daily_momentum.score >= 70,
                four_hour.score >= 75,
                not command.extended,
                command.relative_strength in {"Leading", "Improving"},
                option_liquidity in {"Unknown", "Indicative"},
                market_regime != "Hostile",
                not catalyst.major_event_risk,
                not base_rejection_reasons,
            ]
        ):
            grade = Grade.TECHNICAL_WATCH
            missing = "Current tradable option liquidity is unavailable on the free data plan"
            reason = "Live option-chain quality must be verified in the broker."
        elif all(
            [
                command.score >= 65,
                daily_momentum.score >= 55,
                four_hour.score >= 60,
                not command.extended,
                command.close > command.sma200,
                command.relative_strength != "Lagging",
                market_regime != "Hostile",
                option_liquidity not in {"Poor"},
                not catalyst.major_event_risk,
                not base_rejection_reasons,
            ]
        ):
            grade = Grade.B_TIER
            missing = "Trend is developing; wait for a current pullback or breakout trigger"
            reason = "Developing setup: confirmation is not ready."
        else:
            grade = Grade.REJECTED
            missing = None
            reason = "Rejected by deterministic requirements."
    return Candidate(
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
