from scanner.evidence import analyze_trend, annualized_realized_volatility, calculate_leadership
from scanner.providers.fixtures import FixtureDataProvider
from scanner.strategy_profile import PROFILE


def test_trend_evidence_is_separate_and_bounded() -> None:
    provider = FixtureDataProvider("ready")
    trend = analyze_trend(provider.daily("SSTR"), provider.weekly("SSTR"), PROFILE)
    assert trend.score == 100
    assert trend.close > trend.ema21 > trend.sma50 > trend.sma200
    assert trend.weekly_aligned
    assert not trend.hard_failures


def test_below_sma200_is_a_hard_failure() -> None:
    provider = FixtureDataProvider("zero")
    trend = analyze_trend(provider.daily("ZERO"), provider.weekly("ZERO"), PROFILE)
    assert trend.score < 60
    assert "below_sma200" in trend.hard_failures


def test_leadership_compares_stock_peer_and_spy() -> None:
    provider = FixtureDataProvider("ready")
    score = calculate_leadership(
        provider.daily("SSTR"), provider.daily("XLK"), provider.daily("SPY")
    )
    assert score >= 70


def test_realized_volatility_is_annualized_and_positive() -> None:
    provider = FixtureDataProvider("ready")
    value = annualized_realized_volatility(provider.daily("SSTR"))
    assert value is not None
    assert value > 0
