from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from scanner.config import ROOT
from scanner.evidence import analyze_trend
from scanner.market_context import calculate_market_context
from scanner.models import Candle, OutcomeState, PatternStatus
from scanner.patterns import detect_best_pattern
from scanner.providers.base import MarketDataProvider
from scanner.strategy_profile import PROFILE
from scanner.universe import metadata_for


class _CutoffMarketProvider(MarketDataProvider):
    def __init__(self, delegate: MarketDataProvider, cutoff: datetime) -> None:
        self.delegate = delegate
        self.cutoff = cutoff
        self.stock_feed = getattr(delegate, "stock_feed", "unknown")

    def _through(self, candles: list[Candle]) -> list[Candle]:
        return [candle for candle in candles if candle.timestamp <= self.cutoff]

    def daily(self, symbol: str) -> list[Candle]:
        return self._through(self.delegate.daily(symbol))

    def one_hour(self, symbol: str) -> list[Candle]:
        return self._through(self.delegate.one_hour(symbol))

    def weekly(self, symbol: str) -> list[Candle]:
        return self._through(self.delegate.weekly(symbol))


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
    for index in eligible_indices:
        cutoff = full_daily[index].timestamp
        cutoff_market = _CutoffMarketProvider(market, cutoff)
        try:
            context = calculate_market_context(
                cutoff_market, context_symbols, PROFILE
            )
            daily = cutoff_market.daily(symbol)
            weekly = cutoff_market.weekly(symbol)
            trend = analyze_trend(daily, weekly, PROFILE)
            pattern = detect_best_pattern(daily, trend, PROFILE)
        except (ValueError, RuntimeError):
            continue
        if pattern.status not in {PatternStatus.READY, PatternStatus.CONFIRMED}:
            continue
        if trend.score < PROFILE.thresholds.trend:
            continue
        if pattern.quality < PROFILE.thresholds.setup:
            continue
        if context.regime == "Hostile" or trend.hard_failures:
            continue
        previous_index = last_pattern_bar.get(pattern.pattern_type)
        if previous_index is not None and index - previous_index <= 5:
            continue
        last_pattern_bar[pattern.pattern_type] = index
        future = full_daily[index + 1 : index + horizon_sessions + 1]
        source = full_daily[index].close
        trigger_index = (
            -1
            if pattern.status == PatternStatus.CONFIRMED
            else next(
                (
                    future_index
                    for future_index, candle in enumerate(future)
                    if candle.high >= pattern.trigger
                ),
                None,
            )
        )
        invalidation_index = next(
            (
                future_index
                for future_index, candle in enumerate(future)
                if candle.low <= pattern.invalidation
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
        risk = max(source - pattern.invalidation, 0.01)
        pivot = (
            trend.resistance_level
            if trend.resistance_level is not None
            and trend.resistance_level > source
            else None
        )
        target = (
            pivot
            if pivot is not None and (pivot - source) / risk >= 1.5
            else source + 2 * risk
        )
        hits.append(
            ReplayHit(
                symbol=symbol,
                signal_timestamp=cutoff,
                lane=metadata_for(symbol).lane.value,
                pattern_type=pattern.pattern_type,
                pattern_status=pattern.status.value,
                market_regime=context.regime,
                trend_score=trend.score,
                setup_score=pattern.quality,
                trigger=pattern.trigger,
                invalidation=pattern.invalidation,
                target=target,
                horizon_sessions=horizon_sessions,
                forward_return=((future[-1].close / source) - 1) * 100,
                maximum_favorable_excursion=(
                    (max(candle.high for candle in future) / source) - 1
                )
                * 100,
                maximum_adverse_excursion=(
                    (min(candle.low for candle in future) / source) - 1
                )
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
        "Signals use only daily prefixes. This is context research, not option performance and not the v5 promotion study.",
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
        json.dumps([asdict(hit) for hit in hits], indent=2, default=str),
        encoding="utf-8",
    )
    return markdown_path, json_path
