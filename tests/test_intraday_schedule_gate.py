from datetime import datetime

from scanner.clocks import NY
from scanner.intraday_schedule_gate import intraday_schedule_decision

TARGETS = ("12:30",)


def test_intraday_gate_matches_midday_entry_window() -> None:
    midday = intraday_schedule_decision(
        datetime(2026, 7, 16, 12, 35, tzinfo=NY),
        TARGETS,
    )
    assert midday.should_run and midday.target == "12:30"
    assert not midday.management_only


def test_intraday_gate_skips_removed_windows_and_late_start() -> None:
    old_open = intraday_schedule_decision(
        datetime(2026, 7, 16, 10, 50, tzinfo=NY),
        TARGETS,
    )
    recovered = intraday_schedule_decision(
        datetime(2026, 7, 16, 14, 44, tzinfo=NY),
        TARGETS,
    )
    after_cutoff = intraday_schedule_decision(
        datetime(2026, 7, 16, 14, 46, tzinfo=NY),
        TARGETS,
    )
    assert not old_open.should_run
    assert recovered.should_run
    assert recovered.target == "12:30"
    assert not after_cutoff.should_run


def test_intraday_gate_skips_exchange_holiday_and_closed_session() -> None:
    holiday = intraday_schedule_decision(
        datetime(2026, 7, 3, 10, 40, tzinfo=NY),
        TARGETS,
    )
    closed = intraday_schedule_decision(
        datetime(2026, 7, 16, 16, 5, tzinfo=NY),
        TARGETS,
    )

    assert not holiday.should_run
    assert holiday.reason == "Not an NYSE trading session."
    assert not closed.should_run
    assert closed.reason == "The NYSE session is closed."
