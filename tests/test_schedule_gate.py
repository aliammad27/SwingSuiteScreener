from datetime import datetime

import pytest

from scanner.clocks import NY
from scanner.schedule_gate import gate_decision, parse_target_time


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


def test_parse_target_time_rejects_invalid_time() -> None:
    with pytest.raises(ValueError):
        parse_target_time("25:00")
