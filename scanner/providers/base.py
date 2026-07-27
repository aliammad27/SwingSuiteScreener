from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from scanner.models import Candle, EventRisk, OptionContractSnapshot, StrategyLane


class MarketDataProvider(ABC):
    stock_feed: str = "unknown"

    @abstractmethod
    def daily(self, symbol: str) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    def one_hour(self, symbol: str) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    def weekly(self, symbol: str) -> list[Candle]:
        raise NotImplementedError


class OptionDataProvider(ABC):
    option_feed: str = "unknown"

    @abstractmethod
    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        raise NotImplementedError

    def put_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        del symbol, expiration_date_gte, expiration_date_lte, as_of
        return []

    @abstractmethod
    def latest_quotes(
        self,
        contracts: list[OptionContractSnapshot],
        as_of: datetime,
    ) -> list[OptionContractSnapshot]:
        raise NotImplementedError


class EventRiskProvider(ABC):
    @abstractmethod
    def event_risk(
        self,
        symbol: str,
        as_of: datetime,
        lane: StrategyLane,
    ) -> EventRisk:
        raise NotImplementedError
