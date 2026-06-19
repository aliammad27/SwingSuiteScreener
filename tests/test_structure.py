from scanner.providers.fixtures import FixtureDataProvider
from scanner.structure import classify_structure, confirmed_pivot_highs, confirmed_pivot_lows


def test_confirmed_pivots_exist_in_fixture() -> None:
    candles = FixtureDataProvider().daily("SSTR")
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    assert confirmed_pivot_highs(highs, 5, 3)
    assert confirmed_pivot_lows(lows, 5, 3)
    assert classify_structure(highs, lows) in {"Bullish", "Improving", "Mixed", "Bearish"}
