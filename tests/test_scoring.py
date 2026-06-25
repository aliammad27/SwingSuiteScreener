from dataclasses import replace as dc_replace

from scanner.grading import grade_candidate
from scanner.market_regime import classify_market_regime
from scanner.models import Grade
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol


def _fixture_grade(symbol: str):
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    return _scan_symbol(symbol, provider, provider, provider, regime)


def test_s_tier_requirements() -> None:
    candidate = _fixture_grade("SSTR")
    assert candidate.grade == Grade.S_TIER
    assert candidate.command.score >= 85
    assert candidate.four_hour_momentum.score >= 85


def test_a_plus_one_missing_confirmation_rule() -> None:
    candidate = _fixture_grade("APLUS")
    assert candidate.grade == Grade.A_PLUS
    assert candidate.option_liquidity == "Acceptable"


def test_zero_candidate_rejected() -> None:
    candidate = _fixture_grade("ZERO")
    assert candidate.grade == Grade.REJECTED
    assert candidate.rejection_reasons


def test_free_mode_technical_watch_when_option_liquidity_missing() -> None:
    provider = FixtureDataProvider(scenario="technical_watch")
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    assert candidate.grade == Grade.TECHNICAL_WATCH
    assert candidate.option_liquidity == "Unknown"
    assert "option liquidity" in (candidate.missing_confirmation or "").lower()


def test_b_tier_not_rejected_when_scores_developing() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    candidate = _scan_symbol("APLUS", provider, provider, provider, regime)
    lower_command = dc_replace(candidate.command, score=68)
    lower_daily = dc_replace(candidate.daily_momentum, score=60)
    lower_4h = dc_replace(candidate.four_hour_momentum, score=65)
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
