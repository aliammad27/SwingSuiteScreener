from scanner.daily_command import calculate_command
from scanner.providers.fixtures import FixtureDataProvider


def test_command_score_maximum_and_components() -> None:
    provider = FixtureDataProvider()
    result = calculate_command(
        "SSTR", provider.daily("SSTR"), provider.daily("QQQ"), provider.weekly("SSTR")
    )
    assert result.score == 100
    assert result.ema21 > result.sma50
    assert result.sma50 > result.sma200
    assert result.call_bias in {"Pullback setup", "Breakout confirmed", "Bullish", "Breakout watch"}


def test_ema9_not_used_by_command_center() -> None:
    import inspect

    import scanner.daily_command as command

    source = inspect.getsource(command)
    assert "ema9" not in source.lower()
    assert "EMA 9" not in source


def test_breakout_lookback_excludes_current_bar() -> None:
    provider = FixtureDataProvider()
    daily = provider.daily("SSTR")
    previous_high = max(c.high for c in daily[-21:-1])
    daily[-1] = type(daily[-1])(
        **{**daily[-1].__dict__, "high": previous_high + 100, "close": previous_high - 1}
    )
    result = calculate_command("SSTR", daily, provider.daily("QQQ"), provider.weekly("SSTR"))
    assert result.breakout_level == previous_high


def test_breakout_confirmed_bias_requires_volume() -> None:
    provider = FixtureDataProvider()
    daily = provider.daily("SSTR")
    previous_high = max(c.high for c in daily[-21:-1])
    daily[-2] = type(daily[-2])(**{**daily[-2].__dict__, "close": previous_high - 1})
    daily[-1] = type(daily[-1])(
        **{
            **daily[-1].__dict__,
            "open": previous_high - 0.50,
            "high": previous_high + 2,
            "close": previous_high + 1,
            "volume": 1,
        }
    )
    result = calculate_command("SSTR", daily, provider.daily("QQQ"), provider.weekly("SSTR"))

    assert result.breakout_confirmed is True
    assert result.call_bias != "Breakout confirmed"


def test_extended_price_detection() -> None:
    provider = FixtureDataProvider()
    result = calculate_command(
        "ZERO", provider.daily("ZERO"), provider.daily("QQQ"), provider.weekly("ZERO")
    )
    assert "below_sma200" in result.rejection_reasons
