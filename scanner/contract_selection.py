from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from scanner.models import (
    ContractRiskMetrics,
    ContractSelection,
    OptionContractSnapshot,
)
from scanner.strategy_profile import LaneProfile


def _range_fit(value: float, preferred: tuple[float, float], weight: float) -> float:
    low, high = preferred
    center = (low + high) / 2
    half_width = max((high - low) / 2, 0.001)
    normalized_distance = abs(value - center) / half_width
    return max(0.0, weight * (1 - 0.30 * normalized_distance))


def _is_standard_monthly(contract: OptionContractSnapshot) -> bool:
    expiry = contract.expiration_date
    return expiry.weekday() == 4 and 15 <= expiry.day <= 21


def _expiration_style(contract: OptionContractSnapshot) -> str:
    return "standard_monthly" if _is_standard_monthly(contract) else "weekly"


def _quote_age_minutes(contract: OptionContractSnapshot, as_of: datetime) -> float:
    return (as_of - contract.quote_timestamp).total_seconds() / 60


def calculate_contract_risk(
    contract: OptionContractSnapshot,
    lane: LaneProfile,
    as_of: datetime,
    realized_volatility: float | None,
    underlying_price: float,
    previous: OptionContractSnapshot | None = None,
) -> ContractRiskMetrics:
    theta_percent = (
        abs(contract.theta) / contract.ask * 100
        if contract.theta is not None and contract.ask > 0
        else None
    )
    intrinsic = max(underlying_price - contract.strike, 0.0)
    extrinsic_percent = (
        max(contract.ask - intrinsic, 0.0) / contract.ask * 100 if contract.ask > 0 else None
    )
    iv_ratio = None
    if (
        contract.implied_volatility is not None
        and realized_volatility is not None
        and realized_volatility > 0
    ):
        iv_ratio = contract.implied_volatility / realized_volatility
    quote_change: float | None = None
    if previous is not None and previous.mid > 0:
        quote_change = abs(contract.mid - previous.mid) / previous.mid * 100
    return ContractRiskMetrics(
        theta_ask_percent=theta_percent,
        extrinsic_value_percent=extrinsic_percent,
        iv_to_realized_volatility=iv_ratio,
        depth_contracts=min(contract.bid_size, contract.ask_size),
        gamma=contract.gamma,
        quote_age_minutes=_quote_age_minutes(contract, as_of),
        quote_change_percent=quote_change,
        quote_stable=quote_change is None or quote_change <= 10.0,
        expiration_style=_expiration_style(contract),
    )


def contract_rejection_reasons(
    contract: OptionContractSnapshot,
    lane: LaneProfile,
    as_of: datetime,
    *,
    maximum_quote_age_minutes: int,
    realized_volatility: float | None = None,
    underlying_price: float = 0.0,
    previous: OptionContractSnapshot | None = None,
) -> tuple[str, ...]:
    dte = (contract.expiration_date - as_of.date()).days
    normalized = replace(contract, dte=dte)
    risk = calculate_contract_risk(
        normalized,
        lane,
        as_of,
        realized_volatility,
        underlying_price,
        previous,
    )
    reasons: list[str] = []
    if not lane.hard_dte[0] <= dte <= lane.hard_dte[1]:
        reasons.append("dte_outside_hard_range")
    if dte <= 6:
        reasons.append("zero_to_six_dte_excluded")
    if not lane.hard_delta[0] <= normalized.delta <= lane.hard_delta[1]:
        reasons.append("delta_outside_hard_range")
    if normalized.bid <= 0 or normalized.ask < normalized.bid:
        reasons.append("invalid_bid_ask")
    if normalized.spread_percent > lane.maximum_spread_percent + 1e-9:
        reasons.append("spread_too_wide")
    if normalized.open_interest < lane.minimum_open_interest:
        reasons.append("open_interest_below_minimum")
    if normalized.volume < lane.minimum_volume:
        reasons.append("volume_below_minimum")
    if (
        normalized.bid_size < lane.minimum_bid_ask_size
        or normalized.ask_size < lane.minimum_bid_ask_size
    ):
        reasons.append("bid_ask_size_below_minimum")
    if risk.quote_age_minutes > maximum_quote_age_minutes:
        reasons.append("quote_stale")
    if risk.quote_age_minutes < 0:
        reasons.append("quote_timestamp_in_future")
    if risk.theta_ask_percent is None:
        reasons.append("theta_unavailable")
    elif risk.theta_ask_percent > lane.maximum_theta_ask_percent + 1e-9:
        reasons.append("theta_ask_percent_too_high")
    return tuple(reasons)


def _iv_score(ratio: float | None) -> float:
    if ratio is None:
        return 2.0
    if 0.75 <= ratio <= 1.25:
        return 8.0
    if 0.55 <= ratio <= 1.60:
        return 5.0
    if ratio <= 2.0:
        return 2.0
    return 0.0


def _extrinsic_score(percent: float | None) -> float:
    if percent is None:
        return 0.0
    if 30 <= percent <= 75:
        return 6.0
    if 15 <= percent <= 90:
        return 3.0
    return 1.0


def score_contract(
    contract: OptionContractSnapshot,
    lane: LaneProfile,
    as_of: datetime,
    realized_volatility: float | None,
    underlying_price: float,
    *,
    maximum_quote_age_minutes: int,
    previous: OptionContractSnapshot | None = None,
) -> tuple[int, ContractRiskMetrics]:
    dte = (contract.expiration_date - as_of.date()).days
    contract = replace(contract, dte=dte)
    risk = calculate_contract_risk(
        contract,
        lane,
        as_of,
        realized_volatility,
        underlying_price,
        previous,
    )
    if contract_rejection_reasons(
        contract,
        lane,
        as_of,
        maximum_quote_age_minutes=maximum_quote_age_minutes,
        realized_volatility=realized_volatility,
        underlying_price=underlying_price,
        previous=previous,
    ):
        return 0, risk
    delta_score = _range_fit(contract.delta, lane.preferred_delta, 15)
    spread_score = 15 * max(0.0, 1 - contract.spread_percent / lane.maximum_spread_percent)
    preferred_dte = (float(lane.preferred_dte[0]), float(lane.preferred_dte[1]))
    dte_score = _range_fit(float(contract.dte), preferred_dte, 12)
    oi_score = 8 * min(contract.open_interest / (2 * lane.minimum_open_interest), 1.0)
    volume_score = 8 * min(contract.volume / (2 * lane.minimum_volume), 1.0)
    depth_score = 8 * min(risk.depth_contracts / (2 * lane.minimum_bid_ask_size), 1.0)
    theta_score = 10 * max(
        0.0,
        1
        - (risk.theta_ask_percent or lane.maximum_theta_ask_percent)
        / lane.maximum_theta_ask_percent,
    )
    gamma_score = (
        3.0
        if risk.gamma is not None and 0.01 <= risk.gamma <= 0.08
        else 1.0
        if risk.gamma is not None
        else 0.0
    )
    freshness_score = 4 * max(0.0, 1 - risk.quote_age_minutes / maximum_quote_age_minutes)
    stability_score = 3.0 if risk.quote_stable else 0.0
    return (
        round(
            delta_score
            + spread_score
            + dte_score
            + oi_score
            + volume_score
            + depth_score
            + theta_score
            + _iv_score(risk.iv_to_realized_volatility)
            + _extrinsic_score(risk.extrinsic_value_percent)
            + gamma_score
            + freshness_score
            + stability_score
        ),
        risk,
    )


def _liquidity_strength(
    contract: OptionContractSnapshot,
    risk: ContractRiskMetrics,
    lane: LaneProfile,
) -> float:
    return (
        contract.open_interest / lane.minimum_open_interest
        + contract.volume / lane.minimum_volume
        + risk.depth_contracts / lane.minimum_bid_ask_size
    )


def _expiration_preference_order(
    scored: list[tuple[int, OptionContractSnapshot, ContractRiskMetrics]],
    lane: LaneProfile,
) -> list[tuple[int, OptionContractSnapshot, ContractRiskMetrics]]:
    scored.sort(key=lambda item: item[0], reverse=True)
    if not lane.prefer_nonstandard_weekly:
        return scored
    weeklies = [item for item in scored if item[2].expiration_style == "weekly"]
    monthlies = [item for item in scored if item[2].expiration_style == "standard_monthly"]
    if not weeklies or not monthlies:
        return scored
    best_weekly = weeklies[0]
    best_monthly = monthlies[0]
    advantage = 1 + lane.monthly_liquidity_advantage_percent / 100
    monthly_materially_better = (
        _liquidity_strength(best_monthly[1], best_monthly[2], lane)
        >= _liquidity_strength(best_weekly[1], best_weekly[2], lane) * advantage
    )
    primary = best_monthly if monthly_materially_better else best_weekly
    return [primary] + [item for item in scored if item[1] != primary[1]]


def select_contracts(
    contracts: list[OptionContractSnapshot],
    lane: LaneProfile,
    as_of: datetime,
    realized_volatility: float | None,
    underlying_price: float,
    *,
    maximum_quote_age_minutes: int,
    feed_when_empty: str = "unknown",
    previous_quotes: dict[str, OptionContractSnapshot] | None = None,
    requoted_count: int = 0,
) -> ContractSelection:
    previous_quotes = previous_quotes or {}
    normalized = [
        replace(
            contract,
            dte=(contract.expiration_date - as_of.date()).days,
        )
        for contract in contracts
    ]
    feed = normalized[0].feed if normalized else feed_when_empty
    scored: list[tuple[int, OptionContractSnapshot, ContractRiskMetrics]] = []
    for contract in normalized:
        previous = previous_quotes.get(contract.contract_symbol)
        rejection_reasons = contract_rejection_reasons(
            contract,
            lane,
            as_of,
            maximum_quote_age_minutes=maximum_quote_age_minutes,
            realized_volatility=realized_volatility,
            underlying_price=underlying_price,
            previous=previous,
        )
        if rejection_reasons:
            continue
        score, risk = score_contract(
            contract,
            lane,
            as_of,
            realized_volatility,
            underlying_price,
            maximum_quote_age_minutes=maximum_quote_age_minutes,
            previous=previous,
        )
        scored.append((score, contract, risk))
    scored = _expiration_preference_order(scored, lane)
    if not scored:
        all_reasons = sorted(
            {
                reason
                for contract in normalized
                for reason in contract_rejection_reasons(
                    contract,
                    lane,
                    as_of,
                    maximum_quote_age_minutes=maximum_quote_age_minutes,
                    realized_volatility=realized_volatility,
                    underlying_price=underlying_price,
                    previous=previous_quotes.get(contract.contract_symbol),
                )
            }
        )
        if not normalized:
            all_reasons.append("option_chain_unavailable")
        return ContractSelection(
            score=0,
            primary=None,
            alternatives=(),
            feed=feed,
            realized_volatility=realized_volatility,
            iv_to_realized_volatility=None,
            requoted_count=requoted_count,
            rejection_reasons=tuple(all_reasons),
        )
    top = scored[:3]
    primary_score, primary, primary_risk = top[0]
    return ContractSelection(
        score=primary_score,
        primary=primary,
        alternatives=tuple(item[1] for item in top[1:]),
        feed=feed,
        realized_volatility=realized_volatility,
        iv_to_realized_volatility=primary_risk.iv_to_realized_volatility,
        primary_risk=primary_risk,
        alternative_risks=tuple(item[2] for item in top[1:]),
        requoted_count=requoted_count,
    )
