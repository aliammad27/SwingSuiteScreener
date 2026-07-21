from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from scanner.contract_selection import (
    contract_rejection_reasons,
    score_contract,
    select_contracts,
)
from scanner.evidence import annualized_realized_volatility
from scanner.models import StrategyLane
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.strategy_profile import PROFILE


def _inputs():
    provider = FixtureDataProvider("ready")
    lane = PROFILE.lane(StrategyLane.LEADER_WEEKLY)
    daily = provider.daily("SSTR")
    chain = provider.call_chain(
        "SSTR",
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[0]),
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[1]),
        FIXTURE_TIMESTAMP,
    )
    return provider, lane, daily, chain


def _rejections(contract, lane, daily):
    return contract_rejection_reasons(
        contract,
        lane,
        FIXTURE_TIMESTAMP,
        maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
        realized_volatility=annualized_realized_volatility(daily),
        underlying_price=daily[-1].close,
    )


def test_contract_ranking_returns_actual_top_three() -> None:
    _, lane, daily, chain = _inputs()
    selection = select_contracts(
        chain,
        lane,
        FIXTURE_TIMESTAMP,
        annualized_realized_volatility(daily),
        daily[-1].close,
        maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
    )
    assert selection.primary is not None
    assert selection.primary.contract_symbol.startswith("SSTR")
    assert len(selection.alternatives) == 2
    assert selection.score >= 80
    assert selection.primary_risk is not None
    assert selection.primary_risk.expiration_style == "weekly"


def test_hard_spread_boundary_is_inclusive() -> None:
    _, lane, daily, chain = _inputs()
    contract = chain[0]
    bid = 4.0
    ask = bid * (200 + lane.maximum_spread_percent) / (200 - lane.maximum_spread_percent)
    at_boundary = replace(contract, bid=bid, ask=ask)
    assert at_boundary.spread_percent == pytest.approx(lane.maximum_spread_percent)
    assert "spread_too_wide" not in _rejections(at_boundary, lane, daily)
    outside = replace(at_boundary, ask=ask + 0.01)
    assert "spread_too_wide" in _rejections(outside, lane, daily)


def test_quote_age_depth_and_theta_boundaries_are_hard() -> None:
    _, lane, daily, chain = _inputs()
    contract = chain[0]
    at_boundary = replace(
        contract,
        bid_size=lane.minimum_bid_ask_size,
        ask_size=lane.minimum_bid_ask_size,
        theta=-(contract.ask * lane.maximum_theta_ask_percent / 100),
        quote_timestamp=FIXTURE_TIMESTAMP - timedelta(minutes=PROFILE.maximum_quote_age_minutes),
    )
    reasons = _rejections(at_boundary, lane, daily)
    assert "bid_ask_size_below_minimum" not in reasons
    assert "theta_ask_percent_too_high" not in reasons
    assert "quote_stale" not in reasons

    outside = replace(
        at_boundary,
        bid_size=lane.minimum_bid_ask_size - 1,
        theta=at_boundary.theta * 1.01 if at_boundary.theta is not None else None,
        quote_timestamp=at_boundary.quote_timestamp - timedelta(seconds=1),
    )
    reasons = _rejections(outside, lane, daily)
    assert "bid_ask_size_below_minimum" in reasons
    assert "theta_ask_percent_too_high" in reasons
    assert "quote_stale" in reasons


def test_future_dated_quote_is_rejected() -> None:
    _, lane, daily, chain = _inputs()
    future = replace(
        chain[0],
        quote_timestamp=FIXTURE_TIMESTAMP + timedelta(seconds=1),
    )

    assert "quote_timestamp_in_future" in _rejections(future, lane, daily)


def test_exact_scan_time_dte_overrides_embedded_snapshot_dte() -> None:
    _, lane, daily, chain = _inputs()
    embedded_wrong = replace(chain[0], dte=999)
    score, _ = score_contract(
        embedded_wrong,
        lane,
        FIXTURE_TIMESTAMP,
        annualized_realized_volatility(daily),
        daily[-1].close,
        maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
    )
    assert score > 0
    expired = replace(
        embedded_wrong,
        expiration_date=FIXTURE_TIMESTAMP.date() + timedelta(days=6),
    )
    assert "zero_to_six_dte_excluded" in _rejections(expired, lane, daily)


def test_indicative_feed_can_rank_but_is_not_trustworthy() -> None:
    provider = FixtureDataProvider("technical_watch")
    lane = PROFILE.lane(StrategyLane.LEADER_WEEKLY)
    daily = provider.daily("SSTR")
    chain = provider.call_chain(
        "SSTR",
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[0]),
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[1]),
        FIXTURE_TIMESTAMP,
    )
    selection = select_contracts(
        chain,
        lane,
        FIXTURE_TIMESTAMP,
        annualized_realized_volatility(daily),
        daily[-1].close,
        maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
    )
    assert selection.score >= 80
    assert not selection.trustworthy


def test_dte_delta_open_interest_and_volume_boundaries_are_inclusive() -> None:
    _, lane, daily, chain = _inputs()
    base = chain[0]
    for dte in lane.hard_dte:
        for delta in lane.hard_delta:
            boundary = replace(
                base,
                expiration_date=FIXTURE_TIMESTAMP.date() + timedelta(days=dte),
                delta=delta,
                open_interest=lane.minimum_open_interest,
                volume=lane.minimum_volume,
            )
            reasons = _rejections(boundary, lane, daily)
            assert "dte_outside_hard_range" not in reasons
            assert "delta_outside_hard_range" not in reasons
            assert "open_interest_below_minimum" not in reasons
            assert "volume_below_minimum" not in reasons


def test_weekly_is_preferred_unless_monthly_liquidity_is_materially_better() -> None:
    _, lane, daily, chain = _inputs()
    as_of = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    base = chain[0]
    weekly = replace(
        base,
        contract_symbol="SSTR260724C00150000",
        expiration_date=as_of.date() + timedelta(days=23),
        quote_timestamp=as_of,
        open_interest=lane.minimum_open_interest * 2,
        volume=lane.minimum_volume * 2,
        bid_size=lane.minimum_bid_ask_size * 2,
        ask_size=lane.minimum_bid_ask_size * 2,
    )
    monthly_equal = replace(
        weekly,
        contract_symbol="SSTR260717C00150000",
        expiration_date=as_of.date() + timedelta(days=16),
    )
    equal = select_contracts(
        [monthly_equal, weekly],
        lane,
        as_of,
        annualized_realized_volatility(daily),
        daily[-1].close,
        maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
    )
    assert equal.primary is not None
    assert equal.primary.contract_symbol == weekly.contract_symbol

    monthly_deeper = replace(
        monthly_equal,
        open_interest=lane.minimum_open_interest * 5,
        volume=lane.minimum_volume * 5,
        bid_size=lane.minimum_bid_ask_size * 5,
        ask_size=lane.minimum_bid_ask_size * 5,
    )
    deeper = select_contracts(
        [weekly, monthly_deeper],
        lane,
        as_of,
        annualized_realized_volatility(daily),
        daily[-1].close,
        maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
    )
    assert deeper.primary is not None
    assert deeper.primary.contract_symbol == monthly_deeper.contract_symbol
