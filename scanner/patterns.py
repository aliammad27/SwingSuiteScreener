from __future__ import annotations

from collections.abc import Callable

from scanner.models import Candle, PatternSignal, PatternStatus, TrendAnalysis
from scanner.strategy_profile import StrategyProfile
from scanner.structure import confirmed_pivot_highs, confirmed_pivot_lows


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2
    y_mean = _average(values)
    numerator = sum(
        (index - x_mean) * (value - y_mean) for index, value in enumerate(values)
    )
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    return numerator / denominator if denominator else 0.0


def _completed(candles: list[Candle]) -> list[Candle]:
    return [candle for candle in candles if candle.completed]


def _quality(*components: int) -> int:
    return max(0, min(sum(components), 100))


def _status(
    candles: list[Candle],
    trigger: float,
    invalidation: float,
    current_atr: float,
    profile: StrategyProfile,
) -> tuple[PatternStatus, int]:
    closes = [candle.close for candle in candles]
    if closes[-1] < invalidation:
        return PatternStatus.FAILED, 0
    breakout_index: int | None = None
    for idx in range(1, len(closes)):
        if closes[idx - 1] <= trigger < closes[idx]:
            breakout_index = idx
    if breakout_index is not None:
        age = len(closes) - 1 - breakout_index
        extension_atr = (closes[-1] - trigger) / max(current_atr, 0.01)
        if (
            age <= profile.maximum_confirmed_age_bars
            and extension_atr <= profile.maximum_confirmed_extension_atr
        ):
            return PatternStatus.CONFIRMED, age
        return PatternStatus.STALE, age
    distance_atr = (trigger - closes[-1]) / max(current_atr, 0.01)
    if 0 <= distance_atr <= profile.ready_distance_atr:
        return PatternStatus.READY, 0
    return PatternStatus.FORMING, 0


def _signal(
    pattern_type: str,
    candles: list[Candle],
    trend: TrendAnalysis,
    profile: StrategyProfile,
    quality: int,
    trigger: float,
    invalidation: float,
    target: float,
    notes: tuple[str, ...],
) -> PatternSignal:
    status, age = _status(candles, trigger, invalidation, trend.atr, profile)
    return PatternSignal(
        pattern_type=pattern_type,
        status=status,
        quality=quality,
        trigger=trigger,
        invalidation=max(invalidation, 0.01),
        target=max(target, trigger + 0.01),
        age_bars=age,
        geometry_notes=notes,
    )


def detect_controlled_pullback(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 2:
        return None
    distance = abs(trend.close - trend.pullback_support) / max(trend.atr, 0.01)
    if not trend.pullback_setup and distance > 0.75:
        return None
    risk = max(trend.close - (trend.pullback_support - 0.20 * trend.atr), 0.01)
    target = max(trend.resistance_level, trend.close + 2 * risk)
    room_pass = target - trend.close >= 1.5 * risk
    quality = _quality(
        40 if trend.pullback_setup else 28,
        25 if 0.65 <= trend.relative_volume <= 1.60 else 12,
        20 if candles[-1].close >= candles[-1].open else 8,
        15 if room_pass else 5,
    )
    trigger = max(candle.high for candle in candles[-2:])
    return _signal(
        "controlled_pullback",
        candles,
        trend,
        profile,
        quality,
        trigger,
        trend.pullback_support - 0.20 * trend.atr,
        target,
        ("21EMA/anchored-VWAP support", "bullish support hold"),
    )


def detect_confirmed_breakout(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 2:
        return None
    distance = (trend.breakout_level - trend.close) / max(trend.atr, 0.01)
    if not trend.breakout_confirmed and not 0 <= distance <= 1.0:
        return None
    invalidation = max(trend.ema21, trend.breakout_level - 0.50 * trend.atr)
    risk = max(trend.breakout_level - invalidation, 0.25 * trend.atr)
    quality = _quality(
        40 if trend.breakout_confirmed else 30,
        25 if trend.relative_volume >= 1.20 else 12,
        20 if trend.weekly_aligned else 0,
        15 if not trend.extended else 0,
    )
    return _signal(
        "confirmed_breakout",
        candles,
        trend,
        profile,
        quality,
        trend.breakout_level,
        invalidation,
        trend.breakout_level + (2 * risk),
        ("20-session resistance", "closing breakout"),
    )


def detect_bull_flag(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 20:
        return None
    pole = candles[-15:-5]
    flag = candles[-5:]
    impulse = pole[-1].close - pole[0].close
    if impulse <= 0:
        return None
    retracement = (pole[-1].close - min(candle.low for candle in flag)) / impulse
    impulse_pass = impulse >= 2 * trend.atr
    retracement_pass = 0.10 <= retracement <= 0.50
    slope_pass = flag[-1].close <= flag[0].close + 0.25 * trend.atr
    volume_pass = _average([float(c.volume) for c in flag]) <= _average(
        [float(c.volume) for c in pole]
    )
    if retracement > 0.65 or not slope_pass:
        return None
    trigger = max(candle.high for candle in flag)
    invalidation = min(candle.low for candle in flag)
    quality = _quality(
        40 if impulse_pass and retracement_pass else 22,
        25 if volume_pass else 10,
        20 if trend.score >= 80 else 10,
        15 if trigger - invalidation <= 1.5 * trend.atr else 5,
    )
    return _signal(
        "bull_flag",
        candles,
        trend,
        profile,
        quality,
        trigger,
        invalidation,
        trigger + max(impulse, 2 * trend.atr),
        (f"pole {impulse / trend.atr:.1f} ATR", f"retracement {retracement:.0%}"),
    )


def detect_flat_base(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 30:
        return None
    base = candles[-25:]
    high = max(candle.high for candle in base)
    low = min(candle.low for candle in base)
    depth = (high - low) / high if high > 0 else 1.0
    if depth > 0.12:
        return None
    volume_pass = _average([float(c.volume) for c in base[-10:]]) <= _average(
        [float(c.volume) for c in base[:-10]]
    )
    trigger = max(candle.high for candle in base[:-1])
    quality = _quality(
        40 if depth <= 0.08 else 28,
        25 if volume_pass else 10,
        20 if trend.ema21 > trend.sma50 else 8,
        15 if trend.close >= trigger - 0.50 * trend.atr else 6,
    )
    return _signal(
        "flat_base",
        candles,
        trend,
        profile,
        quality,
        trigger,
        low,
        trigger + max(trigger - low, 2 * trend.atr),
        (f"25-bar depth {depth:.1%}", "volume contraction" if volume_pass else "volume mixed"),
    )


def detect_ascending_triangle(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    recent = candles[-60:]
    highs = [candle.high for candle in recent]
    lows = [candle.low for candle in recent]
    pivot_highs = confirmed_pivot_highs(highs, 3, 2)[-3:]
    pivot_lows = confirmed_pivot_lows(lows, 3, 2)[-3:]
    if len(pivot_highs) < 2 or len(pivot_lows) < 2:
        return None
    high_values = [value for _, value in pivot_highs]
    top = _average(high_values)
    flat_top = max(high_values) - min(high_values) <= 0.50 * trend.atr
    rising_lows = pivot_lows[-1][1] > pivot_lows[-2][1]
    if not flat_top or not rising_lows:
        return None
    invalidation = pivot_lows[-1][1]
    quality = _quality(
        40,
        25 if recent[-1].volume <= _average([float(c.volume) for c in recent]) else 12,
        20 if trend.score >= 80 else 10,
        15 if trend.close >= top - 0.50 * trend.atr else 6,
    )
    return _signal(
        "ascending_triangle",
        candles,
        trend,
        profile,
        quality,
        top,
        invalidation,
        top + max(top - invalidation, 2 * trend.atr),
        ("flat pivot-high band", "rising confirmed pivot lows"),
    )


def detect_vcp_tight_base(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 70:
        return None
    recent = candles[-60:]
    thirds = (recent[:20], recent[20:40], recent[40:])
    ranges = [max(c.high for c in block) - min(c.low for c in block) for block in thirds]
    contraction = ranges[1] <= 0.85 * ranges[0] and ranges[2] <= 0.85 * ranges[1]
    volume_pass = _average([float(c.volume) for c in recent[-20:]]) <= 0.80 * _average(
        [float(c.volume) for c in recent[20:40]]
    )
    high = max(candle.high for candle in recent)
    near_high = trend.close >= 0.90 * high
    if not contraction or not near_high:
        return None
    trigger = max(candle.high for candle in recent[-20:-1])
    invalidation = min(candle.low for candle in recent[-20:])
    quality = _quality(
        40,
        25 if volume_pass else 12,
        20 if ranges[2] <= 0.70 * ranges[0] else 12,
        15 if trend.close >= trigger - 0.50 * trend.atr else 6,
    )
    return _signal(
        "vcp_tight_base",
        candles,
        trend,
        profile,
        quality,
        trigger,
        invalidation,
        trigger + max(ranges[0], 2 * trend.atr),
        ("three contracting ranges", "volume contraction" if volume_pass else "volume mixed"),
    )


def detect_cup_with_handle(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 130:
        return None
    cup = candles[-120:-15]
    handle = candles[-15:]
    left_rim = max(candle.high for candle in cup[:30])
    right_rim = max(candle.high for candle in cup[-25:])
    bottom = min(candle.low for candle in cup[25:-20])
    rim = max(left_rim, right_rim)
    depth = (rim - bottom) / rim if rim > 0 else 1.0
    rim_match = abs(left_rim - right_rim) / rim <= 0.05 if rim > 0 else False
    handle_low = min(candle.low for candle in handle)
    handle_depth = (right_rim - handle_low) / right_rim if right_rim > 0 else 1.0
    handle_above_midpoint = handle_low > bottom + (rim - bottom) * 0.50
    if not (0.12 <= depth <= 0.35 and rim_match and handle_depth <= 0.12 and handle_above_midpoint):
        return None
    volume_pass = _average([float(c.volume) for c in handle]) <= _average(
        [float(c.volume) for c in cup[-30:]]
    )
    quality = _quality(
        40,
        25 if volume_pass else 12,
        20 if trend.score >= 80 else 10,
        15 if trend.close >= right_rim - 0.50 * trend.atr else 6,
    )
    return _signal(
        "cup_with_handle",
        candles,
        trend,
        profile,
        quality,
        right_rim,
        handle_low,
        right_rim + (rim - bottom),
        (f"cup depth {depth:.1%}", f"handle depth {handle_depth:.1%}"),
    )


def detect_breakout_retest(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 45:
        return None
    breakout_index: int | None = None
    resistance = 0.0
    for idx in range(len(candles) - 10, len(candles) - 1):
        prior = candles[idx - 30 : idx]
        candidate_resistance = max(candle.high for candle in prior)
        average_volume = _average([float(c.volume) for c in prior[-20:]])
        if (
            candles[idx].close > candidate_resistance
            and candles[idx].volume >= 1.20 * average_volume
        ):
            breakout_index = idx
            resistance = candidate_resistance
    if breakout_index is None:
        return None
    post_breakout = candles[breakout_index + 1 :]
    if not post_breakout:
        return None
    retest = min(candle.low for candle in post_breakout) <= resistance + 0.50 * trend.atr
    held = candles[-1].close > resistance
    if not retest or not held:
        return None
    invalidation = min(candle.low for candle in post_breakout)
    quality = _quality(
        40,
        25,
        20 if candles[-1].close >= candles[-1].open else 10,
        15 if candles[-1].close <= resistance + trend.atr else 5,
    )
    return _signal(
        "breakout_retest",
        candles,
        trend,
        profile,
        quality,
        resistance,
        invalidation,
        resistance + max(resistance - invalidation, 2 * trend.atr),
        ("volume-confirmed breakout", "retest held above resistance"),
    )


def detect_double_bottom(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 70:
        return None
    recent = candles[-90:]
    lows = [candle.low for candle in recent]
    pivots = confirmed_pivot_lows(lows, 4, 3)
    if len(pivots) < 2:
        return None
    first, second = pivots[-2], pivots[-1]
    spacing = second[0] - first[0]
    tolerance = max(0.75 * trend.atr, min(first[1], second[1]) * 0.03)
    if not 10 <= spacing <= 60 or abs(first[1] - second[1]) > tolerance:
        return None
    neckline = max(candle.high for candle in recent[first[0] : second[0] + 1])
    depth = neckline - min(first[1], second[1])
    if depth < 1.50 * trend.atr or trend.close < neckline - 0.75 * trend.atr:
        return None
    first_volume = recent[first[0]].volume
    second_volume = recent[second[0]].volume
    quality = _quality(
        40 if abs(first[1] - second[1]) <= 0.35 * trend.atr else 30,
        25 if second_volume <= first_volume else 12,
        20 if depth >= 2.5 * trend.atr else 12,
        15 if trend.close >= neckline - 0.50 * trend.atr else 6,
    )
    invalidation = min(first[1], second[1]) - 0.20 * trend.atr
    return _signal(
        "double_bottom",
        candles,
        trend,
        profile,
        quality,
        neckline,
        invalidation,
        neckline + depth,
        (f"two lows separated by {spacing} bars", "neckline recovery"),
    )


def detect_inverse_head_and_shoulders(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 100:
        return None
    recent = candles[-120:]
    lows = [candle.low for candle in recent]
    pivots = confirmed_pivot_lows(lows, 4, 3)
    if len(pivots) < 3:
        return None
    left, head, right = pivots[-3:]
    if not (8 <= head[0] - left[0] <= 45 and 8 <= right[0] - head[0] <= 45):
        return None
    shoulder_tolerance = max(0.80 * trend.atr, min(left[1], right[1]) * 0.03)
    head_depth = min(left[1], right[1]) - head[1]
    if abs(left[1] - right[1]) > shoulder_tolerance or head_depth < 0.75 * trend.atr:
        return None
    left_neckline = max(candle.high for candle in recent[left[0] : head[0] + 1])
    right_neckline = max(candle.high for candle in recent[head[0] : right[0] + 1])
    neckline = (left_neckline + right_neckline) / 2
    if trend.close < neckline - 0.75 * trend.atr:
        return None
    measured_depth = neckline - head[1]
    quality = _quality(
        40 if abs(left[1] - right[1]) <= 0.40 * trend.atr else 30,
        25 if abs(left_neckline - right_neckline) <= trend.atr else 12,
        20 if measured_depth >= 2 * trend.atr else 12,
        15 if trend.close >= neckline - 0.50 * trend.atr else 6,
    )
    return _signal(
        "inverse_head_and_shoulders",
        candles,
        trend,
        profile,
        quality,
        neckline,
        head[1] - 0.20 * trend.atr,
        neckline + measured_depth,
        ("three confirmed pivot lows", "right shoulder recovered toward neckline"),
    )


def detect_falling_wedge(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 45:
        return None
    wedge = candles[-35:]
    highs = [candle.high for candle in wedge]
    lows = [candle.low for candle in wedge]
    high_slope = _slope(highs)
    low_slope = _slope(lows)
    early_width = _average(
        [high - low for high, low in zip(highs[:10], lows[:10], strict=True)]
    )
    late_width = _average(
        [high - low for high, low in zip(highs[-10:], lows[-10:], strict=True)]
    )
    converging = high_slope < low_slope < 0 and late_width <= 0.80 * early_width
    upper_now = highs[0] + high_slope * (len(highs) - 1)
    if not converging or trend.close < upper_now - 0.75 * trend.atr:
        return None
    invalidation = min(lows[-12:])
    height = max(highs[:10]) - min(lows)
    quality = _quality(
        40,
        25 if late_width <= 0.65 * early_width else 15,
        20 if trend.close >= upper_now - 0.35 * trend.atr else 10,
        15 if trend.weekly_aligned else 5,
    )
    return _signal(
        "falling_wedge",
        candles,
        trend,
        profile,
        quality,
        upper_now,
        invalidation,
        upper_now + max(height, 2 * trend.atr),
        ("descending converging boundaries", "price recovered toward upper boundary"),
    )


def detect_rounding_base(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal | None:
    candles = _completed(candles)
    if len(candles) < 90:
        return None
    base = candles[-80:]
    thirds = (base[:20], base[20:60], base[60:])
    left_rim = _average([candle.high for candle in thirds[0][:8]])
    right_rim = _average([candle.high for candle in thirds[2][-8:]])
    bottom = min(candle.low for candle in thirds[1])
    rim = max(left_rim, right_rim)
    depth = (rim - bottom) / rim if rim > 0 else 1.0
    rim_match = abs(left_rim - right_rim) / rim <= 0.06 if rim > 0 else False
    left_slope = _slope([candle.close for candle in thirds[0]])
    right_slope = _slope([candle.close for candle in thirds[2]])
    if not (
        0.08 <= depth <= 0.30
        and rim_match
        and left_slope < 0
        and right_slope > 0
        and trend.close >= right_rim - 0.75 * trend.atr
    ):
        return None
    quality = _quality(
        40 if 0.10 <= depth <= 0.25 else 30,
        25 if abs(left_rim - right_rim) <= 0.50 * trend.atr else 12,
        20 if right_slope >= abs(left_slope) * 0.60 else 10,
        15 if trend.close >= right_rim - 0.50 * trend.atr else 6,
    )
    return _signal(
        "rounding_base",
        candles,
        trend,
        profile,
        quality,
        right_rim,
        bottom,
        right_rim + (rim - bottom),
        (f"80-bar depth {depth:.1%}", "decline-to-recovery curvature"),
    )


_DETECTORS: tuple[
    Callable[[list[Candle], TrendAnalysis, StrategyProfile], PatternSignal | None], ...
] = (
    detect_controlled_pullback,
    detect_confirmed_breakout,
    detect_bull_flag,
    detect_flat_base,
    detect_ascending_triangle,
    detect_vcp_tight_base,
    detect_cup_with_handle,
    detect_breakout_retest,
    detect_double_bottom,
    detect_inverse_head_and_shoulders,
    detect_falling_wedge,
    detect_rounding_base,
)


def detect_pattern_candidates(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> tuple[PatternSignal, ...]:
    return tuple(
        signal
        for detector in _DETECTORS
        if (signal := detector(candles, trend, profile)) is not None
        and signal.pattern_type in profile.enabled_patterns
    )


def detect_best_pattern(
    candles: list[Candle], trend: TrendAnalysis, profile: StrategyProfile
) -> PatternSignal:
    candidates = detect_pattern_candidates(candles, trend, profile)
    if not candidates:
        return PatternSignal(
            pattern_type="no_valid_setup",
            status=PatternStatus.FORMING,
            quality=0,
            trigger=trend.breakout_level,
            invalidation=max(trend.pullback_support - 0.20 * trend.atr, 0.01),
            target=max(trend.resistance_level, trend.close + 2 * trend.atr),
            age_bars=0,
            geometry_notes=("No qualifying bullish setup geometry",),
        )
    priority = {
        PatternStatus.CONFIRMED: 4,
        PatternStatus.READY: 3,
        PatternStatus.FORMING: 2,
        PatternStatus.STALE: 1,
        PatternStatus.FAILED: 0,
    }
    return max(candidates, key=lambda signal: (priority[signal.status], signal.quality))
