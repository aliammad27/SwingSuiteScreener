from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from scanner.config import ROOT, load_config
from scanner.models import (
    Candle,
    EvidenceMaturity,
    OutcomeState,
    ScanResult,
    SignalObservation,
)
from scanner.providers.base import MarketDataProvider
from scanner.strategy_profile import PROFILE

OBSERVATION_HORIZONS = (1, 2, 3, 4, 5)


def strategy_config_hash() -> str:
    payload = {
        "strategy": load_config("strategy"),
        "universe": load_config("universe"),
    }
    serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def evidence_maturity(observation_count: int) -> EvidenceMaturity:
    if observation_count >= 150:
        return EvidenceMaturity.VALIDATED
    if observation_count >= 50:
        return EvidenceMaturity.PROVISIONAL
    return EvidenceMaturity.EXPLORATORY


@dataclass(frozen=True)
class ResearchSummaryRow:
    lane: str
    pattern_type: str
    market_regime: str
    horizon_sessions: int
    observation_count: int
    maturity: EvidenceMaturity
    median_forward_return: float | None
    median_mfe: float | None
    median_mae: float | None
    confirmed_count: int
    invalidated_count: int
    unresolved_count: int


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


class ResearchLedger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or ROOT / "data" / "research" / "research.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> ResearchLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id TEXT PRIMARY KEY,
                generated_at TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                profile_version INTEGER NOT NULL,
                config_hash TEXT NOT NULL,
                market_regime TEXT NOT NULL,
                market_score INTEGER NOT NULL,
                fixture INTEGER NOT NULL,
                validation_state TEXT NOT NULL DEFAULT 'research_default'
            );
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                scan_run_id TEXT NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
                signal_timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                lane TEXT NOT NULL,
                review_state TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_status TEXT NOT NULL,
                market_regime TEXT NOT NULL,
                trigger REAL NOT NULL,
                invalidation REAL NOT NULL,
                target REAL NOT NULL,
                underlying_close REAL NOT NULL,
                config_hash TEXT NOT NULL,
                timing_timestamp TEXT,
                tactical_warning REAL,
                tactical_failure REAL,
                structural_invalidation REAL,
                confirmed_pivot REAL,
                planning_objective_2r REAL,
                stock_feed TEXT,
                option_feed TEXT,
                event_source TEXT,
                event_source_timestamp TEXT,
                event_checked_at TEXT,
                quote_age_minutes REAL,
                UNIQUE(signal_timestamp, symbol, pattern_type, config_hash)
            );
            CREATE TABLE IF NOT EXISTS contract_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
                captured_at TEXT NOT NULL,
                contract_symbol TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                strike REAL NOT NULL,
                dte INTEGER NOT NULL,
                delta REAL NOT NULL,
                gamma REAL,
                theta REAL,
                vega REAL,
                implied_volatility REAL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                open_interest INTEGER NOT NULL,
                volume INTEGER NOT NULL,
                feed TEXT NOT NULL,
                bid_size INTEGER,
                ask_size INTEGER,
                spread_percent REAL,
                theta_ask_percent REAL,
                extrinsic_value_percent REAL,
                quote_age_minutes REAL,
                quote_change_percent REAL,
                expiration_style TEXT,
                requoted_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(signal_id, contract_symbol)
            );
            CREATE TABLE IF NOT EXISTS observations (
                signal_id TEXT NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
                horizon_sessions INTEGER NOT NULL,
                observed_at TEXT NOT NULL,
                underlying_close REAL NOT NULL,
                forward_return REAL NOT NULL,
                maximum_favorable_excursion REAL NOT NULL,
                maximum_adverse_excursion REAL NOT NULL,
                outcome TEXT NOT NULL,
                triggered_at TEXT,
                invalidated_at TEXT,
                trigger_invalidation_order TEXT NOT NULL DEFAULT 'neither',
                contract_bid_exit REAL,
                PRIMARY KEY(signal_id, horizon_sessions)
            );
            CREATE INDEX IF NOT EXISTS idx_signals_symbol_time
                ON signals(symbol, signal_timestamp);
            CREATE INDEX IF NOT EXISTS idx_observations_horizon
                ON observations(horizon_sessions);
            """
        )
        self._ensure_columns(
            "scan_runs",
            (("validation_state", "TEXT NOT NULL DEFAULT 'research_default'"),),
        )
        self._ensure_columns(
            "signals",
            (
                ("timing_timestamp", "TEXT"),
                ("tactical_warning", "REAL"),
                ("tactical_failure", "REAL"),
                ("structural_invalidation", "REAL"),
                ("confirmed_pivot", "REAL"),
                ("planning_objective_2r", "REAL"),
                ("stock_feed", "TEXT"),
                ("option_feed", "TEXT"),
                ("event_source", "TEXT"),
                ("event_source_timestamp", "TEXT"),
                ("event_checked_at", "TEXT"),
                ("quote_age_minutes", "REAL"),
            ),
        )
        self._ensure_columns(
            "contract_snapshots",
            (
                ("bid_size", "INTEGER"),
                ("ask_size", "INTEGER"),
                ("spread_percent", "REAL"),
                ("theta_ask_percent", "REAL"),
                ("extrinsic_value_percent", "REAL"),
                ("quote_age_minutes", "REAL"),
                ("quote_change_percent", "REAL"),
                ("expiration_style", "TEXT"),
                ("requoted_count", "INTEGER NOT NULL DEFAULT 0"),
            ),
        )
        self._ensure_columns(
            "observations",
            (
                ("triggered_at", "TEXT"),
                ("invalidated_at", "TEXT"),
                ("trigger_invalidation_order", "TEXT NOT NULL DEFAULT 'neither'"),
            ),
        )
        self.connection.commit()

    def _ensure_columns(
        self,
        table: str,
        columns: tuple[tuple[str, str], ...],
    ) -> None:
        existing = {
            str(row[1])
            for row in self.connection.execute(f"PRAGMA table_info({table})")
        }
        for column, definition in columns:
            if column not in existing:
                self.connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )

    def record_scan(self, result: ScanResult) -> str:
        config_hash = strategy_config_hash()
        run_id = hashlib.sha256(
            f"{result.scan_type.value}|{result.generated_at.isoformat()}|{config_hash}".encode()
        ).hexdigest()
        self.connection.execute(
            """
            INSERT OR IGNORE INTO scan_runs
            (id, generated_at, scan_type, profile_version, config_hash, market_regime,
             market_score, fixture, validation_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                result.generated_at.isoformat(),
                result.scan_type.value,
                PROFILE.schema_version,
                config_hash,
                result.market.regime,
                result.market.score,
                int(result.fixture),
                result.validation_state,
            ),
        )
        for candidate in result.candidates:
            signal_id = hashlib.sha256(
                f"{result.market_data_timestamp.isoformat()}|{candidate.symbol}|{candidate.pattern.pattern_type}|{config_hash}".encode()
            ).hexdigest()
            self.connection.execute(
                """
                INSERT OR IGNORE INTO signals
                (id, scan_run_id, signal_timestamp, symbol, lane, review_state, pattern_type,
                 pattern_status, market_regime, trigger, invalidation, target, underlying_close,
                 config_hash, timing_timestamp, tactical_warning, tactical_failure,
                 structural_invalidation, confirmed_pivot, planning_objective_2r, stock_feed,
                 option_feed, event_source, event_source_timestamp, event_checked_at,
                 quote_age_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    run_id,
                    result.market_data_timestamp.isoformat(),
                    candidate.symbol,
                    candidate.lane.value,
                    candidate.state.value,
                    candidate.pattern.pattern_type,
                    candidate.pattern.status.value,
                    candidate.market.regime,
                    candidate.entry_plan.trigger,
                    candidate.entry_plan.invalidation,
                    candidate.entry_plan.target_price,
                    candidate.trend.close,
                    config_hash,
                    candidate.timing.completed_at.isoformat(),
                    candidate.entry_plan.tactical_warning,
                    candidate.entry_plan.tactical_failure,
                    candidate.entry_plan.invalidation,
                    candidate.entry_plan.resistance_level,
                    candidate.entry_plan.planning_objective_2r,
                    candidate.data_trust.stock_feed,
                    candidate.data_trust.option_feed,
                    candidate.data_trust.event_source,
                    (
                        candidate.event_risk.source_timestamp.isoformat()
                        if candidate.event_risk.source_timestamp
                        else None
                    ),
                    candidate.event_risk.checked_at.isoformat(),
                    candidate.data_trust.quote_age_minutes,
                ),
            )
            contracts_with_risk = []
            if candidate.contracts.primary:
                contracts_with_risk.append(
                    (
                        candidate.contracts.primary,
                        candidate.contracts.primary_risk,
                    )
                )
            contracts_with_risk.extend(
                (
                    contract,
                    (
                        candidate.contracts.alternative_risks[index]
                        if index < len(candidate.contracts.alternative_risks)
                        else None
                    ),
                )
                for index, contract in enumerate(candidate.contracts.alternatives)
            )
            for contract, risk in contracts_with_risk:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO contract_snapshots
                    (signal_id, captured_at, contract_symbol, expiration_date, strike, dte, delta,
                     gamma, theta, vega, implied_volatility, bid, ask, open_interest, volume, feed,
                     bid_size, ask_size, spread_percent, theta_ask_percent,
                     extrinsic_value_percent, quote_age_minutes, quote_change_percent,
                     expiration_style, requoted_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal_id,
                        contract.quote_timestamp.isoformat(),
                        contract.contract_symbol,
                        contract.expiration_date.isoformat(),
                        contract.strike,
                        contract.dte,
                        contract.delta,
                        contract.gamma,
                        contract.theta,
                        contract.vega,
                        contract.implied_volatility,
                        contract.bid,
                        contract.ask,
                        contract.open_interest,
                        contract.volume,
                        contract.feed,
                        contract.bid_size,
                        contract.ask_size,
                        contract.spread_percent,
                        risk.theta_ask_percent if risk else None,
                        risk.extrinsic_value_percent if risk else None,
                        risk.quote_age_minutes if risk else None,
                        risk.quote_change_percent if risk else None,
                        risk.expiration_style if risk else None,
                        candidate.contracts.requoted_count,
                    ),
                )
        self.connection.commit()
        return run_id

    def _pending_signals(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT signals.*
                FROM signals
                WHERE EXISTS (
                    SELECT 1 FROM (SELECT 1) marker
                    WHERE (SELECT COUNT(*) FROM observations WHERE signal_id = signals.id) < ?
                )
                ORDER BY signal_timestamp
                """,
                (len(OBSERVATION_HORIZONS),),
            )
        )

    def evaluate_pending(self, market: MarketDataProvider) -> int:
        inserted = 0
        for row in self._pending_signals():
            candles = market.daily(str(row["symbol"]))
            timestamp = datetime.fromisoformat(str(row["signal_timestamp"]))
            signal_index = max(
                (index for index, candle in enumerate(candles) if candle.timestamp <= timestamp),
                default=-1,
            )
            if signal_index < 0:
                continue
            for horizon in OBSERVATION_HORIZONS:
                if signal_index + horizon >= len(candles):
                    continue
                exists = self.connection.execute(
                    "SELECT 1 FROM observations WHERE signal_id = ? AND horizon_sessions = ?",
                    (row["id"], horizon),
                ).fetchone()
                if exists:
                    continue
                observation = _observe_signal(row, candles, signal_index, horizon)
                self.connection.execute(
                    """
                    INSERT INTO observations
                    (signal_id, horizon_sessions, observed_at, underlying_close, forward_return,
                     maximum_favorable_excursion, maximum_adverse_excursion, outcome,
                     triggered_at, invalidated_at, trigger_invalidation_order, contract_bid_exit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        observation.signal_id,
                        observation.horizon_sessions,
                        observation.observed_at.isoformat(),
                        observation.underlying_close,
                        observation.forward_return,
                        observation.maximum_favorable_excursion,
                        observation.maximum_adverse_excursion,
                        observation.outcome.value,
                        observation.triggered_at.isoformat()
                        if observation.triggered_at
                        else None,
                        observation.invalidated_at.isoformat()
                        if observation.invalidated_at
                        else None,
                        observation.trigger_invalidation_order,
                        observation.contract_bid_exit,
                    ),
                )
                inserted += 1
        self.connection.commit()
        return inserted

    def summary(self, horizon_sessions: int = 5) -> tuple[ResearchSummaryRow, ...]:
        rows = self.connection.execute(
            """
            SELECT s.lane, s.pattern_type, s.market_regime, o.forward_return,
                   o.maximum_favorable_excursion, o.maximum_adverse_excursion, o.outcome
            FROM observations o
            JOIN signals s ON s.id = o.signal_id
            WHERE o.horizon_sessions = ?
            ORDER BY s.lane, s.pattern_type, s.market_regime
            """,
            (horizon_sessions,),
        )
        grouped: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault(
                (str(row["lane"]), str(row["pattern_type"]), str(row["market_regime"])),
                [],
            ).append(row)
        output: list[ResearchSummaryRow] = []
        for (lane, pattern, regime), values in grouped.items():
            count = len(values)
            outcomes = [str(value["outcome"]) for value in values]
            output.append(
                ResearchSummaryRow(
                    lane=lane,
                    pattern_type=pattern,
                    market_regime=regime,
                    horizon_sessions=horizon_sessions,
                    observation_count=count,
                    maturity=evidence_maturity(count),
                    median_forward_return=_median(
                        [float(value["forward_return"]) for value in values]
                    ),
                    median_mfe=_median(
                        [float(value["maximum_favorable_excursion"]) for value in values]
                    ),
                    median_mae=_median(
                        [float(value["maximum_adverse_excursion"]) for value in values]
                    ),
                    confirmed_count=outcomes.count(OutcomeState.CONFIRMED.value),
                    invalidated_count=outcomes.count(OutcomeState.INVALIDATED.value),
                    unresolved_count=outcomes.count(OutcomeState.UNRESOLVED.value),
                )
            )
        return tuple(output)

    def write_summary(self, output_dir: Path | None = None) -> tuple[Path, Path]:
        folder = output_dir or ROOT / "reports" / "research"
        folder.mkdir(parents=True, exist_ok=True)
        markdown_path = folder / "latest.md"
        json_path = folder / "latest.json"
        rows = self.summary()
        lines = [
            f"# {PROFILE.name} Research Evidence",
            "",
            "Outcomes are descriptive evidence, not a profit claim or automatic threshold update.",
            "",
            "| Lane | Pattern | Regime | N | Maturity | Median 5D | MFE | MAE | Confirmed | Invalidated | Unresolved |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            lines.append(
                f"| {row.lane} | {row.pattern_type} | {row.market_regime} | {row.observation_count} | "
                f"{row.maturity.value} | {row.median_forward_return or 0:.2f}% | "
                f"{row.median_mfe or 0:.2f}% | {row.median_mae or 0:.2f}% | "
                f"{row.confirmed_count} | {row.invalidated_count} | {row.unresolved_count} |"
            )
        if not rows:
            lines.append("| No completed observations | - | - | 0 | exploratory | 0 | 0 | 0 | 0 | 0 | 0 |")
        markdown_path.write_text("\n".join(lines), encoding="utf-8")
        json_path.write_text(
            json.dumps([asdict(row) for row in rows], indent=2, default=str), encoding="utf-8"
        )
        return markdown_path, json_path


def _observe_signal(
    row: sqlite3.Row,
    candles: list[Candle],
    signal_index: int,
    horizon: int,
) -> SignalObservation:
    source = float(row["underlying_close"])
    future = candles[signal_index + 1 : signal_index + horizon + 1]
    endpoint = future[-1]
    trigger = float(row["trigger"])
    invalidation = float(row["invalidation"])
    trigger_index = (
        -1
        if str(row["pattern_status"]) == "confirmed"
        else next(
            (index for index, candle in enumerate(future) if candle.high >= trigger),
            None,
        )
    )
    invalidation_index = next(
        (index for index, candle in enumerate(future) if candle.low <= invalidation), None
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
    return SignalObservation(
        signal_id=str(row["id"]),
        observed_at=endpoint.timestamp,
        horizon_sessions=horizon,
        underlying_close=endpoint.close,
        forward_return=((endpoint.close / source) - 1) * 100,
        maximum_favorable_excursion=((max(candle.high for candle in future) / source) - 1)
        * 100,
        maximum_adverse_excursion=((min(candle.low for candle in future) / source) - 1)
        * 100,
        outcome=outcome,
        triggered_at=(
            datetime.fromisoformat(str(row["signal_timestamp"]))
            if trigger_index == -1
            else future[trigger_index].timestamp
            if trigger_index is not None
            else None
        ),
        invalidated_at=(
            future[invalidation_index].timestamp
            if invalidation_index is not None
            else None
        ),
        trigger_invalidation_order=order,
        contract_bid_exit=None,
    )


def create_replay_signal_id() -> str:
    return uuid4().hex
