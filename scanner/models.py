from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class ScanType(StrEnum):
    POST_CLOSE = "post_close"
    PREMARKET = "premarket"
    FOUR_HOUR = "four_hour"


class StrategyLane(StrEnum):
    INDEX_CORE = "index_core"
    LEADER_SWING = "leader_swing"

    @property
    def label(self) -> str:
        return {
            StrategyLane.INDEX_CORE: "Index Core",
            StrategyLane.LEADER_SWING: "Leader Swing",
        }[self]


class ReviewState(StrEnum):
    READY = "ready"
    READY_VERIFY = "ready_verify"
    DEVELOPING = "developing"
    VERIFY_CONTRACT = "verify_contract"
    REJECTED = "rejected"

    @property
    def label(self) -> str:
        return {
            ReviewState.READY: "Ready",
            ReviewState.READY_VERIFY: "Ready - Verify",
            ReviewState.DEVELOPING: "Developing",
            ReviewState.VERIFY_CONTRACT: "Verify Contract",
            ReviewState.REJECTED: "Rejected",
        }[self]


class PatternStatus(StrEnum):
    FORMING = "forming"
    READY = "ready"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    STALE = "stale"


class EventRiskStatus(StrEnum):
    CLEAR = "clear"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class EvidenceMaturity(StrEnum):
    EXPLORATORY = "exploratory"
    PROVISIONAL = "provisional"
    VALIDATED = "validated"


class OutcomeState(StrEnum):
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"
    UNRESOLVED = "unresolved"


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
class AssetMetadata:
    symbol: str
    company: str
    sector: str
    peer_etf: str
    lane: StrategyLane


@dataclass(frozen=True)
class OptionContractSnapshot:
    contract_symbol: str
    underlying_symbol: str
    expiration_date: date
    strike: float
    dte: int
    delta: float
    gamma: float | None
    theta: float | None
    vega: float | None
    implied_volatility: float | None
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    open_interest: int
    volume: int
    feed: str
    quote_timestamp: datetime

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_percent(self) -> float:
        return ((self.ask - self.bid) / self.mid) * 100 if self.mid > 0 else float("inf")

    @property
    def maximum_loss_per_contract(self) -> float:
        return self.ask * 100


@dataclass(frozen=True)
class EventRisk:
    symbol: str
    status: EventRiskStatus
    earnings_date: date | None
    summary: str
    source: str
    checked_at: datetime


@dataclass(frozen=True)
class MarketContext:
    score: int
    regime: str
    spy_daily_pass: bool
    qqq_daily_pass: bool
    weekly_alignment: bool
    breadth_above_sma50: float
    breadth_above_ema21: float
    breadth_symbol_count: int
    components: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceScores:
    trend: int
    leadership: int | None
    setup: int
    momentum: int
    market: int
    contract: int
    risk: int


@dataclass(frozen=True)
class TrendAnalysis:
    score: int
    close: float
    ema21: float
    sma50: float
    sma200: float
    anchored_vwap: float
    atr: float
    atr_percent: float
    weekly_aligned: bool
    structure: str
    relative_volume: float
    breakout_level: float
    breakout_confirmed: bool
    pullback_support: float
    pullback_setup: bool
    resistance_level: float
    extended: bool
    hard_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class PatternSignal:
    pattern_type: str
    status: PatternStatus
    quality: int
    trigger: float
    invalidation: float
    target: float
    age_bars: int
    geometry_notes: tuple[str, ...] = ()


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
    resistance_level: float
    target_price: float
    target_basis: str
    target_gain_percent: float
    distance_to_trigger: float
    distance_to_support: float
    reward_to_risk: float | None
    status: str
    intended_hold_sessions: tuple[int, int]
    requalify_dte: int


@dataclass(frozen=True)
class ContractSelection:
    score: int
    primary: OptionContractSnapshot | None
    alternatives: tuple[OptionContractSnapshot, ...]
    feed: str
    realized_volatility: float | None
    iv_to_realized_volatility: float | None
    rejection_reasons: tuple[str, ...] = ()

    @property
    def trustworthy(self) -> bool:
        return self.feed.lower() == "opra"


@dataclass(frozen=True)
class Candidate:
    symbol: str
    company: str
    sector: str
    peer_etf: str
    lane: StrategyLane
    trend: TrendAnalysis
    leadership_score: int | None
    pattern: PatternSignal
    daily_momentum: MomentumResult
    four_hour_momentum: MomentumResult
    market: MarketContext
    event_risk: EventRisk
    contracts: ContractSelection
    entry_plan: EntryPlan
    scores: EvidenceScores
    state: ReviewState
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RejectedRecord:
    symbol: str
    stage: str
    reason_codes: tuple[str, ...]
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ScanResult:
    scan_type: ScanType
    generated_at: datetime
    market_data_timestamp: datetime
    market: MarketContext
    universe_count: int
    evaluated_count: int
    ready: tuple[Candidate, ...]
    ready_verify: tuple[Candidate, ...]
    developing: tuple[Candidate, ...]
    verify_contract: tuple[Candidate, ...]
    rejected: tuple[RejectedRecord, ...]
    fixture: bool = False

    @property
    def candidates(self) -> tuple[Candidate, ...]:
        return self.ready + self.ready_verify + self.developing + self.verify_contract


@dataclass(frozen=True)
class SignalObservation:
    signal_id: str
    observed_at: datetime
    horizon_sessions: int
    underlying_close: float
    forward_return: float
    maximum_favorable_excursion: float
    maximum_adverse_excursion: float
    outcome: OutcomeState
    triggered_at: datetime | None
    invalidated_at: datetime | None
    trigger_invalidation_order: str
    contract_bid_exit: float | None = None
