from __future__ import annotations

from datetime import date, datetime, time, timedelta

from scanner.clocks import NY

FULL_HOLIDAYS_2026 = {
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
}

HALF_DAYS_2026 = {date(2026, 11, 27), date(2026, 12, 24)}


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in FULL_HOLIDAYS_2026


def is_half_day(day: date) -> bool:
    return day in HALF_DAYS_2026


def next_trading_day(after_day: date) -> date:
    candidate = after_day + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def market_close_for(day: date) -> datetime:
    close = time(13, 0) if is_half_day(day) else time(16, 0)
    return datetime.combine(day, close, tzinfo=NY)


def assert_completed_daily(candle_timestamp: datetime, as_of: datetime) -> None:
    local = as_of.astimezone(NY)
    if not is_trading_day(candle_timestamp.astimezone(NY).date()):
        raise ValueError("Daily candle timestamp is not a trading day.")
    if local <= market_close_for(local.date()):
        raise ValueError("Daily candle is not completed.")
