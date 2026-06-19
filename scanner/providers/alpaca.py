from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from scanner.models import Candle, Catalyst, OptionQuote
from scanner.providers.base import CatalystProvider, MarketDataProvider, OptionDataProvider


class AlpacaConfigurationError(RuntimeError):
    pass


class AlpacaDataProvider(MarketDataProvider, OptionDataProvider):
    """Direct production provider using Alpaca's HTTP APIs.

    The implementation intentionally reads market and option data only. It contains no account,
    position, order, paper-trading, or live-trading methods.
    """

    def __init__(self) -> None:
        self.key = os.environ.get("ALPACA_API_KEY_ID")
        self.secret = os.environ.get("ALPACA_API_SECRET_KEY")
        self.base_url = os.environ.get("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")
        self.feed = os.environ.get("ALPACA_FEED", "iex")
        self.option_feed = os.environ.get("ALPACA_OPTION_FEED", "indicative")
        if not self.key or not self.secret:
            raise AlpacaConfigurationError("Alpaca data credentials are not configured.")

    def _headers(self) -> dict[str, str]:
        return {"APCA-API-KEY-ID": self.key or "", "APCA-API-SECRET-KEY": self.secret or ""}

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        import requests

        response = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Alpaca response shape.")
        return data

    def _bars(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        data = self._get(
            "/v2/stocks/bars",
            {"symbols": symbol, "timeframe": timeframe, "limit": str(limit), "feed": self.feed},
        )
        bars = data.get("bars", {}).get(symbol, [])
        candles: list[Candle] = []
        for bar in bars:
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromisoformat(bar["t"].replace("Z", "+00:00")),
                    open=float(bar["o"]),
                    high=float(bar["h"]),
                    low=float(bar["l"]),
                    close=float(bar["c"]),
                    volume=int(bar["v"]),
                    completed=True,
                    source="alpaca",
                )
            )
        return candles

    def daily(self, symbol: str) -> list[Candle]:
        return self._bars(symbol, "1Day", 260)

    def four_hour(self, symbol: str) -> list[Candle]:
        return self._bars(symbol, "4Hour", 160)

    def weekly(self, symbol: str) -> list[Candle]:
        return self._bars(symbol, "1Week", 80)

    def company_name(self, symbol: str) -> str:
        return symbol

    def sector(self, symbol: str) -> str:
        return "Unknown"

    def option_quotes(self, symbol: str) -> list[OptionQuote]:
        data = self._get(
            f"/v1beta1/options/snapshots/{symbol}",
            {"limit": "100", "feed": self.option_feed},
        )
        snapshots = data.get("snapshots", {})
        quotes: list[OptionQuote] = []
        for contract, snapshot in snapshots.items():
            quote = snapshot.get("latestQuote") or {}
            greeks = snapshot.get("greeks") or {}
            details = snapshot.get("details") or {}
            expiration = details.get("expiration_date")
            dte = 0
            if expiration:
                expiry = datetime.fromisoformat(expiration).replace(tzinfo=UTC)
                dte = max((expiry.date() - datetime.now(UTC).date()).days, 0)
            quotes.append(
                OptionQuote(
                    symbol=contract,
                    dte=dte,
                    delta=float(greeks.get("delta", 0.0)),
                    bid=float(quote.get("bp", 0.0)),
                    ask=float(quote.get("ap", 0.0)),
                    open_interest=int(snapshot.get("openInterest", 0) or 0),
                    volume=int(snapshot.get("dailyBar", {}).get("v", 0) or 0),
                    implied_volatility_rank=None,
                    timestamp=datetime.now(UTC),
                )
            )
        return quotes


class NullCatalystProvider(CatalystProvider):
    def catalyst(self, symbol: str) -> Catalyst:
        now = datetime.now(UTC)
        return Catalyst(
            symbol=symbol,
            summary="Technical continuation only",
            verified=True,
            source_title="No live catalyst provider configured",
            publisher="SwingSuiteScreener",
            source_url="local:none",
            publication_timestamp=None,
            retrieval_timestamp=now,
            earnings_date=None,
            major_event_risk=False,
        )
