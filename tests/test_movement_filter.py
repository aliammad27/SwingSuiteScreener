"""Movement-capability filter tests (aggressive contract profile v2)."""
from __future__ import annotations

from scanner.movement_filter import (
    ATR_BELOW_FLOOR,
    INSUFFICIENT_MOVEMENT,
    movement_filter_reasons,
    required_move_percent,
)


def test_required_move_percent_call() -> None:
    # close 100, strike 105 -> 5% move + 1% cushion = 6%
    assert required_move_percent(100.0, 105.0) == 6.0


def test_required_move_percent_put() -> None:
    # close 100, strike 95 (below) -> 5% move + 1% cushion = 6%
    assert required_move_percent(100.0, 95.0, bearish=True) == 6.0


def test_required_move_clamps_when_price_past_strike() -> None:
    # Call already above strike: only the cushion remains
    assert required_move_percent(110.0, 105.0) == 1.0
    # Put already below strike: only the cushion remains
    assert required_move_percent(90.0, 95.0, bearish=True) == 1.0


def test_target_gain_exactly_at_boundary_passes() -> None:
    # required = 6%, boundary = 9%: exactly at 1.5x passes
    reasons = movement_filter_reasons(100.0, 105.0, 9.0, 3.0)
    assert INSUFFICIENT_MOVEMENT not in reasons


def test_target_gain_just_below_boundary_fails() -> None:
    reasons = movement_filter_reasons(100.0, 105.0, 8.99, 3.0)
    assert INSUFFICIENT_MOVEMENT in reasons


def test_target_gain_boundary_put_side() -> None:
    # put: close 100, strike 95 -> required 6%, boundary 9%
    passing = movement_filter_reasons(100.0, 95.0, 9.0, 3.0, bearish=True)
    failing = movement_filter_reasons(100.0, 95.0, 8.99, 3.0, bearish=True)
    assert INSUFFICIENT_MOVEMENT not in passing
    assert INSUFFICIENT_MOVEMENT in failing


def test_atr_percent_exactly_at_floor_passes() -> None:
    reasons = movement_filter_reasons(100.0, 105.0, 20.0, 2.0)
    assert ATR_BELOW_FLOOR not in reasons


def test_atr_percent_just_below_floor_fails() -> None:
    reasons = movement_filter_reasons(100.0, 105.0, 20.0, 1.99)
    assert ATR_BELOW_FLOOR in reasons


def test_atr_floor_boundary_put_side() -> None:
    passing = movement_filter_reasons(100.0, 95.0, 20.0, 2.0, bearish=True)
    failing = movement_filter_reasons(100.0, 95.0, 20.0, 1.99, bearish=True)
    assert ATR_BELOW_FLOOR not in passing
    assert ATR_BELOW_FLOOR in failing


def test_both_reasons_can_fire_together() -> None:
    reasons = movement_filter_reasons(100.0, 105.0, 1.0, 1.0)
    assert INSUFFICIENT_MOVEMENT in reasons
    assert ATR_BELOW_FLOOR in reasons
