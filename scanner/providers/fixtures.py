from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import sin

from scanner.models import Candle, Catalyst, OptionQuote
from scanner.providers.base import CatalystProvider, MarketDataProvider, OptionDataProvider

FIXTURE_TIMESTAMP = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)


def _series(
    symbol: str, timeframe: str, count: int, base: float, drift: float, amp: float
) -> list[Candle]:
    candles: list[Candle] = []
    close = base
    step = timedelta(days=1) if timeframe == "1D" else timedelta(hours=4)
    start = FIXTURE_TIMESTAMP - (step * count)
    for idx in range(count):
        wave = sin(idx / 4) * amp
        close = max(5, close + drift + wave * 0.12)
        if idx > count - 6 and drift > 0:
            close += drift * 0.55
        open_price = close - (drift * 0.35) - (wave * 0.02)
        high = max(open_price, close) + max(0.45, amp * 0.55)
        low = min(open_price, close) - max(0.45, amp * 0.55)
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


class FixtureDataProvider(MarketDataProvider, OptionDataProvider, CatalystProvider):
    def __init__(self, scenario: str = "default") -> None:
        self.scenario = scenario

    def _profile(self, symbol: str) -> tuple[float, float, float]:
        if self.scenario == "zero" or symbol == "ZERO":
            return 80, -0.08, 1.6
        if symbol == "APLUS":
            return 55, 0.12, 2.2
        if self.scenario == "b_tier" or symbol == "BTIER":
            return 38, 0.014, 2.6
        if symbol in {"SPY", "QQQ"}:
            return 100, 0.04, 1.5
        return 70, 0.045, 3.8

    def daily(self, symbol: str) -> list[Candle]:
        base, drift, amp = self._profile(symbol)
        return _series(symbol, "1D", 260, base, drift, amp)

    def four_hour(self, symbol: str) -> list[Candle]:
        base, drift, amp = self._profile(symbol)
        if symbol == "APLUS":
            drift = 0.10
        return _series(symbol, "4H", 160, base, drift, amp)

    def weekly(self, symbol: str) -> list[Candle]:
        base, drift, amp = self._profile(symbol)
        return _series(symbol, "1W", 80, base, drift * 4.2, amp * 2)

    def company_name(self, symbol: str) -> str:
        return {
            "SSTR": "Swing Suite Strong Fixture Corp.",
            "APLUS": "A Plus Watch Fixture Corp.",
            "BTIER": "B Tier Developing Fixture Corp.",
            "ZERO": "Zero Candidate Fixture Corp.",
            "SPY": "SPDR S&P 500 ETF Trust",
            "QQQ": "Invesco QQQ Trust",
        }.get(symbol, symbol)

    def sector(self, symbol: str) -> str:
        return "Technology" if symbol != "ZERO" else "Industrials"

    def option_quotes(self, symbol: str) -> list[OptionQuote]:
        if self.scenario == "technical_watch":
            return []
        if symbol == "ZERO":
            return [OptionQuote("FIXTURE", 21, 0.30, 1.0, 1.4, 50, 10, 85, FIXTURE_TIMESTAMP)]
        if symbol == "APLUS":
            return [OptionQuote("FIXTURE", 52, 0.50, 2.00, 2.22, 650, 180, 58, FIXTURE_TIMESTAMP)]
        if symbol == "BTIER":
            return [OptionQuote("FIXTURE", 52, 0.50, 2.00, 2.22, 650, 180, 58, FIXTURE_TIMESTAMP)]
        return [OptionQuote("FIXTURE", 52, 0.55, 2.10, 2.26, 1200, 350, 42, FIXTURE_TIMESTAMP)]

    def catalyst(self, symbol: str) -> Catalyst:
        now = FIXTURE_TIMESTAMP
        if symbol == "ZERO":
            return Catalyst(
                symbol=symbol,
                summary="No verified catalyst; simulated weak setup.",
                verified=False,
                source_title="Fixture weak candidate",
                publisher="SwingSuiteScreener fixtures",
                source_url="fixture:zero",
                publication_timestamp=now,
                retrieval_timestamp=now,
                earnings_date="2026-06-23",
                major_event_risk=True,
            )
        return Catalyst(
            symbol=symbol,
            summary="Verified simulated technical continuation with sector support.",
            verified=True,
            source_title="Fixture catalyst record",
            publisher="SwingSuiteScreener fixtures",
            source_url=f"fixture:{symbol.lower()}",
            publication_timestamp=now,
            retrieval_timestamp=now,
            earnings_date="2026-08-15",
            major_event_risk=False,
        )
