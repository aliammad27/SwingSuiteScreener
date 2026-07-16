from __future__ import annotations

from datetime import timedelta

from scanner.clocks import utc_now
from scanner.models import Candle, OptionContractSnapshot


class DataQualityError(RuntimeError):
    pass


def require_completed_candles(candles: list[Candle], *, minimum: int, label: str) -> None:
    if len(candles) < minimum:
        raise DataQualityError(f"{label}: insufficient candles")
    if any(not candle.completed for candle in candles):
        raise DataQualityError(f"{label}: incomplete candle present")
    if any(candle.volume <= 0 for candle in candles):
        raise DataQualityError(f"{label}: missing volume")


def require_fresh_options(
    contracts: list[OptionContractSnapshot], max_age_minutes: int = 90
) -> None:
    if not contracts:
        raise DataQualityError("Option chain is missing")
    newest = max(contract.quote_timestamp for contract in contracts)
    if utc_now() - newest > timedelta(minutes=max_age_minutes) and contracts[0].feed != "fixture":
        raise DataQualityError("Option chain is stale")
