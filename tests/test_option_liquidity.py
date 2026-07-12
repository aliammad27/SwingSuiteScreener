from datetime import UTC, datetime

from scanner.models import OptionQuote
from scanner.option_liquidity import (
    classify_option_liquidity,
    classify_put_option_liquidity,
)


def test_option_liquidity_classifications() -> None:
    now = datetime.now(UTC)
    assert (
        classify_option_liquidity([OptionQuote("X", 45, 0.55, 4.0, 4.2, 800, 200, 50, now)])
        == "Good"
    )
    assert (
        classify_option_liquidity([OptionQuote("X", 45, 0.55, 4.0, 4.42, 800, 200, 50, now)])
        == "Acceptable"
    )
    assert (
        classify_option_liquidity([OptionQuote("X", 5, 0.10, 1.0, 1.5, 10, 1, 90, now)]) == "Poor"
    )
    assert classify_option_liquidity([]) == "Unknown"


def test_dte_rules() -> None:
    now = datetime.now(UTC)
    # One miss (DTE 28) remains inside the 21-75 hard window.
    assert (
        classify_option_liquidity([OptionQuote("X", 28, 0.55, 4.0, 4.2, 800, 200, 50, now)])
        == "Acceptable"
    )
    # DTE outside the 21-75 hard bounds.
    assert (
        classify_option_liquidity([OptionQuote("X", 90, 0.55, 4.0, 4.2, 800, 200, 50, now)])
        == "Poor"
    )


def test_delta_hard_floor_causes_poor() -> None:
    now = datetime.now(UTC)
    # Everything else perfect, but call delta below the 0.35 hard floor.
    assert (
        classify_option_liquidity([OptionQuote("X", 45, 0.34, 4.0, 4.2, 800, 200, 50, now)])
        == "Poor"
    )
    assert (
        classify_put_option_liquidity([OptionQuote("X", 17, -0.19, 2.0, 2.1, 800, 200, 50, now)])
        == "Poor"
    )
    # At the call floor exactly, the preferred-band miss is acceptable.
    assert (
        classify_option_liquidity([OptionQuote("X", 45, 0.35, 4.0, 4.2, 800, 200, 50, now)])
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
