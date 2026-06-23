from datetime import datetime

import pytest

from scanner.clocks import NY
from scanner.schedule_gate import gate_decision, hold_decision, parse_target_time


def test_schedule_gate_waits_before_target() -> None:
    decision = gate_decision(
        now=datetime(2026, 6, 22, 8, 40, tzinfo=NY),
        target=parse_target_time("08:45"),
        max_late_minutes=20,
    )

    assert decision.action == "wait"
    assert decision.wait_seconds == 300


def test_schedule_gate_runs_inside_late_window() -> None:
    decision = gate_decision(
        now=datetime(2026, 6, 22, 8, 52, tzinfo=NY),
        target=parse_target_time("08:45"),
        max_late_minutes=20,
    )

    assert decision.action == "run"
    assert decision.wait_seconds == 0


def test_schedule_gate_blocks_when_github_is_too_late() -> None:
    decision = gate_decision(
        now=datetime(2026, 6, 22, 13, 18, tzinfo=NY),
        target=parse_target_time("08:45"),
        max_late_minutes=20,
    )

    assert decision.action == "late"
    assert "too late" in decision.message


def test_schedule_gate_blocks_after_midnight_for_prior_evening_target() -> None:
    decision = gate_decision(
        now=datetime(2026, 6, 23, 0, 10, tzinfo=NY),
        target=parse_target_time("21:00"),
        max_late_minutes=20,
    )

    assert decision.action == "late"
    assert "too late" in decision.message


def test_hold_decision_keeps_window_open_after_success() -> None:
    decision = hold_decision(
        now=datetime(2026, 6, 22, 21, 5, tzinfo=NY),
        target=parse_target_time("21:00"),
        max_late_minutes=20,
    )

    assert decision.action == "wait"
    assert decision.wait_seconds == 930


def test_hold_decision_noops_after_window_closed() -> None:
    decision = hold_decision(
        now=datetime(2026, 6, 22, 21, 25, tzinfo=NY),
        target=parse_target_time("21:00"),
        max_late_minutes=20,
    )

    assert decision.action == "run"
    assert decision.wait_seconds == 0


def test_parse_target_time_rejects_invalid_time() -> None:
    with pytest.raises(ValueError):
        parse_target_time("25:00")
