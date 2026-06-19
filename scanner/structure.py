from __future__ import annotations


def confirmed_pivot_highs(highs: list[float], left: int, right: int) -> list[tuple[int, float]]:
    pivots: list[tuple[int, float]] = []
    for idx in range(left, len(highs) - right):
        value = highs[idx]
        if value == max(highs[idx - left : idx + right + 1]):
            pivots.append((idx, value))
    return pivots


def confirmed_pivot_lows(lows: list[float], left: int, right: int) -> list[tuple[int, float]]:
    pivots: list[tuple[int, float]] = []
    for idx in range(left, len(lows) - right):
        value = lows[idx]
        if value == min(lows[idx - left : idx + right + 1]):
            pivots.append((idx, value))
    return pivots


def classify_structure(highs: list[float], lows: list[float], left: int = 5, right: int = 3) -> str:
    ph = confirmed_pivot_highs(highs, left, right)[-2:]
    pl = confirmed_pivot_lows(lows, left, right)[-2:]
    higher_high = len(ph) == 2 and ph[-1][1] > ph[-2][1]
    higher_low = len(pl) == 2 and pl[-1][1] > pl[-2][1]
    lower_high = len(ph) == 2 and ph[-1][1] < ph[-2][1]
    lower_low = len(pl) == 2 and pl[-1][1] < pl[-2][1]
    if higher_high and higher_low:
        return "Bullish"
    if higher_high or higher_low:
        return "Improving"
    if lower_high and lower_low:
        return "Bearish"
    return "Mixed"


def nearest_support_below(price: float, levels: list[float]) -> float:
    below = [level for level in levels if level < price]
    return max(below) if below else min(levels)


def latest_resistance(highs: list[float]) -> float:
    pivots = confirmed_pivot_highs(highs, 5, 3)
    return pivots[-1][1] if pivots else max(highs[-20:])
