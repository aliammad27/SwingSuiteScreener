from __future__ import annotations

from scanner.models import Candle, OptionQuote
from scanner.providers.base import MarketDataProvider, OptionDataProvider


class CachedMarketDataProvider(MarketDataProvider):
    def __init__(self, delegate: MarketDataProvider) -> None:
        self.delegate = delegate
        self._daily: dict[str, list[Candle]] = {}
        self._four_hour: dict[str, list[Candle]] = {}
        self._weekly: dict[str, list[Candle]] = {}
        self._company: dict[str, str] = {}
        self._sector: dict[str, str] = {}

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

    def company_name(self, symbol: str) -> str:
        if symbol not in self._company:
            self._company[symbol] = self.delegate.company_name(symbol)
        return self._company[symbol]

    def sector(self, symbol: str) -> str:
        if symbol not in self._sector:
            self._sector[symbol] = self.delegate.sector(symbol)
        return self._sector[symbol]


class CachedOptionDataProvider(OptionDataProvider):
    def __init__(self, delegate: OptionDataProvider) -> None:
        self.delegate = delegate
        self._quotes: dict[str, list[OptionQuote]] = {}
        self.option_feed = getattr(delegate, "option_feed", "")

    def option_quotes(self, symbol: str) -> list[OptionQuote]:
        if symbol not in self._quotes:
            self._quotes[symbol] = self.delegate.option_quotes(symbol)
        return self._quotes[symbol]
