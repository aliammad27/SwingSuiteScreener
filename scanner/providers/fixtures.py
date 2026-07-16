from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from math import sin

from scanner.calendars import is_trading_day, market_close_for
from scanner.clocks import NY
from scanner.models import (
    Candle,
    EventRisk,
    EventRiskStatus,
    OptionContractSnapshot,
    StrategyLane,
)
from scanner.providers.base import EventRiskProvider, MarketDataProvider, OptionDataProvider

FIXTURE_TIMESTAMP = datetime(2026, 6, 18, 18, 0, tzinfo=UTC)


def _hourly_timestamps(count: int) -> list[datetime]:
    local_as_of = FIXTURE_TIMESTAMP.astimezone(NY)
    timestamps: list[datetime] = []
    current_day = local_as_of.date()
    while len(timestamps) < count:
        if is_trading_day(current_day):
            session_end = market_close_for(current_day)
            if current_day == local_as_of.date():
                session_end = min(session_end, local_as_of)
            bucket_start = datetime.combine(current_day, time(9, 30), NY)
            while bucket_start + timedelta(hours=1) <= session_end:
                timestamps.append(bucket_start.astimezone(UTC))
                bucket_start += timedelta(hours=1)
        current_day -= timedelta(days=1)
    return sorted(timestamps)[-count:]


def _series(
    symbol: str,
    timeframe: str,
    count: int,
    base: float,
    drift: float,
    amplitude: float,
) -> list[Candle]:
    candles: list[Candle] = []
    close = base
    timestamps: list[datetime]
    if timeframe == "1D":
        step = timedelta(days=1)
        start = FIXTURE_TIMESTAMP - (step * count)
        timestamps = [start + (step * idx) for idx in range(count)]
    elif timeframe == "1W":
        step = timedelta(days=7)
        start = FIXTURE_TIMESTAMP - (step * count)
        timestamps = [start + (step * idx) for idx in range(count)]
    else:
        timestamps = _hourly_timestamps(count)
    for idx, timestamp in enumerate(timestamps):
        wave = sin(idx / 4) * amplitude
        close = max(5, close + drift + wave * 0.12)
        if idx > count - 9 and drift > 0:
            close += drift * (idx - (count - 9)) * 0.20
        open_price = close - (drift * 0.35) - (wave * 0.02)
        high = max(open_price, close) + max(0.45, amplitude * 0.55)
        low = min(open_price, close) - max(0.45, amplitude * 0.55)
        volume = 1_200_000 + idx * 1200
        if idx == count - 1 and drift > 0:
            volume = int(volume * 1.45)
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volume,
                completed=True,
                source="fixture",
            )
        )
    return candles


class FixtureDataProvider(MarketDataProvider, OptionDataProvider, EventRiskProvider):
    def __init__(self, scenario: str = "default") -> None:
        self.scenario = scenario
        self.stock_feed = "sip"
        self.option_feed = "indicative" if scenario == "technical_watch" else "opra"

    def _profile(self, symbol: str) -> tuple[float, float, float]:
        if self.scenario == "zero" or symbol == "ZERO":
            return 80, -0.08, 1.6
        if symbol == "APLUS":
            return 55, 0.20, 1.9
        if symbol == "BTIER":
            return 38, 0.014, 2.6
        if symbol == "SSTR":
            return 70, 0.25, 1.8
        if symbol in {"SPY", "QQQ"}:
            return 100, 0.03, 1.2
        if symbol == "XLK":
            return 100, 0.12, 1.2
        return 70, 0.17, 1.8

    def daily(self, symbol: str) -> list[Candle]:
        base, drift, amplitude = self._profile(symbol)
        candles = _series(symbol, "1D", 320, base, drift, amplitude)
        if symbol in {"BTIER", "ZERO"}:
            candles = [
                replace(candle, volume=int(candle.volume * 3))
                for candle in candles
            ]
        if symbol in {"SSTR", "APLUS"}:
            anchor = candles[-6].close
            shift = 0.0
            closes = (
                anchor - 0.20 + shift,
                anchor - 0.45 + shift,
                anchor - 0.70 + shift,
                anchor - 0.90 + shift,
                anchor - 0.70 + shift,
            )
            for index, close in zip(
                range(len(candles) - 5, len(candles)),
                closes,
                strict=True,
            ):
                bullish_reclaim = index == len(candles) - 1
                candles[index] = replace(
                    candles[index],
                    open=round(close - 0.20 if bullish_reclaim else close + 0.10, 2),
                    high=round(close + 0.28, 2),
                    low=round(
                        close
                        - (
                            1.40
                            if bullish_reclaim and symbol == "SSTR"
                            else 0.90
                            if bullish_reclaim
                            else 0.30
                        ),
                        2,
                    ),
                    close=round(close, 2),
                    volume=(
                        int(candles[index].volume * 1.05)
                        if bullish_reclaim
                        else candles[index].volume
                    ),
                )
        return candles

    def one_hour(self, symbol: str) -> list[Candle]:
        base, drift, amplitude = self._profile(symbol)
        if symbol == "APLUS":
            drift = 0.08
        candles = _series(symbol, "1H", 240, base, drift * 0.35, amplitude * 0.60)
        if symbol not in {"BTIER", "ZERO"}:
            anchor = candles[-9].close
            for offset, index in enumerate(range(len(candles) - 8, len(candles)), 1):
                close = anchor + offset * 0.22
                candles[index] = replace(
                    candles[index],
                    open=round(close - 0.12, 2),
                    high=round(close + 0.24, 2),
                    low=round(close - 0.20, 2),
                    close=round(close, 2),
                    volume=int(candles[index].volume * 1.15),
                )
        target_close = self.daily(symbol)[-1].close
        shift = target_close - candles[-1].close
        candles = [
            replace(
                candle,
                open=round(candle.open + shift, 2),
                high=round(candle.high + shift, 2),
                low=round(candle.low + shift, 2),
                close=round(candle.close + shift, 2),
            )
            for candle in candles
        ]
        return candles

    def weekly(self, symbol: str) -> list[Candle]:
        base, drift, amplitude = self._profile(symbol)
        return _series(symbol, "1W", 100, base, drift * 4.2, amplitude * 2)

    def eligible_underlyings(
        self,
        symbols: list[str],
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> set[str]:
        if self.scenario == "missing_contracts":
            return set()
        expiry = FIXTURE_TIMESTAMP.date() + timedelta(days=15)
        if not expiration_date_gte <= expiry <= expiration_date_lte:
            return set()
        return set(symbols)

    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        if self.scenario == "missing_contracts":
            return []
        lane_is_index = symbol in {"SPY", "QQQ"}
        target_dte = 15
        expiry = as_of.date() + timedelta(days=target_dte)
        if not expiration_date_gte <= expiry <= expiration_date_lte:
            return []
        if symbol == "ZERO":
            return [
                self._contract(symbol, expiry, 0.30, 1.0, 1.5, 50, 10, strike=100.0)
            ]
        if symbol == "APLUS":
            strike = round((self.daily(symbol)[-1].close - 2.5) / 2.5) * 2.5
            return [
                self._contract(
                    symbol,
                    expiry,
                    0.55,
                    3.00,
                    3.12,
                    1500,
                    300,
                    strike=strike,
                )
            ]
        base_delta = 0.67 if lane_is_index else 0.61
        minimum_oi = 3000 if lane_is_index else 2500
        minimum_volume = 1200 if lane_is_index else 800
        underlying = self.daily(symbol)[-1].close
        strike_anchor = round((underlying - 2.5) / 2.5) * 2.5
        return [
            self._contract(
                symbol,
                expiry,
                base_delta + offset,
                4.10 + index * 0.35,
                4.15 + index * 0.35,
                minimum_oi - index * 100,
                minimum_volume - index * 20,
                strike=strike_anchor + index * 2.5,
            )
            for index, offset in enumerate((0.0, -0.04, 0.05))
        ]

    def _contract(
        self,
        symbol: str,
        expiry: date,
        delta: float,
        bid: float,
        ask: float,
        open_interest: int,
        volume: int,
        *,
        strike: float,
    ) -> OptionContractSnapshot:
        encoded_strike = int(strike * 1000)
        contract_symbol = f"{symbol}{expiry.strftime('%y%m%d')}C{encoded_strike:08d}"
        return OptionContractSnapshot(
            contract_symbol=contract_symbol,
            underlying_symbol=symbol,
            expiration_date=expiry,
            strike=strike,
            dte=(expiry - FIXTURE_TIMESTAMP.date()).days,
            delta=delta,
            gamma=0.025,
            theta=-0.08,
            vega=0.14,
            implied_volatility=0.03,
            bid=bid,
            ask=ask,
            bid_size=20,
            ask_size=25,
            open_interest=open_interest,
            volume=volume,
            feed=self.option_feed,
            quote_timestamp=FIXTURE_TIMESTAMP,
        )

    def latest_quotes(
        self,
        contracts: list[OptionContractSnapshot],
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        return [
            replace(
                contract,
                bid=round(contract.bid + 0.01, 2),
                ask=round(contract.ask + 0.01, 2),
                dte=(contract.expiration_date - as_of.date()).days,
                quote_timestamp=as_of,
            )
            for contract in contracts
        ]

    def event_risk(
        self,
        symbol: str,
        as_of: datetime,
        lane: StrategyLane,
    ) -> EventRisk:
        del lane
        if symbol == "ZERO":
            return EventRisk(
                symbol=symbol,
                status=EventRiskStatus.BLOCKED,
                earnings_date=FIXTURE_TIMESTAMP.date() + timedelta(days=5),
                summary="Fixture earnings fall inside the blackout window.",
                source="fixture",
                checked_at=as_of,
                source_timestamp=as_of,
            )
        return EventRisk(
            symbol=symbol,
            status=EventRiskStatus.CLEAR,
            earnings_date=FIXTURE_TIMESTAMP.date() + timedelta(days=60),
            summary="Fixture event calendar is clear.",
            source="fixture",
            checked_at=as_of,
            source_timestamp=as_of,
        )
