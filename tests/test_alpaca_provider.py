from __future__ import annotations

from typing import Any

import pytest
import requests

import scanner.providers.alpaca as alpaca_module
from scanner.providers.alpaca import AlpacaDataProvider


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
