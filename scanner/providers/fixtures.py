from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from math import sin

from scanner.models import (
    Candle,
    EventRisk,
    EventRiskStatus,
    OptionContractSnapshot,
)
from scanner.providers.base import EventRiskProvider, MarketDataProvider, OptionDataProvider

FIXTURE_TIMESTAMP = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)


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
    if timeframe == "1D":
        step = timedelta(days=1)
    elif timeframe == "1W":
        step = timedelta(days=7)
    else:
        step = timedelta(hours=4)
    start = FIXTURE_TIMESTAMP - (step * count)
    for idx in range(count):
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
                timestamp=start + (step * idx),
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
        self.option_feed = "indicative" if scenario == "technical_watch" else "opra"

    def _profile(self, symbol: str) -> tuple[float, float, float]:
        if self.scenario == "zero" or symbol == "ZERO":
            return 80, -0.08, 1.6
        if symbol == "APLUS":
            return 55, 0.14, 1.9
        if symbol == "BTIER":
            return 38, 0.014, 2.6
        if symbol in {"SPY", "QQQ", "XLK"}:
            return 100, 0.06, 1.2
        return 70, 0.17, 1.8

    def daily(self, symbol: str) -> list[Candle]:
        base, drift, amplitude = self._profile(symbol)
        return _series(symbol, "1D", 320, base, drift, amplitude)

    def four_hour(self, symbol: str) -> list[Candle]:
        base, drift, amplitude = self._profile(symbol)
        if symbol == "APLUS":
            drift = 0.08
        candles = _series(symbol, "4H", 200, base, drift, amplitude)
        if symbol not in {"BTIER", "ZERO"}:
            anchor = candles[-9].close
            for offset, index in enumerate(range(len(candles) - 8, len(candles)), 1):
                close = anchor + offset * 0.70
                candles[index] = replace(
                    candles[index],
                    open=round(close - 0.35, 2),
                    high=round(close + 0.55, 2),
                    low=round(close - 0.55, 2),
                    close=round(close, 2),
                    volume=int(candles[index].volume * 1.15),
                )
        return candles

    def weekly(self, symbol: str) -> list[Candle]:
        base, drift, amplitude = self._profile(symbol)
        return _series(symbol, "1W", 100, base, drift * 4.2, amplitude * 2)

    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[OptionContractSnapshot]:
        if self.scenario == "missing_contracts":
            return []
        lane_is_index = symbol in {"SPY", "QQQ"}
        target_dte = 60 if lane_is_index else 45
        expiry = FIXTURE_TIMESTAMP.date() + timedelta(days=target_dte)
        if not expiration_date_gte <= expiry <= expiration_date_lte:
            return []
        if symbol == "ZERO":
            return [
                self._contract(symbol, expiry, 0.30, 1.0, 1.5, 50, 10, strike=100.0)
            ]
        if symbol == "APLUS":
            return [
                self._contract(symbol, expiry, 0.55, 3.00, 3.18, 500, 100, strike=75.0)
            ]
        base_delta = 0.67 if lane_is_index else 0.55
        minimum_oi = 2500 if lane_is_index else 1200
        minimum_volume = 1200 if lane_is_index else 350
        return [
            self._contract(
                symbol,
                expiry,
                base_delta + offset,
                4.10 + index * 0.35,
                (4.18 if lane_is_index else 4.28) + index * 0.35,
                minimum_oi - index * 100,
                minimum_volume - index * 20,
                strike=100.0 + index * 2.5,
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
            implied_volatility=0.34,
            bid=bid,
            ask=ask,
            bid_size=40,
            ask_size=45,
            open_interest=open_interest,
            volume=volume,
            feed=self.option_feed,
            quote_timestamp=FIXTURE_TIMESTAMP,
        )

    def event_risk(self, symbol: str) -> EventRisk:
        if symbol == "ZERO":
            return EventRisk(
                symbol=symbol,
                status=EventRiskStatus.BLOCKED,
                earnings_date=FIXTURE_TIMESTAMP.date() + timedelta(days=5),
                summary="Fixture earnings fall inside the blackout window.",
                source="fixture",
                checked_at=FIXTURE_TIMESTAMP,
            )
        return EventRisk(
            symbol=symbol,
            status=EventRiskStatus.CLEAR,
            earnings_date=FIXTURE_TIMESTAMP.date() + timedelta(days=60),
            summary="Fixture event calendar is clear.",
            source="fixture",
            checked_at=FIXTURE_TIMESTAMP,
        )
