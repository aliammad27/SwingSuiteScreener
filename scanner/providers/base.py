from __future__ import annotations

from abc import ABC, abstractmethod

from scanner.models import Candle, Catalyst, OptionQuote


class MarketDataProvider(ABC):
    @abstractmethod
    def daily(self, symbol: str) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    def four_hour(self, symbol: str) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    def weekly(self, symbol: str) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    def company_name(self, symbol: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def sector(self, symbol: str) -> str:
        raise NotImplementedError


class OptionDataProvider(ABC):
    @abstractmethod
    def option_quotes(self, symbol: str) -> list[OptionQuote]:
        raise NotImplementedError


class CatalystProvider(ABC):
    @abstractmethod
    def catalyst(self, symbol: str) -> Catalyst:
        raise NotImplementedError
