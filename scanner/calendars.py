from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

from scanner.clocks import NY


@lru_cache(maxsize=1)
def _nyse_calendar() -> Any:
    import exchange_calendars as exchange  # type: ignore[import-untyped]

    return exchange.get_calendar("XNYS")


def _session_label(day: date) -> Any:
    import pandas as pd  # type: ignore[import-untyped]

    return pd.Timestamp(day.isoformat())


def is_trading_day(day: date) -> bool:
    return bool(_nyse_calendar().is_session(_session_label(day)))


def is_half_day(day: date) -> bool:
    if not is_trading_day(day):
        return False
    return market_close_for(day).hour < 16


def next_trading_day(after_day: date) -> date:
    candidate = after_day + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def market_close_for(day: date) -> datetime:
    if not is_trading_day(day):
        raise ValueError(f"{day.isoformat()} is not an NYSE trading session.")
    close = _nyse_calendar().session_close(_session_label(day))
    converted = close.to_pydatetime()
    if not isinstance(converted, datetime):
        raise TypeError("NYSE calendar returned an invalid close timestamp.")
    return converted.astimezone(NY)


def assert_completed_daily(candle_timestamp: datetime, as_of: datetime) -> None:
    candle_day = candle_timestamp.astimezone(NY).date()
    if not is_trading_day(candle_day):
        raise ValueError("Daily candle timestamp is not a trading day.")
    if as_of.astimezone(NY) <= market_close_for(candle_day):
        raise ValueError("Daily candle is not completed.")
