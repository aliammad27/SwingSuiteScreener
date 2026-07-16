from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from scanner.providers.massive import (
    MassiveConfigurationError,
    MassiveHistoricalOptionProvider,
)


def test_massive_provider_requires_a_research_key(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    with pytest.raises(MassiveConfigurationError):
        MassiveHistoricalOptionProvider()


def test_massive_provider_parses_contracts_and_quotes(monkeypatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "test")
    provider = MassiveHistoricalOptionProvider()
    payloads = [
        {
            "results": [
                {
                    "ticker": "O:TEST260619C00100000",
                    "underlying_ticker": "TEST",
                    "contract_type": "call",
                    "expiration_date": "2026-06-19",
                    "strike_price": 100,
                    "shares_per_contract": 100,
                    "exercise_style": "american",
                }
            ]
        },
        {
            "results": [
                {
                    "sip_timestamp": 1_765_000_000_000_000_000,
                    "bid_price": 4.10,
                    "ask_price": 4.25,
                    "bid_size": 12,
                    "ask_size": 15,
                }
            ]
        },
    ]

    def fake_get(_path: str, _params: dict[str, str]) -> dict[str, object]:
        return payloads.pop(0)

    monkeypatch.setattr(provider, "_get", fake_get)
    contracts = provider.call_contracts(
        "TEST",
        date(2026, 5, 1),
        date(2026, 6, 1),
        date(2026, 7, 31),
    )
    assert contracts[0].contract_symbol == "O:TEST260619C00100000"
    quotes = provider.quotes(
        contracts[0].contract_symbol,
        datetime(2025, 12, 1, tzinfo=UTC),
        datetime(2025, 12, 2, tzinfo=UTC),
    )
    assert quotes[0].bid == 4.10
    assert quotes[0].ask == 4.25
    assert quotes[0].timestamp.tzinfo is UTC
