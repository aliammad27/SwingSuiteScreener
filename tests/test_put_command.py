"""Tests for the put command center (bearish daily selection)."""
from __future__ import annotations

from scanner.put_command import calculate_put_command, _relative_weakness
from scanner.providers.fixtures import FixtureDataProvider


def _put_cmd(symbol: str, scenario: str = "default"):
    prov = FixtureDataProvider(scenario)
    return calculate_put_command(
        symbol,
        prov.daily(symbol),
        prov.daily("QQQ"),
        prov.weekly(symbol),
    )


def test_sput_score_at_least_85() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.score >= 85


def test_sput_has_leading_relative_weakness() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.relative_weakness == "Leading"


def test_sput_close_below_sma200() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.close < cmd.sma200


def test_sput_below_vwap() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.below_vwap


def test_sput_weekly_bearish_alignment() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.weekly_alignment  # True means close < weekly EMA21


def test_sput_not_extended_downside() -> None:
    """Extended downside (like extended upside for calls) blocks S-Put tier."""
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert not cmd.extended_downside


def test_sput_bearish_valid_bias() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.put_bias in {"Bearish", "Breakdown confirmed", "Rejection setup"}


def test_bput_score_at_least_65() -> None:
    cmd = _put_cmd("BPUT", "put_b_tier")
    assert cmd.score >= 65


def test_bput_close_below_sma200() -> None:
    cmd = _put_cmd("BPUT", "put_b_tier")
    assert cmd.close < cmd.sma200


def test_breakdown_level_excludes_current_bar() -> None:
    """Breakdown level must use lows[-21:-1], not including the last bar."""
    prov = FixtureDataProvider("put_s_tier")
    daily = prov.daily("SPUT")
    bench = prov.daily("QQQ")
    weekly = prov.weekly("SPUT")
    cmd = calculate_put_command("SPUT", daily, bench, weekly)
    lows = [c.low for c in daily]
    expected = min(lows[-21:-1])
    assert cmd.breakdown_level == expected


def test_relative_weakness_leading_when_stock_underperforms_and_falling() -> None:
    n = 100
    # Stock closes falling, benchmark flat
    stock = [100.0 - i * 0.5 for i in range(n)]
    bench = [100.0] * n
    assert _relative_weakness(stock, bench) == "Leading"


def test_relative_weakness_lagging_when_stock_outperforms() -> None:
    n = 100
    # Stock rising, benchmark flat
    stock = [100.0 + i * 0.5 for i in range(n)]
    bench = [100.0] * n
    assert _relative_weakness(stock, bench) == "Lagging"


def test_put_command_score_max_100() -> None:
    cmd = _put_cmd("SPUT", "put_s_tier")
    assert cmd.score <= 100


def test_avoid_bias_when_above_sma200() -> None:
    """Scores below 45 or price above SMA200 must produce Avoid bias."""
    prov = FixtureDataProvider("default")
    # SSTR is a bullish fixture — its put command should be Avoid
    cmd = _put_cmd("SSTR", "default")
    assert cmd.put_bias == "Avoid"
