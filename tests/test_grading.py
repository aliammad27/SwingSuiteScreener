from dataclasses import replace

from scanner.grading import grade_candidate
from scanner.market_regime import classify_market_regime
from scanner.models import Grade
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol


def _a_plus_candidate():
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    return _scan_symbol("APLUS", provider, provider, provider, regime)


def test_hostile_market_blocks_primary_grade() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    hostile = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        candidate.command,
        candidate.daily_momentum,
        candidate.four_hour_momentum,
        candidate.option_liquidity,
        candidate.catalyst,
        "Hostile",
        candidate.entry_plan,
    )
    assert hostile.grade == Grade.REJECTED
    assert "hostile_market_regime" in hostile.rejection_reasons


def test_b_tier_developing_setup() -> None:
    candidate = _a_plus_candidate()
    lower_command = replace(candidate.command, score=68)
    lower_daily = replace(candidate.daily_momentum, score=60)
    lower_4h = replace(candidate.four_hour_momentum, score=65)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        lower_command,
        lower_daily,
        lower_4h,
        candidate.option_liquidity,
        candidate.catalyst,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.B_TIER
    assert result.missing_confirmation is not None


def test_b_tier_blocked_by_poor_liquidity() -> None:
    candidate = _a_plus_candidate()
    lower_command = replace(candidate.command, score=68)
    lower_daily = replace(candidate.daily_momentum, score=60)
    lower_4h = replace(candidate.four_hour_momentum, score=65)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        lower_command,
        lower_daily,
        lower_4h,
        "Poor",
        candidate.catalyst,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
    assert "options_illiquid" in result.rejection_reasons


def test_b_tier_blocked_by_hostile_regime() -> None:
    candidate = _a_plus_candidate()
    lower_command = replace(candidate.command, score=68)
    lower_daily = replace(candidate.daily_momentum, score=60)
    lower_4h = replace(candidate.four_hour_momentum, score=65)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        lower_command,
        lower_daily,
        lower_4h,
        candidate.option_liquidity,
        candidate.catalyst,
        "Hostile",
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
    assert "hostile_market_regime" in result.rejection_reasons


def test_major_event_risk_rejects() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    risky = replace(candidate.catalyst, major_event_risk=True)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        candidate.command,
        candidate.daily_momentum,
        candidate.four_hour_momentum,
        candidate.option_liquidity,
        risky,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
