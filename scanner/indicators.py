from __future__ import annotations


def sma(values: list[float], length: int) -> float:
    if len(values) < length:
        raise ValueError("not enough values for SMA")
    return sum(values[-length:]) / length


def ema_series(values: list[float], length: int) -> list[float]:
    if len(values) < length:
        raise ValueError("not enough values for EMA")
    alpha = 2 / (length + 1)
    result = [sum(values[:length]) / length]
    for value in values[length:]:
        result.append((value * alpha) + (result[-1] * (1 - alpha)))
    return result


def ema(values: list[float], length: int) -> float:
    return ema_series(values, length)[-1]


def rsi_series(values: list[float], length: int = 14) -> list[float]:
    if len(values) <= length:
        raise ValueError("not enough values for RSI")
    gains: list[float] = []
    losses: list[float] = []
    for prev, current in zip(values, values[1:], strict=False):
        change = current - prev
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    avg_gain = sum(gains[:length]) / length
    avg_loss = sum(losses[:length]) / length
    output: list[float] = []
    for gain, loss in zip(gains[length:], losses[length:], strict=False):
        avg_gain = ((avg_gain * (length - 1)) + gain) / length
        avg_loss = ((avg_loss * (length - 1)) + loss) / length
        if avg_loss == 0:
            output.append(100.0)
        else:
            rs = avg_gain / avg_loss
            output.append(100 - (100 / (1 + rs)))
    return output


def macd(values: list[float]) -> tuple[float, float, float, float]:
    fast = ema_series(values, 12)
    slow = ema_series(values, 26)
    offset = len(fast) - len(slow)
    macd_line_series = [f - s for f, s in zip(fast[offset:], slow, strict=True)]
    signal_series = ema_series(macd_line_series, 9)
    hist_series = [
        line - signal
        for line, signal in zip(macd_line_series[-len(signal_series) :], signal_series, strict=True)
    ]
    return macd_line_series[-1], signal_series[-1], hist_series[-1], hist_series[-2]


def atr(highs: list[float], lows: list[float], closes: list[float], length: int = 14) -> float:
    if len(closes) <= length:
        raise ValueError("not enough values for ATR")
    true_ranges: list[float] = []
    for idx in range(1, len(closes)):
        true_ranges.append(
            max(
                highs[idx] - lows[idx],
                abs(highs[idx] - closes[idx - 1]),
                abs(lows[idx] - closes[idx - 1]),
            )
        )
    return sum(true_ranges[-length:]) / length


def bollinger(values: list[float], length: int = 20, deviations: float = 2.0) -> tuple[float, float, float, float]:
    basis = sma(values, length)
    window = values[-length:]
    variance = sum((v - basis) ** 2 for v in window) / length
    stdev = variance**0.5
    upper = basis + (deviations * stdev)
    lower = basis - (deviations * stdev)
    width = upper - lower
    return basis, upper, lower, width


def anchored_vwap(highs: list[float], lows: list[float], closes: list[float], volumes: list[int], anchor_index: int) -> float:
    typical = [
        (high + low + close) / 3
        for high, low, close in zip(
            highs[anchor_index:],
            lows[anchor_index:],
            closes[anchor_index:],
            strict=True,
        )
    ]
    vol = volumes[anchor_index:]
    total_volume = sum(vol)
    if total_volume == 0:
        raise ValueError("zero volume for VWAP")
    return sum(t * v for t, v in zip(typical, vol, strict=True)) / total_volume
