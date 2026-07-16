from dataclasses import replace
from datetime import timedelta

import pytest

from scanner.contract_selection import (
    contract_rejection_reasons,
    score_contract,
    select_contracts,
)
from scanner.models import StrategyLane
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.strategy_profile import PROFILE


def _leader_contract():
    provider = FixtureDataProvider("ready")
    lane = PROFILE.lane(StrategyLane.LEADER_SWING)
    return provider.call_chain(
        "SSTR",
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[0]),
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[1]),
    )[0]


def test_contract_ranking_returns_actual_top_three() -> None:
    provider = FixtureDataProvider("ready")
    lane = PROFILE.lane(StrategyLane.LEADER_SWING)
    chain = provider.call_chain(
        "SSTR",
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[0]),
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[1]),
    )
    selection = select_contracts(chain, lane, FIXTURE_TIMESTAMP, 0.25)
    assert selection.primary is not None
    assert selection.primary.contract_symbol.startswith("SSTR")
    assert len(selection.alternatives) == 2
    assert selection.score >= 80
    assert selection.iv_to_realized_volatility is not None


def test_hard_spread_boundary_is_inclusive() -> None:
    lane = PROFILE.lane(StrategyLane.LEADER_SWING)
    contract = _leader_contract()
    bid = 4.0
    ask = bid * (200 + lane.maximum_spread_percent) / (200 - lane.maximum_spread_percent)
    at_boundary = replace(contract, bid=bid, ask=ask)
    assert at_boundary.spread_percent == pytest.approx(lane.maximum_spread_percent)
    assert "spread_too_wide" not in contract_rejection_reasons(at_boundary, lane, FIXTURE_TIMESTAMP)
    outside = replace(at_boundary, ask=ask + 0.01)
    assert "spread_too_wide" in contract_rejection_reasons(outside, lane, FIXTURE_TIMESTAMP)


def test_stale_quote_and_low_liquidity_are_hard_rejections() -> None:
    lane = PROFILE.lane(StrategyLane.LEADER_SWING)
    contract = replace(
        _leader_contract(),
        open_interest=lane.minimum_open_interest - 1,
        quote_timestamp=FIXTURE_TIMESTAMP - timedelta(minutes=31),
    )
    reasons = contract_rejection_reasons(contract, lane, FIXTURE_TIMESTAMP)
    assert "open_interest_below_minimum" in reasons
    assert "quote_stale" in reasons
    assert score_contract(contract, lane, FIXTURE_TIMESTAMP) == 0


def test_indicative_feed_can_score_but_is_not_trustworthy() -> None:
    provider = FixtureDataProvider("technical_watch")
    lane = PROFILE.lane(StrategyLane.LEADER_SWING)
    chain = provider.call_chain(
        "SSTR",
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[0]),
        FIXTURE_TIMESTAMP.date() + timedelta(days=lane.hard_dte[1]),
    )
    selection = select_contracts(chain, lane, FIXTURE_TIMESTAMP, 0.25)
    assert selection.score >= 80
    assert not selection.trustworthy
