from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ScanType(StrEnum):
    POST_CLOSE = "post_close"
    PREMARKET = "premarket"
    FOUR_HOUR = "four_hour"


class Grade(StrEnum):
    S_TIER = "S"
    A_PLUS = "A+"
    REJECTED = "Rejected"


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    completed: bool = True
    source: str = "fixture"


@dataclass(frozen=True)
class OptionQuote:
    symbol: str
    dte: int
    delta: float
    bid: float
    ask: float
    open_interest: int
    volume: int
    implied_volatility_rank: float | None
    timestamp: datetime


@dataclass(frozen=True)
class Catalyst:
    symbol: str
    summary: str
    verified: bool
    source_title: str
    publisher: str
    source_url: str
    publication_timestamp: datetime | None
    retrieval_timestamp: datetime
    earnings_date: str | None = None
    major_event_risk: bool = False


@dataclass(frozen=True)
class CommandResult:
    symbol: str
    score: int
    call_bias: str
    trend: str
    relative_strength: str
    relative_volume: float
    volume_state: str
    volatility_state: str
    structure: str
    above_vwap: bool
    anchored_vwap: float
    weekly_alignment: bool
    breakout_level: float
    breakout_confirmed: bool
    breakout_watch: bool
    pullback_support: float
    pullback_setup: bool
    extended: bool
    close: float
    ema21: float
    sma50: float
    sma200: float
    rejection_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MomentumResult:
    symbol: str
    timeframe: str
    score: int
    state: str
    rsi: float
    rsi_rising: bool
    macd: float
    macd_signal: float
    histogram: float
    histogram_rising: bool
    daily_filter_passed: bool
    bullish_confirmation: bool
    trigger: float
    support: float
    warning: float


@dataclass(frozen=True)
class EntryPlan:
    entry_mode: str
    trigger: float
    support: float
    invalidation: float
    nearest_resistance: float
    distance_to_trigger: float
    distance_to_support: float
    reward_to_risk: float | None
    status: str


@dataclass(frozen=True)
class Candidate:
    symbol: str
    company: str
    sector: str
    benchmark: str
    command: CommandResult
    daily_momentum: MomentumResult
    four_hour_momentum: MomentumResult
    option_liquidity: str
    catalyst: Catalyst
    market_regime: str
    entry_plan: EntryPlan
    grade: Grade
    missing_confirmation: str | None = None
    not_s_tier_reason: str | None = None
    rejection_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RejectedRecord:
    symbol: str
    stage: str
    reason_codes: list[str]
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ScanResult:
    scan_type: ScanType
    generated_at: datetime
    market_data_timestamp: datetime
    market_regime: str
    universe_count: int
    deterministic_pass_count: int
    research_count: int
    s_tier: list[Candidate]
    a_plus: list[Candidate]
    rejected: list[RejectedRecord]
    fixture: bool = False
