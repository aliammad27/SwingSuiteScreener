from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from scanner.models import Candle, Catalyst, OptionQuote
from scanner.providers.base import CatalystProvider, MarketDataProvider, OptionDataProvider


class AlpacaConfigurationError(RuntimeError):
    pass


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class AlpacaDataProvider(MarketDataProvider, OptionDataProvider):
    """Direct production provider using Alpaca's HTTP APIs.

    The implementation intentionally reads market and option data only. It contains no account,
    position, order, paper-trading, or live-trading methods.
    """

    def __init__(self) -> None:
        self.key: str | None = os.environ.get("ALPACA_API_KEY_ID")
        self.secret: str | None = os.environ.get("ALPACA_API_SECRET_KEY")
        self.base_url: str = os.environ.get("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")
        self.feed: str = os.environ.get("ALPACA_FEED", "iex")
        self.option_feed: str = os.environ.get("ALPACA_OPTION_FEED", "indicative")
        self.min_request_interval_seconds: float = _float_env(
            "ALPACA_MIN_REQUEST_INTERVAL_SECONDS",
            0.45,
        )
        self.max_retries: int = _int_env("ALPACA_MAX_RETRIES", 8)
        self.retry_base_seconds: float = _float_env("ALPACA_RETRY_BASE_SECONDS", 2.0)
        self._last_request_at: float = 0.0
        if not self.key or not self.secret:
            raise AlpacaConfigurationError("Alpaca data credentials are not configured.")

    def _headers(self) -> dict[str, str]:
        return {"APCA-API-KEY-ID": self.key or "", "APCA-API-SECRET-KEY": self.secret or ""}

    def _throttle(self) -> None:
        if self.min_request_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait_seconds = self.min_request_interval_seconds - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def _retry_wait_seconds(self, response: Any, attempt: int) -> float:
        headers = getattr(response, "headers", {})
        retry_after = str(headers.get("Retry-After", "")) if isinstance(headers, dict) else ""
        if retry_after:
            try:
                wait_seconds = max(float(retry_after), self.retry_base_seconds)
                return min(wait_seconds, 90.0)
            except ValueError:
                pass
        exponential_wait = self.retry_base_seconds * float(2**attempt)
        return min(exponential_wait, 90.0)

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        import requests

        last_status = "unknown"
        for attempt in range(self.max_retries + 1):
            try:
                self._throttle()
                response = requests.get(
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    params=params,
                    timeout=20,
                )
                self._last_request_at = time.monotonic()
                last_status = str(response.status_code)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self.max_retries:
                        break
                    wait_seconds = self._retry_wait_seconds(response, attempt)
                    print(
                        f"Alpaca transient HTTP {response.status_code}; retrying in {wait_seconds:.1f}s.",
                        flush=True,
                    )
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise RuntimeError("Unexpected Alpaca response shape.")
                return data
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(f"Alpaca request failed after retries for {path}.") from exc
                wait_seconds = min(self.retry_base_seconds * (2**attempt), 90.0)
                print(f"Alpaca network error; retrying in {wait_seconds:.1f}s.", flush=True)
                time.sleep(wait_seconds)
        raise RuntimeError(f"Alpaca request failed after retries with HTTP {last_status} for {path}.")

    def _bars(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        end = datetime.now(UTC) - timedelta(minutes=20)
        lookback_days = {"1Day": 520, "4Hour": 240, "1Week": 900}.get(timeframe, 240)
        start = end - timedelta(days=lookback_days)
        data = self._get(
            "/v2/stocks/bars",
            {
                "symbols": symbol,
                "timeframe": timeframe,
                "limit": str(limit),
                "feed": self.feed,
                "adjustment": "all",
                "sort": "desc",
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),
            },
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
        return sorted(candles, key=lambda candle: candle.timestamp)

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
