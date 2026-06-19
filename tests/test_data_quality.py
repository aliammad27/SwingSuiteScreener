from dataclasses import replace

import pytest

from scanner.data_quality import DataQualityError, require_completed_candles
from scanner.providers.fixtures import FixtureDataProvider


def test_incomplete_candle_rejection() -> None:
    candles = FixtureDataProvider().daily("SSTR")
    candles[-1] = replace(candles[-1], completed=False)
    with pytest.raises(DataQualityError):
        require_completed_candles(candles, minimum=220, label="daily")


def test_missing_volume_rejection() -> None:
    candles = FixtureDataProvider().daily("SSTR")
    candles[-1] = replace(candles[-1], volume=0)
    with pytest.raises(DataQualityError):
        require_completed_candles(candles, minimum=220, label="daily")
