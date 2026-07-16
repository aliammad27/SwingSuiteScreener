from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
import requests

import scanner.providers.alpaca as alpaca_module
from scanner.clocks import NY
from scanner.models import Candle
from scanner.providers.alpaca import (
    AlpacaDataProvider,
    _aggregate_regular_session_hours,
    parse_occ_call_symbol,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self.payload


def _provider(monkeypatch: pytest.MonkeyPatch) -> AlpacaDataProvider:
    monkeypatch.setenv("ALPACA_API_KEY_ID", "test-key")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ALPACA_MIN_REQUEST_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("ALPACA_MAX_RETRIES", "2")
    monkeypatch.setenv("ALPACA_RETRY_BASE_SECONDS", "0.01")
    return AlpacaDataProvider()


def test_alpaca_get_retries_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(monkeypatch)
    responses = [
        FakeResponse(429, headers={"Retry-After": "0.01"}),
        FakeResponse(200, {"ok": True}),
    ]
    sleeps: list[float] = []

    def fake_get(*args: object, **kwargs: object) -> FakeResponse:
        return responses.pop(0)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(alpaca_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = provider._get("/test", {})

    assert result == {"ok": True}
    assert sleeps == [0.01]


def test_alpaca_get_raises_runtime_error_after_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch)
    calls = 0

    def fake_get(*args: object, **kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(429)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(alpaca_module.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="after retries"):
        provider._get("/test", {})

    assert calls == 3


def test_occ_call_symbol_parser_retains_expiry_and_strike() -> None:
    underlying, expiry, strike = parse_occ_call_symbol("AAPL260821C00225000")
    assert underlying == "AAPL"
    assert expiry == date(2026, 8, 21)
    assert strike == 225.0


def test_regular_session_hours_are_anchored_at_0930_and_require_two_parts() -> None:
    def bar(hour: int, minute: int, price: float, volume: int) -> Candle:
        return Candle(
            symbol="AAPL",
            timeframe="30Min",
            timestamp=datetime(2026, 7, 16, hour, minute, tzinfo=NY).astimezone(UTC),
            open=price,
            high=price + 1,
            low=price - 1,
            close=price + 0.5,
            volume=volume,
            source="alpaca",
        )

    half_hours = [
        bar(9, 0, 90, 50),
        bar(9, 30, 100, 100),
        bar(10, 0, 101, 200),
        bar(10, 30, 102, 300),
        bar(11, 0, 103, 400),
        bar(14, 30, 110, 500),
    ]

    result = _aggregate_regular_session_hours(
        half_hours,
        datetime(2026, 7, 16, 15, 30, tzinfo=NY),
    )

    assert len(result) == 2
    assert result[0].timestamp.astimezone(NY).strftime("%H:%M") == "09:30"
    assert result[0].open == 100
    assert result[0].close == 101.5
    assert result[0].high == 102
    assert result[0].volume == 300
    assert result[1].timestamp.astimezone(NY).strftime("%H:%M") == "10:30"


def test_eligible_underlyings_uses_active_calls_in_lane_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch)
    pagination_cursor = "cursor-page-2"
    pages = [
        {
            "option_contracts": [
                {
                    "underlying_symbol": "AAPL",
                    "expiration_date": "2026-07-31",
                    "type": "call",
                    "status": "active",
                    "tradable": True,
                },
                {
                    "underlying_symbol": "MSFT",
                    "expiration_date": "2026-07-31",
                    "type": "put",
                    "status": "active",
                    "tradable": True,
                },
            ],
            "next_page_token": pagination_cursor,
        },
        {
            "option_contracts": [
                {
                    "underlying_symbol": "MSFT",
                    "expiration_date": "2026-08-07",
                    "type": "call",
                    "status": "active",
                    "tradable": True,
                }
            ]
        },
    ]
    seen: list[tuple[str, dict[str, str], str | None]] = []

    def fake_get(
        path: str,
        params: dict[str, str],
        *,
        base_url: str | None = None,
    ) -> dict[str, Any]:
        seen.append((path, params.copy(), base_url))
        return pages.pop(0)

    monkeypatch.setattr(provider, "_get", fake_get)

    eligible = provider.eligible_underlyings(
        ["AAPL", "MSFT", "NOPE"],
        date(2026, 7, 27),
        date(2026, 8, 9),
    )

    assert eligible == {"AAPL", "MSFT"}
    assert seen[0][0] == "/v2/options/contracts"
    assert seen[0][1]["type"] == "call"
    assert seen[1][1]["page_token"] == pagination_cursor
    assert seen[0][2] == provider.metadata_base_url


def test_call_chain_follows_pagination_and_filters_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch)
    pages = [
        {
            "snapshots": {
                "AAPL260821C00225000": {
                    "latestQuote": {
                        "bp": 5.0,
                        "ap": 5.2,
                        "bs": 10,
                        "as": 12,
                        "t": "2026-07-15T19:59:00Z",
                    },
                    "greeks": {"delta": 0.55, "gamma": 0.02, "theta": -0.08, "vega": 0.12},
                    "impliedVolatility": 0.32,
                    "openInterest": 900,
                    "dailyBar": {"v": 250},
                }
            },
            "next_page_token": "next",
        },
        {
            "snapshots": {
                "AAPL260918C00230000": {
                    "latestQuote": {
                        "bp": 4.0,
                        "ap": 4.2,
                        "bs": 8,
                        "as": 9,
                        "t": "2026-07-15T19:58:00Z",
                    },
                    "greeks": {"delta": 0.50},
                    "openInterest": 800,
                    "dailyBar": {"v": 180},
                }
            }
        },
    ]
    expected_page_token = str(pages[0]["next_page_token"])
    seen_params: list[dict[str, str]] = []

    def fake_get(path: str, params: dict[str, str]) -> dict[str, Any]:
        seen_params.append(params.copy())
        return pages.pop(0)

    monkeypatch.setattr(provider, "_get", fake_get)
    as_of = datetime(2026, 7, 15, 20, 0, tzinfo=UTC)
    chain = provider.call_chain(
        "AAPL",
        date(2026, 8, 1),
        date(2026, 10, 1),
        as_of,
    )
    assert len(chain) == 2
    assert chain[0].dte == 37
    assert seen_params[0]["type"] == "call"
    assert seen_params[0]["limit"] == "1000"
    assert seen_params[1]["page_token"] == expected_page_token


def test_latest_quotes_refreshes_top_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch)
    as_of = datetime(2026, 7, 15, 20, 0, tzinfo=UTC)
    monkeypatch.setattr(
        provider,
        "_get",
        lambda _path, _params: {
            "quotes": {
                "AAPL260821C00225000": {
                    "bp": 5.05,
                    "ap": 5.15,
                    "bs": 20,
                    "as": 22,
                    "t": "2026-07-15T20:00:00Z",
                }
            }
        },
    )
    from scanner.models import OptionContractSnapshot

    contract = OptionContractSnapshot(
        contract_symbol="AAPL260821C00225000",
        underlying_symbol="AAPL",
        expiration_date=date(2026, 8, 21),
        strike=225,
        dte=999,
        delta=0.6,
        gamma=0.02,
        theta=-0.08,
        vega=0.12,
        implied_volatility=0.3,
        bid=5.0,
        ask=5.2,
        bid_size=10,
        ask_size=12,
        open_interest=3000,
        volume=800,
        feed="opra",
        quote_timestamp=as_of.replace(minute=58),
    )
    refreshed = provider.latest_quotes([contract], as_of)[0]
    assert refreshed.bid == 5.05
    assert refreshed.ask == 5.15
    assert refreshed.dte == 37
    assert refreshed.quote_timestamp == as_of


def test_latest_quotes_omits_contracts_missing_from_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch)
    as_of = datetime(2026, 7, 15, 20, 0, tzinfo=UTC)
    monkeypatch.setattr(
        provider,
        "_get",
        lambda _path, _params: {"quotes": {}},
    )
    from scanner.models import OptionContractSnapshot

    contract = OptionContractSnapshot(
        contract_symbol="AAPL260821C00225000",
        underlying_symbol="AAPL",
        expiration_date=date(2026, 8, 21),
        strike=225,
        dte=37,
        delta=0.6,
        gamma=0.02,
        theta=-0.08,
        vega=0.12,
        implied_volatility=0.3,
        bid=5.0,
        ask=5.2,
        bid_size=10,
        ask_size=12,
        open_interest=3000,
        volume=800,
        feed="opra",
        quote_timestamp=as_of,
    )

    assert provider.latest_quotes([contract], as_of) == []
