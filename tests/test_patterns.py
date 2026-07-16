from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from scanner.models import Candle, PatternSignal, PatternStatus, TrendAnalysis
from scanner.patterns import (
    _status,
    detect_ascending_triangle,
    detect_breakout_retest,
    detect_bull_flag,
    detect_confirmed_breakout,
    detect_controlled_pullback,
    detect_cup_with_handle,
    detect_double_bottom,
    detect_falling_wedge,
    detect_flat_base,
    detect_inverse_head_and_shoulders,
    detect_rounding_base,
    detect_vcp_tight_base,
)
from scanner.strategy_profile import PROFILE, StrategyProfile

Detector = Callable[[list[Candle], TrendAnalysis, StrategyProfile], PatternSignal | None]
Builder = Callable[[], tuple[list[Candle], list[Candle], TrendAnalysis]]
START = datetime(2025, 1, 2, 21, 0, tzinfo=UTC)


def _candle(
    index: int,
    close: float,
    *,
    high: float | None = None,
    low: float | None = None,
    volume: int = 1_000,
    completed: bool = True,
) -> Candle:
    return Candle(
        symbol="TEST",
        timeframe="1D",
        timestamp=START + timedelta(days=index),
        open=close - 0.10,
        high=high if high is not None else close + 0.30,
        low=low if low is not None else close - 0.30,
        close=close,
        volume=volume,
        completed=completed,
        source="test",
    )


def _trend(candles: list[Candle], **changes: object) -> TrendAnalysis:
    close = candles[-1].close
    values: dict[str, object] = {
        "score": 90,
        "close": close,
        "ema21": close - 2,
        "sma50": close - 4,
        "sma200": close - 8,
        "anchored_vwap": close - 1.5,
        "atr": 1.0,
        "atr_percent": 1.0,
        "weekly_aligned": True,
        "structure": "Bullish",
        "relative_volume": 1.25,
        "breakout_level": close + 0.30,
        "breakout_confirmed": False,
        "pullback_support": close - 0.20,
        "pullback_setup": True,
        "resistance_level": close + 5,
        "extended": False,
        "hard_failures": (),
    }
    values.update(changes)
    return TrendAnalysis(**values)  # type: ignore[arg-type]


def _controlled_pullback() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 99 + index * 0.02) for index in range(40)]
    negative = list(positive)
    trend = _trend(positive)
    return positive, negative, trend


def _confirmed_breakout() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 99.5) for index in range(38)]
    positive.extend([_candle(38, 99.80), _candle(39, 100.20)])
    negative = list(positive)
    trend = _trend(positive, breakout_level=100.0, breakout_confirmed=True)
    return positive, negative, trend


def _bull_flag() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 100.0) for index in range(5)]
    positive.extend(
        _candle(index + 5, 100.0 + index, volume=2_000) for index in range(10)
    )
    for index, close in enumerate((108.8, 108.2, 107.8, 108.1, 108.6), 15):
        positive.append(_candle(index, close, volume=800))
    negative = list(positive)
    negative[-3] = replace(negative[-3], low=100.0)
    return positive, negative, _trend(positive)


def _flat_base() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 99.5) for index in range(5)]
    for index in range(5, 30):
        close = 100.4 + (index - 5) * 0.035
        positive.append(_candle(index, close, high=101.5, low=98.5, volume=900))
    positive[-1] = replace(positive[-1], close=101.3, open=101.1)
    negative = list(positive)
    negative[12] = replace(negative[12], low=80.0)
    return positive, negative, _trend(positive)


def _ascending_triangle() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive: list[Candle] = []
    for index in range(40):
        close = 103.2 + index * 0.015
        positive.append(_candle(index, close, high=close + 0.25, low=close - 0.45))
    for index in (8, 20, 31):
        positive[index] = replace(positive[index], high=105.0)
    positive[12] = replace(positive[12], low=96.0)
    positive[24] = replace(positive[24], low=98.0)
    positive[-1] = replace(positive[-1], close=104.8, open=104.6, high=104.9)
    negative = list(positive)
    negative[24] = replace(negative[24], low=95.0)
    return positive, negative, _trend(positive)


def _vcp() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 103.0) for index in range(10)]
    blocks = ((110.0, 98.0, 1_200), (108.0, 100.0, 1_000), (107.0, 102.0, 600))
    for block, (high, low, volume) in enumerate(blocks):
        for offset in range(20):
            index = 10 + block * 20 + offset
            close = low + (high - low) * (0.60 + offset / 100)
            positive.append(_candle(index, close, high=high, low=low, volume=volume))
    positive[-1] = replace(positive[-1], close=106.8, open=106.6)
    negative = list(positive)
    for index in range(50, 70):
        negative[index] = replace(negative[index], low=98.0)
    return positive, negative, _trend(positive)


def _cup_with_handle() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 118.0, high=119.0, low=116.0) for index in range(10)]
    for cup_index in range(105):
        index = cup_index + 10
        if cup_index < 30:
            positive.append(_candle(index, 118.5, high=120.0, low=115.0))
        elif cup_index < 80:
            low = 90.0 if cup_index == 52 else 100.0
            positive.append(_candle(index, 108.0, high=114.0, low=low))
        else:
            positive.append(_candle(index, 118.2, high=119.0, low=111.0))
    for index in range(115, 130):
        positive.append(_candle(index, 118.7, high=118.9, low=112.0, volume=700))
    negative = list(positive)
    negative[-5] = replace(negative[-5], low=100.0)
    return positive, negative, _trend(positive)


def _breakout_retest() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 99.0, high=100.0, low=98.5) for index in range(45)]
    positive[42] = _candle(42, 101.2, high=101.5, low=99.8, volume=1_500)
    positive[43] = _candle(43, 100.4, high=101.0, low=100.2)
    positive[44] = _candle(44, 100.6, high=100.8, low=100.1)
    negative = list(positive)
    negative[42] = _candle(42, 99.5, high=100.0, low=98.8)
    return positive, negative, _trend(positive)


def _double_bottom() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [
        _candle(
            index,
            104.0 + index * 0.02,
            high=105.5 + index * 0.01,
            low=102.0 + index * 0.01,
            volume=1_000,
        )
        for index in range(90)
    ]
    positive[24] = replace(positive[24], low=94.8, volume=1_400)
    positive[61] = replace(positive[61], low=95.1, volume=800)
    positive[-1] = replace(positive[-1], close=106.0, open=105.7, high=106.3)
    negative = list(positive)
    negative[61] = replace(negative[61], low=89.0)
    return positive, negative, _trend(positive)


def _inverse_head_and_shoulders() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [
        _candle(
            index,
            104.0 + index * 0.01,
            high=106.0 + index * 0.002,
            low=102.0 + index * 0.005,
        )
        for index in range(120)
    ]
    positive[25] = replace(positive[25], low=96.0)
    positive[58] = replace(positive[58], low=91.0)
    positive[91] = replace(positive[91], low=96.3)
    positive[-1] = replace(positive[-1], close=106.1, open=105.8, high=106.4)
    negative = list(positive)
    negative[91] = replace(negative[91], low=90.0)
    return positive, negative, _trend(positive)


def _falling_wedge() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 116.0) for index in range(15)]
    for offset in range(35):
        high = 115.0 - offset * 0.20
        low = 108.0 - offset * 0.10
        close = high - 0.20
        positive.append(
            _candle(15 + offset, close, high=high, low=low, volume=1_100 - offset * 5)
        )
    negative = list(positive)
    for offset, index in enumerate(range(15, 50)):
        negative[index] = replace(negative[index], low=108.0 - offset * 0.25)
    return positive, negative, _trend(positive)


def _rounding_base() -> tuple[list[Candle], list[Candle], TrendAnalysis]:
    positive = [_candle(index, 120.0) for index in range(10)]
    for offset in range(80):
        normalized = (offset - 39.5) / 39.5
        close = 96.0 + 23.0 * normalized * normalized
        positive.append(
            _candle(
                10 + offset,
                close,
                high=close + 1.0,
                low=close - 1.0,
                volume=1_100 - min(offset, 79 - offset) * 5,
            )
        )
    positive[-1] = replace(positive[-1], close=119.2, open=118.9, high=120.0)
    negative = list(positive)
    for index in range(70, 90):
        negative[index] = replace(negative[index], close=100.0, high=101.0, low=99.0)
    return positive, negative, _trend(positive)


CASES: tuple[tuple[str, Detector, Builder], ...] = (
    ("controlled_pullback", detect_controlled_pullback, _controlled_pullback),
    ("confirmed_breakout", detect_confirmed_breakout, _confirmed_breakout),
    ("bull_flag", detect_bull_flag, _bull_flag),
    ("flat_base", detect_flat_base, _flat_base),
    ("ascending_triangle", detect_ascending_triangle, _ascending_triangle),
    ("vcp_tight_base", detect_vcp_tight_base, _vcp),
    ("cup_with_handle", detect_cup_with_handle, _cup_with_handle),
    ("breakout_retest", detect_breakout_retest, _breakout_retest),
    ("double_bottom", detect_double_bottom, _double_bottom),
    (
        "inverse_head_and_shoulders",
        detect_inverse_head_and_shoulders,
        _inverse_head_and_shoulders,
    ),
    ("falling_wedge", detect_falling_wedge, _falling_wedge),
    ("rounding_base", detect_rounding_base, _rounding_base),
)


@pytest.mark.parametrize(("pattern_type", "detector", "builder"), CASES)
def test_pattern_positive_and_negative_geometry(
    pattern_type: str, detector: Detector, builder: Builder
) -> None:
    positive, negative, trend = builder()
    signal = detector(positive, trend, PROFILE)
    assert signal is not None
    assert signal.pattern_type == pattern_type
    assert signal.quality > 0
    assert signal.invalidation < signal.target

    negative_trend = trend
    if pattern_type == "controlled_pullback":
        negative_trend = replace(
            trend, pullback_setup=False, pullback_support=trend.close - 2
        )
    elif pattern_type == "confirmed_breakout":
        negative_trend = replace(
            trend, breakout_confirmed=False, breakout_level=trend.close + 3
        )
    assert detector(negative, negative_trend, PROFILE) is None


@pytest.mark.parametrize(("pattern_type", "detector", "builder"), CASES)
def test_pattern_detectors_ignore_an_unconfirmed_future_bar(
    pattern_type: str, detector: Detector, builder: Builder
) -> None:
    candles, _, trend = builder()
    expected = detector(candles, trend, PROFILE)
    future = _candle(
        len(candles),
        1_000.0,
        high=1_200.0,
        low=1.0,
        volume=100_000_000,
        completed=False,
    )
    actual = detector([*candles, future], trend, PROFILE)
    assert actual == expected, pattern_type


@pytest.mark.parametrize("pattern_type", [case[0] for case in CASES])
def test_shared_pattern_state_boundaries_apply_to_every_pattern(pattern_type: str) -> None:
    ready_bars = [_candle(0, 99.0), _candle(1, 99.5)]
    ready, _ = _status(ready_bars, 100.0, 95.0, 1.0, PROFILE)
    assert ready == PatternStatus.READY, pattern_type

    extension_boundary = [_candle(0, 99.0), _candle(1, 101.0)]
    confirmed, age = _status(extension_boundary, 100.0, 95.0, 1.0, PROFILE)
    assert (confirmed, age) == (PatternStatus.CONFIRMED, 0), pattern_type

    stale_bars = [_candle(0, 99.0), _candle(1, 100.2)] + [
        _candle(index, 100.4) for index in range(2, 6)
    ]
    stale, age = _status(stale_bars, 100.0, 95.0, 1.0, PROFILE)
    assert (stale, age) == (PatternStatus.STALE, 4), pattern_type

    failed_bars = [_candle(0, 99.0), _candle(1, 94.9)]
    failed, _ = _status(failed_bars, 100.0, 95.0, 1.0, PROFILE)
    assert failed == PatternStatus.FAILED, pattern_type
