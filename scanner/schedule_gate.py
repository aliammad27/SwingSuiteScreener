from __future__ import annotations

import argparse
import time as sleep_time
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal

from scanner.clocks import NY

GateAction = Literal["wait", "run", "late"]


@dataclass(frozen=True)
class GateDecision:
    action: GateAction
    wait_seconds: int
    message: str


def parse_target_time(value: str) -> time:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError("Target time must use HH:MM format.") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Target time must use 00:00 through 23:59.")
    return time(hour=hour, minute=minute)


def _target_datetime(now: datetime, target: time, max_early_minutes: int) -> datetime:
    local_now = now.astimezone(NY)
    target_at = local_now.replace(
        hour=target.hour,
        minute=target.minute,
        second=0,
        microsecond=0,
    )
    if local_now < target_at:
        early_by = target_at - local_now
        if early_by > timedelta(minutes=max_early_minutes):
            return target_at - timedelta(days=1)
    return target_at


def gate_decision(
    *,
    now: datetime,
    target: time,
    max_late_minutes: int,
    max_early_minutes: int = 720,
) -> GateDecision:
    local_now = now.astimezone(NY)
    target_at = _target_datetime(local_now, target, max_early_minutes)
    if local_now < target_at:
        wait_seconds = int((target_at - local_now).total_seconds())
        return GateDecision(
            "wait",
            wait_seconds,
            (
                "Waiting until "
                f"{target_at.strftime('%Y-%m-%d %I:%M %p %Z')} "
                f"({wait_seconds} seconds)."
            ),
        )
    latest_allowed = target_at + timedelta(minutes=max_late_minutes)
    if local_now <= latest_allowed:
        return GateDecision(
            "run",
            0,
            f"Within allowed schedule window for {target_at.strftime('%Y-%m-%d %I:%M %p %Z')}.",
        )
    late_by = int((local_now - target_at).total_seconds() // 60)
    return GateDecision(
        "late",
        0,
        (
            "GitHub started this job too late for the intended market window: "
            f"target was {target_at.strftime('%Y-%m-%d %I:%M %p %Z')}, "
            f"current time is {local_now.strftime('%Y-%m-%d %I:%M %p %Z')}, "
            f"late by {late_by} minutes."
        ),
    )


def hold_decision(
    *,
    now: datetime,
    target: time,
    max_late_minutes: int,
    max_early_minutes: int = 720,
) -> GateDecision:
    local_now = now.astimezone(NY)
    target_at = _target_datetime(local_now, target, max_early_minutes)
    close_at = target_at + timedelta(minutes=max_late_minutes, seconds=30)
    if local_now < close_at:
        wait_seconds = int((close_at - local_now).total_seconds())
        return GateDecision(
            "wait",
            wait_seconds,
            (
                "Holding the schedule window open until "
                f"{close_at.strftime('%Y-%m-%d %I:%M %p %Z')} "
                f"({wait_seconds} seconds)."
            ),
        )
    return GateDecision("run", 0, "Schedule window is already closed.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Eastern target time in HH:MM format.")
    parser.add_argument("--max-late-minutes", type=int, default=20)
    parser.add_argument("--max-early-minutes", type=int, default=720)
    parser.add_argument(
        "--hold-window-open",
        action="store_true",
        help="Sleep until the late window closes so queued backup schedules cannot duplicate alerts.",
    )
    args = parser.parse_args()

    now = datetime.now(NY)
    target = parse_target_time(args.target)
    if args.hold_window_open:
        decision = hold_decision(
            now=now,
            target=target,
            max_late_minutes=args.max_late_minutes,
            max_early_minutes=args.max_early_minutes,
        )
        print(decision.message, flush=True)
        if decision.action == "wait":
            sleep_time.sleep(decision.wait_seconds)
            print("Schedule window closed.", flush=True)
        return 0

    decision = gate_decision(
        now=now,
        target=target,
        max_late_minutes=args.max_late_minutes,
        max_early_minutes=args.max_early_minutes,
    )
    print(decision.message, flush=True)
    if decision.action == "wait":
        sleep_time.sleep(decision.wait_seconds)
        print("Reached scheduled Eastern market time.", flush=True)
        return 0
    if decision.action == "run":
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
