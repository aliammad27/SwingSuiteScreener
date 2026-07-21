from __future__ import annotations

import math

from scanner.models import Candidate, OptionContractSnapshot, PremiumTargetScenario
from scanner.strategy_profile import PROFILE

SCENARIO_ASSUMPTIONS = "quote-anchored Greeks; stable IV; not a forecast"
LIVE_OPRA_REQUIRED = "live OPRA verification required"


def estimate_premium_range(
    contract: OptionContractSnapshot,
    *,
    underlying_price: float,
    underlying_target: float,
    maximum_hold_sessions: int,
) -> tuple[float, float]:
    """Estimate an immediate-to-maximum-hold premium range from refreshed Greeks."""
    move = underlying_target - underlying_price
    gamma = contract.gamma if contract.gamma is not None else 0.0
    greek_response = contract.delta * move + 0.5 * gamma * move * move
    intrinsic_floor = max(underlying_target - contract.strike, 0.0)
    immediate_high = max(contract.ask + greek_response, intrinsic_floor, 0.0)
    maximum_hold_low = max(
        contract.bid + greek_response - abs(contract.theta or 0.0) * maximum_hold_sessions,
        intrinsic_floor,
        0.0,
    )
    return round(min(maximum_hold_low, immediate_high), 2), round(
        max(maximum_hold_low, immediate_high), 2
    )


def _scenario_unavailable_reason(candidate: Candidate) -> str | None:
    selection = candidate.contracts
    contract = selection.primary
    risk = selection.primary_risk
    if contract is None:
        return LIVE_OPRA_REQUIRED
    if (
        selection.feed.lower() != PROFILE.required_option_feed.lower()
        or not candidate.data_trust.option_trusted
    ):
        return LIVE_OPRA_REQUIRED
    if (
        risk is None
        or risk.quote_age_minutes < 0
        or risk.quote_age_minutes > PROFILE.maximum_quote_age_minutes
        or not risk.quote_stable
    ):
        return LIVE_OPRA_REQUIRED
    if (
        contract.bid <= 0
        or contract.ask < contract.bid
        or contract.spread_percent > PROFILE.lane(candidate.lane).maximum_spread_percent
        or not math.isfinite(contract.bid)
        or not math.isfinite(contract.ask)
        or not math.isfinite(contract.delta)
        or contract.theta is None
        or not math.isfinite(contract.theta)
    ):
        return LIVE_OPRA_REQUIRED
    if contract.gamma is not None and not math.isfinite(contract.gamma):
        return LIVE_OPRA_REQUIRED
    return None


def _underlying_targets(candidate: Candidate) -> tuple[tuple[str, float, str], ...]:
    plan = candidate.entry_plan
    targets: list[tuple[str, float, str]] = [
        ("TP1", plan.target_price, plan.target_basis)
    ]
    if round(plan.planning_objective_2r, 2) > round(plan.target_price, 2):
        targets.append(("TP2", plan.planning_objective_2r, "2R planning objective"))
    return tuple(targets)


def premium_target_scenarios(candidate: Candidate) -> tuple[PremiumTargetScenario, ...]:
    """Build display-only target scenarios without changing candidate qualification."""
    maximum_hold = max(candidate.entry_plan.intended_hold_sessions)
    sessions = (0, maximum_hold)
    unavailable_reason = _scenario_unavailable_reason(candidate)
    contract = candidate.contracts.primary
    scenarios: list[PremiumTargetScenario] = []
    for label, target, basis in _underlying_targets(candidate):
        premium_low: float | None = None
        premium_high: float | None = None
        if unavailable_reason is None and contract is not None:
            premium_low, premium_high = estimate_premium_range(
                contract,
                underlying_price=candidate.trend.close,
                underlying_target=target,
                maximum_hold_sessions=maximum_hold,
            )
        assumptions = SCENARIO_ASSUMPTIONS
        if contract is not None and contract.gamma is None:
            assumptions += "; gamma unavailable, delta-only price response"
        scenarios.append(
            PremiumTargetScenario(
                target_label=label,
                underlying_target=target,
                target_basis=basis,
                premium_low=premium_low,
                premium_high=premium_high,
                modeled_sessions=sessions,
                assumptions=assumptions,
                unavailable_reason=unavailable_reason,
            )
        )
    return tuple(scenarios)
