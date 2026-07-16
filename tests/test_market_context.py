from scanner.market_context import calculate_market_context, classify_market_regime
from scanner.providers.fixtures import FixtureDataProvider
from scanner.strategy_profile import PROFILE


def test_market_regime_threshold_boundaries() -> None:
    assert classify_market_regime(100, PROFILE) == "Supportive"
    assert classify_market_regime(70, PROFILE) == "Supportive"
    assert classify_market_regime(69, PROFILE) == "Mixed"
    assert classify_market_regime(45, PROFILE) == "Mixed"
    assert classify_market_regime(44, PROFILE) == "Hostile"


def test_market_context_uses_five_twenty_point_components() -> None:
    provider = FixtureDataProvider()
    context = calculate_market_context(
        provider,
        ["SSTR", "APLUS", "BTIER", "ZERO"],
        PROFILE,
    )
    assert set(context.components) == {
        "spy_daily",
        "qqq_daily",
        "weekly_alignment",
        "breadth_above_sma50",
        "breadth_above_ema21",
    }
    assert all(0 <= component <= 20 for component in context.components.values())
    assert context.score == sum(context.components.values())
