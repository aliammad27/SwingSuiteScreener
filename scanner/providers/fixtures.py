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
        if idx > count - 6 and drift != 0:
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
        # Put scenarios: bearish profiles.  Amplitude must be large enough for real RSI
        # oscillation (amp * 0.12 > |drift| ensures some up bars exist), but counts
        # are chosen so the LAST bars fall in the negative sin phase (keeping MACD bearish).
        if symbol in {"SPUT", "APUT", "BPUT"}:
            if symbol == "APUT":
                return 120, -0.055, 1.5
            if symbol == "BPUT":
                return 80, -0.018, 0.6
            return 150, -0.05, 2.0  # SPUT: moderate drift so RSI stays 30-40, not pinned at 0
        # SPY/QQQ in put scenarios: falling market for put-supportive regime
        if self.scenario in {"put_s_tier", "put_a_plus", "put_b_tier"}:
            if symbol in {"SPY", "QQQ"}:
                return 450, -0.030, 0.8
        if symbol in {"SPY", "QQQ"}:
            return 100, 0.04, 1.5
        return 70, 0.045, 3.8

    def daily(self, symbol: str) -> list[Candle]:
        base, drift, amp = self._profile(symbol)
        # SPUT/APUT use count=272 (negative sin phase) — MACD stays below signal.
        # BPUT uses count=280 (positive sin phase, MACD still below signal but recovering):
        # rsi_falling=False and histogram_falling=False keep the score at 65, which
        # passes B-tier (daily ≥55) but fails A+ (daily ≥70).
        if symbol == "SPUT" or symbol == "APUT":
            count = 272
        elif symbol == "BPUT":
            count = 280
        else:
            count = 260
        return _series(symbol, "1D", count, base, drift, amp)

    def four_hour(self, symbol: str) -> list[Candle]:
        base, drift, amp = self._profile(symbol)
        if symbol == "APLUS":
            drift = 0.10
        # SPUT/APUT use count=170 (negative sin phase — MACD reliably below signal).
        # BPUT uses count=180 (positive sin phase, score=65): passes B-tier (4H ≥60)
        # but fails A+ (4H ≥75).
        if symbol == "SPUT" or symbol == "APUT":
            count = 170
        elif symbol == "BPUT":
            count = 180
        else:
            count = 160
        return _series(symbol, "4H", count, base, drift, amp)

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
            "SPUT": "S-Put Tier Fixture Corp.",
            "APUT": "A-Plus Put Fixture Corp.",
            "BPUT": "B-Put Tier Fixture Corp.",
        }.get(symbol, symbol)

    def sector(self, symbol: str) -> str:
        if symbol == "ZERO":
            return "Industrials"
        if symbol in {"SPUT", "APUT", "BPUT"}:
            return "Financials"
        return "Technology"

    def option_quotes(self, symbol: str) -> list[OptionQuote]:
        if self.scenario == "technical_watch":
            return []
        if symbol == "ZERO":
            return [OptionQuote("FIXTURE", 21, 0.30, 1.0, 1.4, 50, 10, 85, FIXTURE_TIMESTAMP)]
        if symbol == "APLUS":
            return [OptionQuote("FIXTURE", 52, 0.50, 2.00, 2.22, 650, 180, 58, FIXTURE_TIMESTAMP)]
        if symbol == "BTIER":
            return [OptionQuote("FIXTURE", 52, 0.50, 2.00, 2.22, 650, 180, 58, FIXTURE_TIMESTAMP)]
        # Put fixture symbols: use absolute delta ~0.50 (call-side from free feed).
        # SPUT uses tighter spread so classify_put_option_liquidity returns "Good" (S-tier requires it).
        if symbol == "SPUT":
            return [OptionQuote("FIXTURE", 57, 0.50, 3.80, 4.18, 1200, 450, 38, FIXTURE_TIMESTAMP)]
        if symbol == "APUT":
            return [OptionQuote("FIXTURE", 58, 0.50, 2.00, 2.22, 800, 220, 38, FIXTURE_TIMESTAMP)]
        if symbol == "BPUT":
            return [OptionQuote("FIXTURE", 58, 0.50, 2.00, 2.22, 650, 180, 38, FIXTURE_TIMESTAMP)]
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
        if symbol in {"SPUT", "APUT", "BPUT"}:
            return Catalyst(
                symbol=symbol,
                summary="Technical continuation only",
                verified=True,
                source_title="Fixture bearish catalyst record",
                publisher="SwingSuiteScreener fixtures",
                source_url=f"fixture:{symbol.lower()}",
                publication_timestamp=now,
                retrieval_timestamp=now,
                earnings_date="2026-09-15",
                major_event_risk=False,
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
