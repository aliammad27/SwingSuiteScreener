from datetime import UTC, datetime

from scanner.models import OptionQuote
from scanner.option_liquidity import (
    classify_option_liquidity,
    classify_put_option_liquidity,
)


def test_option_liquidity_classifications() -> None:
    now = datetime.now(UTC)
    assert (
        classify_option_liquidity([OptionQuote("X", 17, 0.30, 2.0, 2.1, 800, 200, 50, now)])
        == "Good"
    )
    assert (
        classify_option_liquidity([OptionQuote("X", 17, 0.30, 2.0, 2.22, 800, 200, 50, now)])
        == "Acceptable"
    )
    assert (
        classify_option_liquidity([OptionQuote("X", 5, 0.10, 1.0, 1.5, 10, 1, 90, now)]) == "Poor"
    )
    assert classify_option_liquidity([]) == "Unknown"


def test_dte_rules() -> None:
    now = datetime.now(UTC)
    # One miss (DTE 13, just below the 14-21 window) inside the 10-25 near window
    assert (
        classify_option_liquidity([OptionQuote("X", 13, 0.30, 2.0, 2.1, 800, 200, 50, now)])
        == "Acceptable"
    )
    # DTE outside the 10-25 hard bounds
    assert (
        classify_option_liquidity([OptionQuote("X", 30, 0.30, 2.0, 2.1, 800, 200, 50, now)])
        == "Poor"
    )


def test_delta_hard_floor_causes_poor() -> None:
    now = datetime.now(UTC)
    # Everything else perfect, but absolute delta below 0.20
    assert (
        classify_option_liquidity([OptionQuote("X", 17, 0.19, 2.0, 2.1, 800, 200, 50, now)])
        == "Poor"
    )
    assert (
        classify_put_option_liquidity([OptionQuote("X", 17, -0.19, 2.0, 2.1, 800, 200, 50, now)])
        == "Poor"
    )
    # At the floor exactly, the floor does not fire (one-miss delta window applies)
    assert (
        classify_option_liquidity([OptionQuote("X", 17, 0.20, 2.0, 2.1, 800, 200, 50, now)])
        == "Acceptable"
    )


def test_put_option_liquidity_classifications() -> None:
    now = datetime.now(UTC)
    assert (
        classify_put_option_liquidity(
            [OptionQuote("X", 17, -0.30, 2.0, 2.1, 800, 200, 50, now)]
        )
        == "Good"
    )
    assert (
        classify_put_option_liquidity(
            [OptionQuote("X", 17, -0.30, 2.0, 2.22, 800, 200, 50, now)]
        )
        == "Acceptable"
    )
    assert classify_put_option_liquidity([]) == "Unknown"
