from __future__ import annotations

from datetime import datetime

from scanner.models import ContractSelection, OptionContractSnapshot
from scanner.strategy_profile import LaneProfile


def _range_fit(value: float, preferred: tuple[float, float], weight: float) -> float:
    low, high = preferred
    center = (low + high) / 2
    half_width = max((high - low) / 2, 0.001)
    return max(0.0, weight * (1 - abs(value - center) / half_width))


def contract_rejection_reasons(
    contract: OptionContractSnapshot,
    lane: LaneProfile,
    as_of: datetime,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not lane.hard_dte[0] <= contract.dte <= lane.hard_dte[1]:
        reasons.append("dte_outside_hard_range")
    if not lane.hard_delta[0] <= contract.delta <= lane.hard_delta[1]:
        reasons.append("delta_outside_hard_range")
    if contract.bid <= 0 or contract.ask < contract.bid:
        reasons.append("invalid_bid_ask")
    if contract.spread_percent > lane.maximum_spread_percent:
        reasons.append("spread_too_wide")
    if contract.open_interest < lane.minimum_open_interest:
        reasons.append("open_interest_below_minimum")
    if contract.volume < lane.minimum_volume:
        reasons.append("volume_below_minimum")
    age_minutes = max((as_of - contract.quote_timestamp).total_seconds() / 60, 0.0)
    if age_minutes > lane.maximum_quote_age_minutes:
        reasons.append("quote_stale")
    return tuple(reasons)


def score_contract(
    contract: OptionContractSnapshot,
    lane: LaneProfile,
    as_of: datetime,
) -> int:
    if contract_rejection_reasons(contract, lane, as_of):
        return 0
    delta_score = _range_fit(contract.delta, lane.preferred_delta, 25)
    spread_score = 25 * max(
        0.0, 1 - contract.spread_percent / lane.maximum_spread_percent
    )
    preferred_dte = (float(lane.preferred_dte[0]), float(lane.preferred_dte[1]))
    dte_score = _range_fit(float(contract.dte), preferred_dte, 20)
    oi_score = 15 * min(contract.open_interest / (2 * lane.minimum_open_interest), 1.0)
    volume_score = 10 * min(contract.volume / (2 * lane.minimum_volume), 1.0)
    age_minutes = max((as_of - contract.quote_timestamp).total_seconds() / 60, 0.0)
    freshness_score = 5 * max(0.0, 1 - age_minutes / lane.maximum_quote_age_minutes)
    return round(
        delta_score + spread_score + dte_score + oi_score + volume_score + freshness_score
    )


def select_contracts(
    contracts: list[OptionContractSnapshot],
    lane: LaneProfile,
    as_of: datetime,
    realized_volatility: float | None,
    *,
    feed_when_empty: str = "unknown",
) -> ContractSelection:
    feed = contracts[0].feed if contracts else feed_when_empty
    scored = [
        (score_contract(contract, lane, as_of), contract)
        for contract in contracts
        if not contract_rejection_reasons(contract, lane, as_of)
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        reasons = sorted(
            {
                reason
                for contract in contracts
                for reason in contract_rejection_reasons(contract, lane, as_of)
            }
        )
        if not contracts:
            reasons.append("option_chain_unavailable")
        return ContractSelection(
            score=0,
            primary=None,
            alternatives=(),
            feed=feed,
            realized_volatility=realized_volatility,
            iv_to_realized_volatility=None,
            rejection_reasons=tuple(reasons),
        )
    top = tuple(contract for _, contract in scored[:3])
    primary_score, primary = scored[0]
    iv_ratio: float | None = None
    if (
        primary.implied_volatility is not None
        and realized_volatility is not None
        and realized_volatility > 0
    ):
        iv_ratio = primary.implied_volatility / realized_volatility
    return ContractSelection(
        score=primary_score,
        primary=primary,
        alternatives=top[1:],
        feed=feed,
        realized_volatility=realized_volatility,
        iv_to_realized_volatility=iv_ratio,
    )
