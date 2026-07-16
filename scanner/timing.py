from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from scanner.indicators import ema, macd, rsi_series, sma
from scanner.models import Candle, ScanType, TimingAnalysis
from scanner.strategy_profile import StrategyProfile

NY = ZoneInfo("America/New_York")


def _parse_clock(value: str) -> time:
    hour_text, minute_text = value.split(":", 1)
    return time(hour=int(hour_text), minute=int(minute_text))


def _session_vwap(candles: list[Candle]) -> float:
    latest_day = candles[-1].timestamp.astimezone(NY).date()
    session = [
        candle
        for candle in candles
        if candle.timestamp.astimezone(NY).date() == latest_day
    ]
    volume = sum(candle.volume for candle in session)
    if volume <= 0:
        raise ValueError("Hourly timing requires positive session volume.")
    weighted = sum(
        ((candle.high + candle.low + candle.close) / 3) * candle.volume
        for candle in session
    )
    return weighted / volume


def _completed_regular_hours(
    candles: list[Candle],
    *,
    as_of: datetime | None = None,
) -> list[Candle]:
    completed: list[Candle] = []
    for candle in candles:
        local = candle.timestamp.astimezone(NY)
        local_time = local.time().replace(tzinfo=None)
        if not candle.completed or local.minute != 30:
            continue
        if not time(9, 30) <= local_time <= time(14, 30):
            continue
        if as_of is not None and candle.timestamp + timedelta(hours=1) > as_of:
            continue
        completed.append(candle)
    return sorted(completed, key=lambda candle: candle.timestamp)


def _hourly_confirmation(candles: list[Candle]) -> bool:
    completed = _completed_regular_hours(candles)
    if len(completed) < 30:
        return False
    closes = [candle.close for candle in completed]
    _, _, histogram, _ = macd(closes)
    return closes[-1] > ema(closes, 21) and histogram > 0


def market_hourly_confirmation(
    spy_hourly: list[Candle],
    qqq_hourly: list[Candle],
) -> bool:
    return _hourly_confirmation(spy_hourly) and _hourly_confirmation(qqq_hourly)


def analyze_timing(
    symbol: str,
    candles: list[Candle],
    *,
    daily_filter_passed: bool,
    market_confirmation: bool,
    as_of: datetime,
    scan_type: ScanType,
    profile: StrategyProfile,
) -> TimingAnalysis:
    completed = _completed_regular_hours(candles, as_of=as_of)
    if len(completed) < profile.minimum_hourly_bars:
        raise ValueError(
            f"Hourly timing requires {profile.minimum_hourly_bars} completed bars."
        )
    closes = [candle.close for candle in completed]
    lows = [candle.low for candle in completed]
    highs = [candle.high for candle in completed]
    volumes = [float(candle.volume) for candle in completed]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    session_vwap = _session_vwap(completed)
    rsis = rsi_series(closes, 14)
    current_rsi = rsis[-1]
    _, _, histogram, previous_histogram = macd(closes)
    average_volume = sma(volumes, 20)
    relative_volume = volumes[-1] / average_volume if average_volume > 0 else 0.0
    higher_low = lows[-1] > min(lows[-4:-1])
    reclaimed_ema = closes[-2] <= ema9 < closes[-1]
    reclaimed_vwap = closes[-2] <= session_vwap < closes[-1]
    reclaim = reclaimed_ema or reclaimed_vwap or (
        closes[-1] > ema9 and closes[-1] > session_vwap
    )

    local = as_of.astimezone(NY)
    start = _parse_clock(profile.entry_window_start_et)
    end = _parse_clock(profile.entry_window_end_et)
    entry_window_open = (
        scan_type == ScanType.INTRADAY
        and local.weekday() < 5
        and start <= local.time().replace(tzinfo=None) <= end
    )
    management_only = not entry_window_open

    score = 0
    score += 15 if closes[-1] > ema9 else 0
    score += 15 if ema9 > ema21 else 0
    score += 15 if closes[-1] > session_vwap else 0
    score += 10 if 50 <= current_rsi <= 72 else 5 if current_rsi > 45 else 0
    score += 15 if histogram > 0 and histogram >= previous_histogram else 7 if histogram > 0 else 0
    score += 10 if relative_volume >= 0.80 else 5 if relative_volume >= 0.60 else 0
    score += 10 if higher_low else 0
    score += 5 if reclaim else 0
    score += 5 if market_confirmation else 0

    reasons: list[str] = []
    if not daily_filter_passed:
        reasons.append("daily_filter_failed")
    if closes[-1] <= ema9:
        reasons.append("below_hourly_ema9")
    if ema9 <= ema21:
        reasons.append("hourly_ema_stack_not_bullish")
    if closes[-1] <= session_vwap:
        reasons.append("below_session_vwap")
    if current_rsi < 50:
        reasons.append("hourly_rsi_below_50")
    if histogram <= 0:
        reasons.append("hourly_macd_histogram_not_positive")
    if not (higher_low or reclaim):
        reasons.append("no_hourly_higher_low_or_reclaim")
    if not market_confirmation:
        reasons.append("intraday_index_confirmation_failed")
    if management_only:
        reasons.append("outside_new_entry_window")

    bullish_confirmation = (
        daily_filter_passed
        and closes[-1] > ema9 > ema21
        and closes[-1] > session_vwap
        and current_rsi >= 50
        and histogram > 0
        and (higher_low or reclaim)
        and market_confirmation
        and entry_window_open
    )
    tactical_warning = max(min(ema9, session_vwap), min(lows[-3:]))
    tactical_failure = min(ema21, min(lows[-5:]))
    if bullish_confirmation:
        state = "Entry confirmed"
    elif management_only and score >= 70:
        state = "Constructive - management only"
    elif score >= 70:
        state = "Improving"
    else:
        state = "Not confirmed"
    return TimingAnalysis(
        symbol=symbol,
        score=min(score, 100),
        state=state,
        completed_at=completed[-1].timestamp + timedelta(hours=1),
        ema9=ema9,
        ema21=ema21,
        session_vwap=session_vwap,
        rsi=current_rsi,
        macd_histogram=histogram,
        relative_volume=relative_volume,
        higher_low=higher_low,
        reclaim=reclaim,
        market_confirmation=market_confirmation,
        entry_window_open=entry_window_open,
        management_only=management_only,
        bullish_confirmation=bullish_confirmation,
        trigger=max(highs[-3:]),
        support=max(ema21, min(lows[-5:])),
        tactical_warning=tactical_warning,
        tactical_failure=tactical_failure,
        reasons=tuple(reasons),
    )
