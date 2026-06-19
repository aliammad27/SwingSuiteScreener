from scanner.indicators import ema, rsi_series, sma
from scanner.momentum import momentum_score


def test_rsi_score_boundaries() -> None:
    assert momentum_score(75, True, True, True, True) == 84
    assert momentum_score(60, True, True, True, True) == 100
    assert momentum_score(50, False, False, False, False) == 22
    assert momentum_score(39, False, False, False, False) == 0


def test_macd_below_signal_cap() -> None:
    assert momentum_score(60, True, False, True, True) == 74


def test_basic_moving_averages() -> None:
    values = [float(i) for i in range(1, 31)]
    assert sma(values, 10) == 25.5
    assert ema(values, 10) > sma(values[:-5], 10)
    assert rsi_series(values, 14)[-1] == 100
