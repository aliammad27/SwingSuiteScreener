from scanner.momentum import calculate_momentum, strict_daily_filter
from scanner.providers.fixtures import FixtureDataProvider


def test_strict_daily_filter() -> None:
    provider = FixtureDataProvider()
    momentum = calculate_momentum("SSTR", provider.daily("SSTR"), "1D", True)
    assert strict_daily_filter(momentum) is True


def test_four_hour_bullish_confirmation_requires_daily_filter() -> None:
    provider = FixtureDataProvider()
    blocked = calculate_momentum("SSTR", provider.four_hour("SSTR"), "4H", False)
    assert blocked.bullish_confirmation is False
    assert blocked.state == "HTF blocked" or blocked.daily_filter_passed is False
