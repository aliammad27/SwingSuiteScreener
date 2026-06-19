from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_new_york(value: datetime) -> datetime:
    return value.astimezone(NY)


def format_et(value: datetime) -> str:
    return to_new_york(value).strftime("%-I:%M %p ET")
