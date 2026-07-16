from __future__ import annotations

from datetime import date

from scanner.models import Candle, OptionContractSnapshot
from scanner.providers.base import MarketDataProvider, OptionDataProvider


class CachedMarketDataProvider(MarketDataProvider):
    def __init__(self, delegate: MarketDataProvider) -> None:
        self.delegate = delegate
        self._daily: dict[str, list[Candle]] = {}
        self._four_hour: dict[str, list[Candle]] = {}
        self._weekly: dict[str, list[Candle]] = {}

    def daily(self, symbol: str) -> list[Candle]:
        if symbol not in self._daily:
            self._daily[symbol] = self.delegate.daily(symbol)
        return self._daily[symbol]

    def four_hour(self, symbol: str) -> list[Candle]:
        if symbol not in self._four_hour:
            self._four_hour[symbol] = self.delegate.four_hour(symbol)
        return self._four_hour[symbol]

    def weekly(self, symbol: str) -> list[Candle]:
        if symbol not in self._weekly:
            self._weekly[symbol] = self.delegate.weekly(symbol)
        return self._weekly[symbol]


class CachedOptionDataProvider(OptionDataProvider):
    def __init__(self, delegate: OptionDataProvider) -> None:
        self.delegate = delegate
        self._chains: dict[tuple[str, date, date], list[OptionContractSnapshot]] = {}
        self.option_feed = getattr(delegate, "option_feed", "unknown")

    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[OptionContractSnapshot]:
        key = (symbol, expiration_date_gte, expiration_date_lte)
        if key not in self._chains:
            self._chains[key] = self.delegate.call_chain(
                symbol, expiration_date_gte, expiration_date_lte
            )
        return self._chains[key]
