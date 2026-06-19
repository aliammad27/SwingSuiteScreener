from datetime import UTC, datetime

from scanner.models import OptionQuote
from scanner.option_liquidity import classify_option_liquidity


def test_option_liquidity_classifications() -> None:
    now = datetime.now(UTC)
    assert classify_option_liquidity([OptionQuote("X", 38, 0.55, 2.0, 2.1, 800, 200, 50, now)]) == "Good"
    assert (
        classify_option_liquidity([OptionQuote("X", 38, 0.55, 2.0, 2.22, 800, 200, 50, now)])
        == "Acceptable"
    )
    assert classify_option_liquidity([OptionQuote("X", 10, 0.20, 1.0, 1.5, 10, 1, 90, now)]) == "Poor"
    assert classify_option_liquidity([]) == "Unknown"


def test_dte_rules() -> None:
    now = datetime.now(UTC)
    assert classify_option_liquidity([OptionQuote("X", 29, 0.55, 2.0, 2.1, 800, 200, 50, now)]) == "Acceptable"
