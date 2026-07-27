from __future__ import annotations

from math import sqrt

from scanner.models import (
    Candle,
    CatalystSignal,
    ContractEconomics,
    ContractSelection,
    DataTrust,
    EvidenceScores,
    OpportunityTier,
    ReviewState,
    StrategyLane,
)
from scanner.strategy_profile import StrategyProfile


def composite_score(scores: EvidenceScores) -> int:
    values = [
        scores.trend,
        scores.setup,
        scores.timing,
        scores.market,
        scores.contract,
        scores.risk,
    ]
    if scores.leadership is not None:
        values.append(scores.leadership)
    return round(sum(values) / len(values))


def asymmetric_qualification_failures(
    lane: StrategyLane,
    scores: EvidenceScores,
    profile: StrategyProfile,
) -> tuple[str, ...]:
    tier = profile.opportunity_tiers
    requirements = {
        "asymmetric_trend_below_threshold": scores.trend >= tier.asymmetric_trend,
        "asymmetric_setup_below_threshold": scores.setup >= tier.asymmetric_setup,
        "asymmetric_timing_below_threshold": scores.timing >= tier.asymmetric_timing,
        "asymmetric_market_below_threshold": scores.market >= tier.asymmetric_market,
        "asymmetric_risk_below_threshold": scores.risk >= tier.asymmetric_risk,
    }
    if lane == StrategyLane.LEADER_WEEKLY:
        requirements["asymmetric_leadership_below_threshold"] = (
            scores.leadership is not None
            and scores.leadership >= tier.asymmetric_leadership
        )
    return tuple(reason for reason, passed in requirements.items() if not passed)


def detect_catalyst_signal(
    candles: list[Candle],
    atr: float,
    profile: StrategyProfile,
) -> CatalystSignal | None:
    if len(candles) < 22 or atr <= 0:
        return None
    settings = profile.catalyst
    for age in range(settings.maximum_age_bars):
        index = len(candles) - 1 - age
        if index < 20:
            break
        candle = candles[index]
        previous = candles[index - 1]
        average_volume = sum(item.volume for item in candles[index - 20 : index]) / 20
        relative_volume = candle.volume / average_volume if average_volume else 0.0
        gap = candle.open - previous.close
        gap_atr = gap / atr
        midpoint = previous.close + gap / 2
        held_midpoint = candle.close >= midpoint
        if (
            gap_atr >= settings.gap_minimum_atr
            and relative_volume >= settings.relative_volume_minimum
            and candle.close > candle.open
            and (held_midpoint or not settings.require_gap_midpoint_hold)
        ):
            return CatalystSignal(
                kind="gap_continuation",
                age_bars=age,
                gap_atr=round(gap_atr, 2),
                relative_volume=round(relative_volume, 2),
                held_gap_midpoint=held_midpoint,
                event_verified=False,
                summary=(
                    "High volume gap continuation detected from completed daily bars; "
                    "the originating event is not independently verified."
                ),
            )
    return None


def contract_economics(
    selection: ContractSelection,
    *,
    underlying_price: float,
    target_price: float,
    hold_sessions: int,
) -> ContractEconomics | None:
    primary = selection.primary
    if primary is None:
        return None
    expected_move = (
        underlying_price
        * primary.implied_volatility
        * sqrt(primary.dte / 365)
        if primary.implied_volatility is not None and primary.dte > 0
        else None
    )
    target_move = max(target_price - underlying_price, 0.0)
    target_ratio = (
        target_move / expected_move
        if expected_move is not None and expected_move > 0
        else None
    )
    theta_cost = abs(primary.theta) * hold_sessions if primary.theta is not None else None
    theta_percent = (
        theta_cost / primary.ask * 100
        if theta_cost is not None and primary.ask > 0
        else None
    )
    short = next(
        (
            contract
            for contract in selection.alternatives
            if contract.expiration_date == primary.expiration_date
            and contract.strike > primary.strike
            and contract.bid > 0
        ),
        None,
    )
    spread_debit = None
    spread_max_profit = None
    spread_reward_to_risk = None
    spread_breakeven = None
    if short is not None:
        spread_debit = primary.ask - short.bid
        width = short.strike - primary.strike
        if 0 < spread_debit < width:
            spread_max_profit = width - spread_debit
            spread_reward_to_risk = spread_max_profit / spread_debit
            spread_breakeven = primary.strike + spread_debit
        else:
            short = None
            spread_debit = None
    return ContractEconomics(
        expected_move=expected_move,
        target_move=target_move,
        target_to_expected_move=target_ratio,
        long_call_breakeven=primary.strike + primary.ask,
        breakeven_move_percent=((primary.strike + primary.ask) / underlying_price - 1) * 100,
        theta_cost_sessions=hold_sessions,
        theta_cost=theta_cost,
        theta_cost_percent=theta_percent,
        iv_to_realized_volatility=selection.iv_to_realized_volatility,
        spread_short_contract=short.contract_symbol if short else None,
        spread_short_strike=short.strike if short else None,
        spread_debit=spread_debit,
        spread_max_profit=spread_max_profit,
        spread_reward_to_risk=spread_reward_to_risk,
        spread_breakeven=spread_breakeven,
    )


def classify_opportunity_tier(
    *,
    state: ReviewState,
    scores: EvidenceScores,
    data_trust: DataTrust,
    economics: ContractEconomics | None,
    asymmetric_path: bool,
    profile: StrategyProfile,
) -> OpportunityTier:
    settings = profile.opportunity_tiers
    if asymmetric_path:
        ratio = economics.target_to_expected_move if economics else None
        iv_ratio = economics.iv_to_realized_volatility if economics else None
        if (
            scores.contract >= settings.asymmetric_contract
            and ratio is not None
            and ratio >= settings.asymmetric_minimum_target_to_expected_move
            and (
                iv_ratio is None
                or iv_ratio <= settings.asymmetric_maximum_iv_to_realized_volatility
            )
            and data_trust.trustworthy
        ):
            return OpportunityTier.ASYMMETRIC
        return OpportunityTier.WATCHLIST
    composite = composite_score(scores)
    if (
        state in {ReviewState.READY, ReviewState.READY_VERIFY}
        and scores.contract >= settings.s_tier_minimum_contract
        and composite >= settings.s_tier_minimum_composite
        and data_trust.trustworthy
    ):
        return OpportunityTier.S_TIER
    if (
        state in {
            ReviewState.READY,
            ReviewState.READY_VERIFY,
            ReviewState.VERIFY_CONTRACT,
        }
        and scores.contract >= settings.a_plus_minimum_contract
        and composite >= settings.a_plus_minimum_composite
    ):
        return OpportunityTier.A_PLUS
    return OpportunityTier.WATCHLIST
