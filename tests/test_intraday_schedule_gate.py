from datetime import datetime

from scanner.clocks import NY
from scanner.intraday_schedule_gate import intraday_schedule_decision

TARGETS = ("10:45", "12:30", "14:15")


def test_intraday_gate_matches_all_three_entry_windows() -> None:
    entry = intraday_schedule_decision(
        datetime(2026, 7, 16, 10, 50, tzinfo=NY),
        TARGETS,
    )
    midday = intraday_schedule_decision(
        datetime(2026, 7, 16, 12, 35, tzinfo=NY),
        TARGETS,
    )
    final = intraday_schedule_decision(
        datetime(2026, 7, 16, 14, 20, tzinfo=NY),
        TARGETS,
    )
    assert entry.should_run and entry.target == "10:45"
    assert not entry.management_only
    assert midday.should_run and midday.target == "12:30"
    assert not midday.management_only
    assert final.should_run and final.target == "14:15"
    assert not final.management_only


def test_intraday_gate_skips_extra_dst_cron_and_late_start() -> None:
    extra = intraday_schedule_decision(
        datetime(2026, 7, 16, 9, 35, tzinfo=NY),
        TARGETS,
    )
    late = intraday_schedule_decision(
        datetime(2026, 7, 16, 11, 16, tzinfo=NY),
        TARGETS,
    )
    assert not extra.should_run
    assert not late.should_run


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
