from datetime import datetime

from scanner.clocks import NY
from scanner.intraday_schedule_gate import intraday_schedule_decision

TARGETS = ("10:35", "11:35", "12:35", "13:35", "14:35", "15:35")


def test_intraday_gate_matches_entry_and_management_windows() -> None:
    entry = intraday_schedule_decision(
        datetime(2026, 7, 16, 14, 40, tzinfo=NY),
        TARGETS,
    )
    management = intraday_schedule_decision(
        datetime(2026, 7, 16, 15, 40, tzinfo=NY),
        TARGETS,
    )
    assert entry.should_run and entry.target == "14:35"
    assert not entry.management_only
    assert management.should_run and management.target == "15:35"
    assert management.management_only


def test_intraday_gate_skips_extra_dst_cron_and_late_start() -> None:
    extra = intraday_schedule_decision(
        datetime(2026, 7, 16, 9, 35, tzinfo=NY),
        TARGETS,
    )
    late = intraday_schedule_decision(
        datetime(2026, 7, 16, 11, 6, tzinfo=NY),
        TARGETS,
    )
    assert not extra.should_run
    assert not late.should_run
