from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import requests

import scanner.providers.alpaca as alpaca_module
from scanner.providers.alpaca import AlpacaDataProvider, parse_occ_call_symbol


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
    chain = provider.call_chain("AAPL", date(2026, 8, 1), date(2026, 10, 1))
    assert len(chain) == 2
    assert seen_params[0]["type"] == "call"
    assert seen_params[0]["limit"] == "1000"
    assert seen_params[1]["page_token"] == expected_page_token
