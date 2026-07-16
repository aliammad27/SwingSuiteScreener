from __future__ import annotations

import logging
import os
import re
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

from scanner.config import load_config
from scanner.models import (
    Candle,
    EventRisk,
    EventRiskStatus,
    OptionContractSnapshot,
)
from scanner.providers.base import EventRiskProvider, MarketDataProvider, OptionDataProvider

log = logging.getLogger(__name__)


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


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


_OCC_CALL_SYMBOL = re.compile(r"^([A-Z0-9.]+)(\d{6})C(\d{8})$")


def parse_occ_call_symbol(contract_symbol: str) -> tuple[str, date, float]:
    match = _OCC_CALL_SYMBOL.match(contract_symbol)
    if match is None:
        raise ValueError(f"Unsupported OCC call symbol: {contract_symbol}")
    expiry = datetime.strptime(match.group(2), "%y%m%d").date()
    strike = int(match.group(3)) / 1000
    return match.group(1), expiry, strike


class AlpacaDataProvider(MarketDataProvider, OptionDataProvider):
    """Read-only Alpaca market-data adapter.

    This class intentionally has no account, position, order, exercise, or paper-trading methods.
    """

    def __init__(self) -> None:
        self.key = os.environ.get("ALPACA_API_KEY_ID")
        self.secret = os.environ.get("ALPACA_API_SECRET_KEY")
        self.base_url = os.environ.get("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")
        self.feed = os.environ.get("ALPACA_FEED", "iex")
        self.option_feed = os.environ.get("ALPACA_OPTION_FEED", "indicative")
        self.min_request_interval_seconds = _float_env(
            "ALPACA_MIN_REQUEST_INTERVAL_SECONDS", 0.45
        )
        self.max_retries = _int_env("ALPACA_MAX_RETRIES", 8)
        self.retry_base_seconds = _float_env("ALPACA_RETRY_BASE_SECONDS", 2.0)
        self._last_request_at = 0.0
        if not self.key or not self.secret:
            raise AlpacaConfigurationError("Alpaca data credentials are not configured.")

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.key or "",
            "APCA-API-SECRET-KEY": self.secret or "",
        }

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_seconds = self.min_request_interval_seconds - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def _retry_wait_seconds(self, response: Any, attempt: int) -> float:
        retry_after = getattr(response, "headers", {}).get("Retry-After", "")
        try:
            return min(max(float(retry_after), self.retry_base_seconds), 90.0)
        except (TypeError, ValueError):
            return min(self.retry_base_seconds * float(2**attempt), 90.0)

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
                    log.warning(
                        "Alpaca HTTP %s for %s; retrying in %.1fs.",
                        response.status_code,
                        path,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("Unexpected Alpaca response shape.")
                return payload
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(f"Alpaca request failed for {path}.") from exc
                time.sleep(min(self.retry_base_seconds * (2**attempt), 90.0))
        raise RuntimeError(
            f"Alpaca request failed after retries with HTTP {last_status} for {path}."
        )

    def _bars(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        end = datetime.now(UTC) - timedelta(minutes=20)
        lookback_days = {"1Day": 520, "4Hour": 240, "1Week": 900}.get(timeframe, 240)
        start = end - timedelta(days=lookback_days)
        payload = self._get(
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
        raw_bars = payload.get("bars", {})
        bars = raw_bars.get(symbol, []) if isinstance(raw_bars, dict) else []
        candles: list[Candle] = []
        for raw in bars:
            if not isinstance(raw, dict):
                continue
            timestamp = _parse_datetime(raw.get("t"))
            if timestamp is None:
                continue
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=float(raw["o"]),
                    high=float(raw["h"]),
                    low=float(raw["l"]),
                    close=float(raw["c"]),
                    volume=int(raw["v"]),
                    completed=True,
                    source="alpaca",
                )
            )
        return sorted(candles, key=lambda candle: candle.timestamp)

    def daily(self, symbol: str) -> list[Candle]:
        return self._bars(symbol, "1Day", 320)

    def four_hour(self, symbol: str) -> list[Candle]:
        return self._bars(symbol, "4Hour", 200)

    def weekly(self, symbol: str) -> list[Candle]:
        return self._bars(symbol, "1Week", 100)

    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[OptionContractSnapshot]:
        snapshots: dict[str, OptionContractSnapshot] = {}
        page_token = ""
        for _ in range(20):
            params = {
                "feed": self.option_feed,
                "type": "call",
                "expiration_date_gte": expiration_date_gte.isoformat(),
                "expiration_date_lte": expiration_date_lte.isoformat(),
                "limit": "1000",
            }
            if page_token:
                params["page_token"] = page_token
            payload = self._get(f"/v1beta1/options/snapshots/{symbol}", params)
            raw_snapshots = payload.get("snapshots", {})
            if not isinstance(raw_snapshots, dict):
                raise RuntimeError("Alpaca option-chain snapshots must be a mapping.")
            for contract_symbol, raw_snapshot in raw_snapshots.items():
                if not isinstance(raw_snapshot, dict):
                    continue
                try:
                    underlying, expiry, strike = parse_occ_call_symbol(str(contract_symbol))
                except ValueError:
                    continue
                quote = raw_snapshot.get("latestQuote") or {}
                greeks = raw_snapshot.get("greeks") or {}
                daily_bar = raw_snapshot.get("dailyBar") or {}
                if not all(isinstance(item, dict) for item in (quote, greeks, daily_bar)):
                    continue
                quote_time = _parse_datetime(quote.get("t"))
                if quote_time is None:
                    quote_time = datetime.fromtimestamp(0, UTC)
                snapshots[str(contract_symbol)] = OptionContractSnapshot(
                    contract_symbol=str(contract_symbol),
                    underlying_symbol=underlying,
                    expiration_date=expiry,
                    strike=strike,
                    dte=max((expiry - datetime.now(UTC).date()).days, 0),
                    delta=float(greeks.get("delta", 0.0) or 0.0),
                    gamma=float(greeks["gamma"]) if greeks.get("gamma") is not None else None,
                    theta=float(greeks["theta"]) if greeks.get("theta") is not None else None,
                    vega=float(greeks["vega"]) if greeks.get("vega") is not None else None,
                    implied_volatility=(
                        float(raw_snapshot["impliedVolatility"])
                        if raw_snapshot.get("impliedVolatility") is not None
                        else None
                    ),
                    bid=float(quote.get("bp", 0.0) or 0.0),
                    ask=float(quote.get("ap", 0.0) or 0.0),
                    bid_size=int(quote.get("bs", 0) or 0),
                    ask_size=int(quote.get("as", 0) or 0),
                    open_interest=int(raw_snapshot.get("openInterest", 0) or 0),
                    volume=int(daily_bar.get("v", 0) or 0),
                    feed=self.option_feed,
                    quote_timestamp=quote_time,
                )
            raw_next = payload.get("next_page_token")
            page_token = str(raw_next) if raw_next else ""
            if not page_token:
                break
        else:
            raise RuntimeError("Alpaca option-chain pagination exceeded the safety limit.")
        return sorted(snapshots.values(), key=lambda item: (item.expiration_date, item.strike))


class ConfiguredEventRiskProvider(EventRiskProvider):
    def event_risk(self, symbol: str) -> EventRisk:
        config = load_config("events")
        default = str(config.get("default_status", EventRiskStatus.UNKNOWN.value))
        raw_events = config.get("events", {})
        raw = raw_events.get(symbol, {}) if isinstance(raw_events, dict) else {}
        if not isinstance(raw, dict):
            raw = {}
        raw_status = str(raw.get("status", default))
        try:
            status = EventRiskStatus(raw_status)
        except ValueError:
            status = EventRiskStatus.UNKNOWN
        raw_date = raw.get("earnings_date")
        earnings_date: date | None = None
        if isinstance(raw_date, date):
            earnings_date = raw_date
        elif raw_date:
            try:
                earnings_date = date.fromisoformat(str(raw_date))
            except ValueError:
                status = EventRiskStatus.UNKNOWN
        return EventRisk(
            symbol=symbol,
            status=status,
            earnings_date=earnings_date,
            summary=str(raw.get("summary", "Earnings date is not configured.")),
            source=str(raw.get("source", "config/events.yaml")),
            checked_at=datetime.now(UTC),
        )
