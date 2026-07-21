from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from scanner.calendars import is_trading_day, market_close_for
from scanner.clocks import NY
from scanner.config import load_config
from scanner.schedule_gate import parse_target_time
from scanner.strategy_profile import PROFILE


@dataclass(frozen=True)
class IntradayScheduleDecision:
    should_run: bool
    target: str | None
    management_only: bool
    reason: str


def intraday_schedule_decision(
    now: datetime,
    targets: tuple[str, ...],
    *,
    maximum_late_minutes: int = 30,
) -> IntradayScheduleDecision:
    local = now.astimezone(NY)
    if not is_trading_day(local.date()):
        return IntradayScheduleDecision(False, None, False, "Not an NYSE trading session.")
    if local >= market_close_for(local.date()):
        return IntradayScheduleDecision(False, None, False, "The NYSE session is closed.")
    entry_end = parse_target_time(PROFILE.entry_window_end_et)
    for target_text in reversed(targets):
        target_time = parse_target_time(target_text)
        target_at = local.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0,
        )
        if target_at <= local <= target_at + timedelta(minutes=maximum_late_minutes):
            management_only = target_time > entry_end
            return IntradayScheduleDecision(
                True,
                target_text,
                management_only,
                (
                    f"Matched {target_text} ET intraday window"
                    + (" (management only)." if management_only else ".")
                ),
            )
    return IntradayScheduleDecision(
        False,
        None,
        False,
        "No configured ET intraday target is inside the allowed late window.",
    )


def _write_github_output(decision: IntradayScheduleDecision) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"should_run={'true' if decision.should_run else 'false'}\n")
        output.write(f"target={decision.target or ''}\n")
        output.write(f"management_only={'true' if decision.management_only else 'false'}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-match",
        action="store_true",
        help="Return a nonzero status when no configured ET scan window matches.",
    )
    args = parser.parse_args()
    schedule = load_config("schedule")
    raw_targets = schedule.get("intraday_scan_times", [])
    targets = tuple(str(value) for value in raw_targets)
    decision = intraday_schedule_decision(datetime.now(NY), targets)
    print(decision.reason)
    _write_github_output(decision)
    return 0 if decision.should_run or not args.require_match else 2


if __name__ == "__main__":
    raise SystemExit(main())
