from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Any

from scanner.providers.base import (
    HistoricalOptionContract,
    HistoricalOptionDataProvider,
    HistoricalOptionQuote,
)


class MassiveConfigurationError(RuntimeError):
    pass


def _nanoseconds_to_datetime(value: object) -> datetime:
    try:
        nanoseconds = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("Massive quote timestamp is invalid.") from exc
    return datetime.fromtimestamp(nanoseconds / 1_000_000_000, UTC)


class MassiveHistoricalOptionProvider(HistoricalOptionDataProvider):
    """Read-only Massive adapter for point-in-time contract references and quotes."""

    def __init__(self) -> None:
        self.key = os.environ.get("MASSIVE_API_KEY")
        self.base_url = os.environ.get("MASSIVE_BASE_URL", "https://api.massive.com")
        if not self.key:
            raise MassiveConfigurationError(
                "MASSIVE_API_KEY is required for historical option research."
            )

    def _get(self, path_or_url: str, params: dict[str, str]) -> dict[str, Any]:
        import requests

        url = (
            path_or_url
            if path_or_url.startswith("https://")
            else f"{self.base_url}{path_or_url}"
        )
        query = dict(params)
        query["apiKey"] = self.key or ""
        response = requests.get(url, params=query, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected Massive response shape.")
        return payload

    def _pages(
        self,
        path: str,
        params: dict[str, str],
        *,
        maximum_pages: int = 50,
    ) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        next_path = path
        next_params = params
        for _ in range(maximum_pages):
            payload = self._get(next_path, next_params)
            pages.append(payload)
            raw_next = payload.get("next_url")
            if not raw_next:
                return pages
            next_path = str(raw_next)
            next_params = {}
        raise RuntimeError("Massive pagination exceeded the safety limit.")

    def call_contracts(
        self,
        symbol: str,
        as_of: date,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[HistoricalOptionContract]:
        pages = self._pages(
            "/v3/reference/options/contracts",
            {
                "underlying_ticker": symbol,
                "contract_type": "call",
                "as_of": as_of.isoformat(),
                "expiration_date.gte": expiration_date_gte.isoformat(),
                "expiration_date.lte": expiration_date_lte.isoformat(),
                "expired": "true",
                "sort": "expiration_date",
                "order": "asc",
                "limit": "1000",
            },
        )
        contracts: dict[str, HistoricalOptionContract] = {}
        for page in pages:
            raw_results = page.get("results", [])
            if not isinstance(raw_results, list):
                raise RuntimeError("Massive contract results must be a list.")
            for raw in raw_results:
                if not isinstance(raw, dict) or raw.get("contract_type") != "call":
                    continue
                ticker = str(raw.get("ticker", ""))
                expiration = raw.get("expiration_date")
                strike = raw.get("strike_price")
                if not ticker or not expiration or strike is None:
                    continue
                contracts[ticker] = HistoricalOptionContract(
                    contract_symbol=ticker,
                    underlying_symbol=str(raw.get("underlying_ticker", symbol)),
                    expiration_date=date.fromisoformat(str(expiration)),
                    strike=float(strike),
                    shares_per_contract=int(raw.get("shares_per_contract", 100)),
                    exercise_style=str(raw.get("exercise_style", "american")),
                )
        return sorted(
            contracts.values(),
            key=lambda item: (item.expiration_date, item.strike, item.contract_symbol),
        )

    def quotes(
        self,
        contract_symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalOptionQuote]:
        pages = self._pages(
            f"/v3/quotes/{contract_symbol}",
            {
                "timestamp.gte": str(int(start.timestamp() * 1_000_000_000)),
                "timestamp.lte": str(int(end.timestamp() * 1_000_000_000)),
                "sort": "timestamp",
                "order": "asc",
                "limit": "50000",
            },
        )
        quotes: list[HistoricalOptionQuote] = []
        for page in pages:
            raw_results = page.get("results", [])
            if not isinstance(raw_results, list):
                raise RuntimeError("Massive quote results must be a list.")
            for raw in raw_results:
                if not isinstance(raw, dict):
                    continue
                bid = raw.get("bid_price")
                ask = raw.get("ask_price")
                timestamp = raw.get("sip_timestamp")
                if bid is None or ask is None or timestamp is None:
                    continue
                quotes.append(
                    HistoricalOptionQuote(
                        contract_symbol=contract_symbol,
                        timestamp=_nanoseconds_to_datetime(timestamp),
                        bid=float(bid),
                        ask=float(ask),
                        bid_size=int(raw.get("bid_size", 0) or 0),
                        ask_size=int(raw.get("ask_size", 0) or 0),
                    )
                )
        return sorted(quotes, key=lambda quote: quote.timestamp)
