"""Tests for put candidate grading logic."""
from __future__ import annotations

from dataclasses import replace as dc_replace

from scanner.market_regime import classify_market_regime
from scanner.models import Grade
from scanner.providers.fixtures import FixtureDataProvider
from scanner.put_grading import grade_put_candidate
from scanner.run_scan import _scan_put_symbol


def _fixture_put_grade(symbol: str, scenario: str):
    prov = FixtureDataProvider(scenario)
    regime = classify_market_regime(
        prov.daily("SPY"), prov.daily("QQQ"), prov.weekly("SPY")
    )
    return _scan_put_symbol(symbol, prov, prov, prov, regime)


# ---------------------------------------------------------------------------
# S-Put tier
# ---------------------------------------------------------------------------

def test_sput_is_s_tier() -> None:
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert candidate.grade == Grade.S_TIER


def test_sput_s_tier_has_good_option_liquidity() -> None:
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert candidate.option_liquidity == "Good"


def test_sput_s_tier_daily_score_at_least_80() -> None:
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert candidate.daily_momentum.score >= 80


def test_sput_s_tier_four_hour_score_at_least_85() -> None:
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert candidate.four_hour_momentum.score >= 85


def test_sput_s_tier_no_rejection_reasons() -> None:
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert not candidate.rejection_reasons


def test_s_tier_blocked_in_supportive_regime() -> None:
    """A supportive market regime must prevent S-Put tier."""
    prov = FixtureDataProvider("put_s_tier")
    # Neutral / supportive regime by forcing default (bullish) SPY/QQQ
    prov_default = FixtureDataProvider("default")
    regime = classify_market_regime(
        prov_default.daily("SPY"), prov_default.daily("QQQ"), prov_default.weekly("SPY")
    )
    candidate = _scan_put_symbol("SPUT", prov, prov, prov, regime)
    assert candidate.grade != Grade.S_TIER


# ---------------------------------------------------------------------------
# A-Plus Put tier
# ---------------------------------------------------------------------------

def test_aput_is_a_plus() -> None:
    candidate = _fixture_put_grade("APUT", "put_a_plus")
    assert candidate.grade == Grade.A_PLUS


def test_aput_a_plus_daily_score_at_least_70() -> None:
    candidate = _fixture_put_grade("APUT", "put_a_plus")
    assert candidate.daily_momentum.score >= 70


def test_aput_a_plus_four_hour_score_at_least_75() -> None:
    candidate = _fixture_put_grade("APUT", "put_a_plus")
    assert candidate.four_hour_momentum.score >= 75


# ---------------------------------------------------------------------------
# B-Put tier
# ---------------------------------------------------------------------------

def test_bput_is_b_tier() -> None:
    candidate = _fixture_put_grade("BPUT", "put_b_tier")
    assert candidate.grade == Grade.B_TIER


def test_bput_b_tier_daily_score_at_least_55() -> None:
    candidate = _fixture_put_grade("BPUT", "put_b_tier")
    assert candidate.daily_momentum.score >= 55


def test_bput_b_tier_four_hour_score_at_least_60() -> None:
    candidate = _fixture_put_grade("BPUT", "put_b_tier")
    assert candidate.four_hour_momentum.score >= 60


# ---------------------------------------------------------------------------
# Market regime inversion
# ---------------------------------------------------------------------------

def test_hostile_market_is_put_supportive() -> None:
    """A Hostile market regime (bearish SPY/QQQ) must allow put grades."""
    prov = FixtureDataProvider("put_s_tier")
    regime = classify_market_regime(
        prov.daily("SPY"), prov.daily("QQQ"), prov.weekly("SPY")
    )
    assert regime == "Hostile"


def test_supportive_market_blocks_put_s_tier() -> None:
    """Supportive regime must block S-Put tier via automatic rejection."""
    prov = FixtureDataProvider("put_s_tier")
    regime = "Supportive"
    candidate = _scan_put_symbol("SPUT", prov, prov, prov, regime)
    assert "supportive_market_blocks_puts" in candidate.rejection_reasons
    assert candidate.grade != Grade.S_TIER


# ---------------------------------------------------------------------------
# Grade boundaries
# ---------------------------------------------------------------------------

def test_put_rejected_when_daily_score_too_low() -> None:
    """Command score below 60 must reject automatically."""
    prov = FixtureDataProvider("put_s_tier")
    regime = classify_market_regime(
        prov.daily("SPY"), prov.daily("QQQ"), prov.weekly("SPY")
    )
    candidate = _scan_put_symbol("SPUT", prov, prov, prov, regime)
    low_cmd = dc_replace(candidate.command, score=50)
    low_cmd = dc_replace(low_cmd, rejection_reasons=["put_command_score_below_60"])
    result = grade_put_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        low_cmd,
        candidate.daily_momentum,
        candidate.four_hour_momentum,
        candidate.option_liquidity,
        candidate.catalyst,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
    assert "put_command_score_below_60" in result.rejection_reasons


def test_put_downside_target_below_current_price() -> None:
    """Entry plan target price must be below current close for a put."""
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert candidate.entry_plan.target_price < candidate.command.close


def test_put_target_gain_positive() -> None:
    """Target gain percent must be positive (stock must fall for put to profit)."""
    candidate = _fixture_put_grade("SPUT", "put_s_tier")
    assert candidate.entry_plan.target_gain_percent > 0
