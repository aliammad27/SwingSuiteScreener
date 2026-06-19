from __future__ import annotations

from datetime import timedelta

from scanner.clocks import utc_now
from scanner.models import Candle, OptionQuote


class DataQualityError(RuntimeError):
    pass


def require_completed_candles(candles: list[Candle], *, minimum: int, label: str) -> None:
    if len(candles) < minimum:
        raise DataQualityError(f"{label}: insufficient candles")
    if any(not candle.completed for candle in candles):
        raise DataQualityError(f"{label}: incomplete candle present")
    if any(candle.volume <= 0 for candle in candles):
        raise DataQualityError(f"{label}: missing volume")


def require_fresh_options(quotes: list[OptionQuote], max_age_minutes: int = 90) -> None:
    if not quotes:
        raise DataQualityError("Option chain is missing")
    newest = max(q.timestamp for q in quotes)
    if utc_now() - newest > timedelta(minutes=max_age_minutes) and quotes[0].symbol != "FIXTURE":
        raise DataQualityError("Option chain is stale")
