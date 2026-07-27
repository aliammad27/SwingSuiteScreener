from dataclasses import replace

from scanner.models import OpportunityTier, ScanType
from scanner.opportunity import detect_catalyst_signal
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import run_scan
from scanner.strategy_profile import PROFILE


def test_core_and_asymmetric_fixtures_receive_explicit_tiers() -> None:
    s_tier = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready").ready_verify[0]
    a_plus = run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready_verify",
    ).ready_verify[0]
    asymmetric = run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="developing",
    ).developing[0]

    assert s_tier.opportunity_tier == OpportunityTier.S_TIER
    assert a_plus.opportunity_tier == OpportunityTier.A_PLUS
    assert asymmetric.opportunity_tier == OpportunityTier.ASYMMETRIC
    assert "asymmetric_research_only" in asymmetric.reasons


def test_contract_economics_include_expected_move_and_spread_comparison() -> None:
    candidate = run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    ).ready_verify[0]
    economics = candidate.contract_economics

    assert economics is not None
    assert economics.expected_move is not None
    assert economics.target_to_expected_move is not None
    assert economics.target_to_expected_move > 1
    assert economics.long_call_breakeven > candidate.contracts.primary.strike
    assert economics.theta_cost_percent is not None
    assert economics.spread_short_strike is not None
    assert economics.spread_debit is not None
    assert economics.spread_max_profit is not None
    assert economics.spread_reward_to_risk is not None


def test_gap_continuation_uses_completed_price_and_volume_evidence() -> None:
    candles = FixtureDataProvider("ready").daily("SSTR")[-30:]
    previous = candles[-2]
    average_volume = sum(candle.volume for candle in candles[-21:-1]) / 20
    candles[-1] = replace(
        candles[-1],
        open=previous.close + 2.0,
        high=previous.close + 3.2,
        low=previous.close + 1.2,
        close=previous.close + 3.0,
        volume=round(average_volume * 2),
    )

    signal = detect_catalyst_signal(candles, atr=2.0, profile=PROFILE)

    assert signal is not None
    assert signal.kind == "gap_continuation"
    assert signal.gap_atr == 1.0
    assert signal.relative_volume >= 1.5
    assert signal.held_gap_midpoint
    assert not signal.event_verified
