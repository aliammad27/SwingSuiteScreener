from __future__ import annotations

from datetime import date, datetime

from scanner.models import Candle, OptionContractSnapshot
from scanner.providers.base import MarketDataProvider, OptionDataProvider


class CachedMarketDataProvider(MarketDataProvider):
    def __init__(self, delegate: MarketDataProvider) -> None:
        self.delegate = delegate
        self.stock_feed = getattr(delegate, "stock_feed", "unknown")
        self._daily: dict[str, list[Candle]] = {}
        self._one_hour: dict[str, list[Candle]] = {}
        self._weekly: dict[str, list[Candle]] = {}

    def daily(self, symbol: str) -> list[Candle]:
        if symbol not in self._daily:
            self._daily[symbol] = self.delegate.daily(symbol)
        return self._daily[symbol]

    def one_hour(self, symbol: str) -> list[Candle]:
        if symbol not in self._one_hour:
            self._one_hour[symbol] = self.delegate.one_hour(symbol)
        return self._one_hour[symbol]

    def weekly(self, symbol: str) -> list[Candle]:
        if symbol not in self._weekly:
            self._weekly[symbol] = self.delegate.weekly(symbol)
        return self._weekly[symbol]


class CachedOptionDataProvider(OptionDataProvider):
    def __init__(self, delegate: OptionDataProvider) -> None:
        self.delegate = delegate
        self._eligible_underlyings: dict[
            tuple[tuple[str, ...], date, date], set[str]
        ] = {}
        self._chains: dict[
            tuple[str, date, date, date], list[OptionContractSnapshot]
        ] = {}
        self.option_feed = getattr(delegate, "option_feed", "unknown")

    def eligible_underlyings(
        self,
        symbols: list[str],
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> set[str]:
        key = (tuple(sorted(symbols)), expiration_date_gte, expiration_date_lte)
        if key not in self._eligible_underlyings:
            self._eligible_underlyings[key] = self.delegate.eligible_underlyings(
                symbols,
                expiration_date_gte,
                expiration_date_lte,
            )
        return set(self._eligible_underlyings[key])

    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        key = (symbol, expiration_date_gte, expiration_date_lte, as_of.date())
        if key not in self._chains:
            self._chains[key] = self.delegate.call_chain(
                symbol, expiration_date_gte, expiration_date_lte, as_of
            )
        return self._chains[key]

    def latest_quotes(
        self,
        contracts: list[OptionContractSnapshot],
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        return self.delegate.latest_quotes(contracts, as_of)
