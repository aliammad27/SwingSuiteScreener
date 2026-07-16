from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from scanner.models import Candle, EventRisk, OptionContractSnapshot


@dataclass(frozen=True)
class HistoricalOptionContract:
    contract_symbol: str
    underlying_symbol: str
    expiration_date: date
    strike: float
    shares_per_contract: int
    exercise_style: str


@dataclass(frozen=True)
class HistoricalOptionQuote:
    contract_symbol: str
    timestamp: datetime
    bid: float
    ask: float
    bid_size: int
    ask_size: int


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


class OptionDataProvider(ABC):
    option_feed: str = "unknown"

    @abstractmethod
    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[OptionContractSnapshot]:
        raise NotImplementedError


class EventRiskProvider(ABC):
    @abstractmethod
    def event_risk(self, symbol: str) -> EventRisk:
        raise NotImplementedError


class HistoricalOptionDataProvider(ABC):
    @abstractmethod
    def call_contracts(
        self,
        symbol: str,
        as_of: date,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[HistoricalOptionContract]:
        raise NotImplementedError

    @abstractmethod
    def quotes(
        self,
        contract_symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalOptionQuote]:
        raise NotImplementedError
