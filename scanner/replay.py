from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from scanner.config import ROOT
from scanner.market_context import calculate_market_context
from scanner.models import (
    Candle,
    EventRisk,
    EventRiskStatus,
    OptionContractSnapshot,
    OutcomeState,
    PatternStatus,
)
from scanner.providers.base import EventRiskProvider, MarketDataProvider, OptionDataProvider
from scanner.run_scan import _scan_symbol
from scanner.strategy_profile import PROFILE


class _CutoffMarketProvider(MarketDataProvider):
    def __init__(self, delegate: MarketDataProvider, cutoff: datetime) -> None:
        self.delegate = delegate
        self.cutoff = cutoff

    def _through(self, candles: list[Candle]) -> list[Candle]:
        return [candle for candle in candles if candle.timestamp <= self.cutoff]

    def daily(self, symbol: str) -> list[Candle]:
        return self._through(self.delegate.daily(symbol))

    def four_hour(self, symbol: str) -> list[Candle]:
        return self._through(self.delegate.four_hour(symbol))

    def weekly(self, symbol: str) -> list[Candle]:
        return self._through(self.delegate.weekly(symbol))


class _NoOptionProvider(OptionDataProvider):
    option_feed = "unknown"

    def call_chain(
        self,
        symbol: str,
        expiration_date_gte: date,
        expiration_date_lte: date,
    ) -> list[OptionContractSnapshot]:
        return []


class _UnknownEventProvider(EventRiskProvider):
    def event_risk(self, symbol: str) -> EventRisk:
        return EventRisk(
            symbol=symbol,
            status=EventRiskStatus.UNKNOWN,
            earnings_date=None,
            summary="Historical event calendar was not supplied for replay.",
            source="replay",
            checked_at=datetime.now(UTC),
        )


@dataclass(frozen=True)
class ReplayHit:
    symbol: str
    signal_timestamp: datetime
    lane: str
    pattern_type: str
    pattern_status: str
    market_regime: str
    trend_score: int
    setup_score: int
    trigger: float
    invalidation: float
    target: float
    horizon_sessions: int
    forward_return: float
    maximum_favorable_excursion: float
    maximum_adverse_excursion: float
    outcome: OutcomeState
    trigger_invalidation_order: str
    source_bar_count: int


def sequential_replay(
    market: MarketDataProvider,
    symbol: str,
    context_symbols: list[str],
    *,
    start: date | None = None,
    end: date | None = None,
    horizon_sessions: int = 15,
    maximum_signal_dates: int = 120,
) -> tuple[ReplayHit, ...]:
    full_daily = market.daily(symbol)
    eligible_indices = [
        index
        for index in range(219, len(full_daily) - horizon_sessions)
        if (start is None or full_daily[index].timestamp.date() >= start)
        and (end is None or full_daily[index].timestamp.date() <= end)
    ][-maximum_signal_dates:]
    hits: list[ReplayHit] = []
    last_pattern_bar: dict[str, int] = {}
    no_options = _NoOptionProvider()
    unknown_events = _UnknownEventProvider()
    for index in eligible_indices:
        cutoff = full_daily[index].timestamp
        cutoff_market = _CutoffMarketProvider(market, cutoff)
        try:
            context = calculate_market_context(cutoff_market, context_symbols, PROFILE)
            candidate = _scan_symbol(
                symbol,
                cutoff_market,
                no_options,
                unknown_events,
                context,
                cutoff,
            )
        except (ValueError, RuntimeError):
            continue
        if candidate.pattern.status not in {PatternStatus.READY, PatternStatus.CONFIRMED}:
            continue
        if candidate.scores.trend < PROFILE.thresholds.trend:
            continue
        if candidate.scores.setup < PROFILE.thresholds.setup:
            continue
        previous_index = last_pattern_bar.get(candidate.pattern.pattern_type)
        if previous_index is not None and index - previous_index <= 5:
            continue
        last_pattern_bar[candidate.pattern.pattern_type] = index
        future = full_daily[index + 1 : index + horizon_sessions + 1]
        source = full_daily[index].close
        trigger_index = (
            -1
            if candidate.pattern.status == PatternStatus.CONFIRMED
            else next(
                (
                    future_index
                    for future_index, candle in enumerate(future)
                    if candle.high >= candidate.entry_plan.trigger
                ),
                None,
            )
        )
        invalidation_index = next(
            (
                future_index
                for future_index, candle in enumerate(future)
                if candle.low <= candidate.entry_plan.invalidation
            ),
            None,
        )
        if trigger_index is not None and (
            invalidation_index is None or trigger_index < invalidation_index
        ):
            outcome = OutcomeState.CONFIRMED
            order = "trigger_first"
        elif invalidation_index is not None and (
            trigger_index is None or invalidation_index < trigger_index
        ):
            outcome = OutcomeState.INVALIDATED
            order = "invalidation_first"
        elif trigger_index is not None and trigger_index == invalidation_index:
            outcome = OutcomeState.INVALIDATED
            order = "same_bar_ambiguous"
        else:
            outcome = OutcomeState.UNRESOLVED
            order = "neither"
        hits.append(
            ReplayHit(
                symbol=symbol,
                signal_timestamp=cutoff,
                lane=candidate.lane.value,
                pattern_type=candidate.pattern.pattern_type,
                pattern_status=candidate.pattern.status.value,
                market_regime=context.regime,
                trend_score=candidate.scores.trend,
                setup_score=candidate.scores.setup,
                trigger=candidate.entry_plan.trigger,
                invalidation=candidate.entry_plan.invalidation,
                target=candidate.entry_plan.target_price,
                horizon_sessions=horizon_sessions,
                forward_return=((future[-1].close / source) - 1) * 100,
                maximum_favorable_excursion=((max(candle.high for candle in future) / source) - 1)
                * 100,
                maximum_adverse_excursion=((min(candle.low for candle in future) / source) - 1)
                * 100,
                outcome=outcome,
                trigger_invalidation_order=order,
                source_bar_count=index + 1,
            )
        )
    return tuple(hits)


def write_replay_report(
    hits: tuple[ReplayHit, ...], output_dir: Path | None = None
) -> tuple[Path, Path]:
    folder = output_dir or ROOT / "reports" / "research" / "replay"
    folder.mkdir(parents=True, exist_ok=True)
    markdown_path = folder / "latest.md"
    json_path = folder / "latest.json"
    lines = [
        "# Sequential Underlying Replay",
        "",
        "Each signal was generated from a prefix ending at its signal timestamp. Future bars were used only after signal creation for observation.",
        "Contract returns are intentionally absent.",
        "",
        "| Date | Symbol | Pattern | Regime | Outcome | Forward | MFE | MAE |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    for hit in hits:
        lines.append(
            f"| {hit.signal_timestamp.date().isoformat()} | {hit.symbol} | {hit.pattern_type} | "
            f"{hit.market_regime} | {hit.outcome.value} | {hit.forward_return:.2f}% | "
            f"{hit.maximum_favorable_excursion:.2f}% | {hit.maximum_adverse_excursion:.2f}% |"
        )
    if not hits:
        lines.append("| No qualifying signals | - | - | - | unresolved | 0 | 0 | 0 |")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps([asdict(hit) for hit in hits], indent=2, default=str), encoding="utf-8"
    )
    return markdown_path, json_path
