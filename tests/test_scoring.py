from scanner.market_regime import classify_market_regime
from scanner.models import Grade
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol


def _fixture_grade(symbol: str):
    provider = FixtureDataProvider()
    regime = classify_market_regime(provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY"))
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
