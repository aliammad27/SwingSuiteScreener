from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from scanner.models import Candle, EvidenceMaturity, OutcomeState, ScanType
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.research import ResearchLedger, _observe_signal, evidence_maturity
from scanner.run_scan import run_scan


class FutureFixtureProvider(FixtureDataProvider):
    def __init__(self, trigger: float, invalidation: float, source: float) -> None:
        super().__init__(scenario="ready")
        self.trigger = trigger
        self.invalidation = invalidation
        self.source = source

    def daily(self, symbol: str) -> list[Candle]:
        candles = super().daily(symbol)
        if symbol != "SSTR":
            return candles
        first_timestamp = candles[-1].timestamp + timedelta(days=1)
        candles.append(
            replace(
                candles[-1],
                timestamp=first_timestamp,
                open=self.source - 0.05,
                high=self.source + 0.10,
                low=max(self.invalidation + 0.05, self.source - 0.10),
                close=self.source,
            )
        )
        for offset in range(1, 17):
            close = self.trigger + 0.20 + offset * 0.05
            candles.append(
                replace(
                    candles[-1],
                    timestamp=first_timestamp + timedelta(days=offset),
                    open=close - 0.10,
                    high=close + 0.30,
                    low=max(self.invalidation + 0.05, close - 0.30),
                    close=close,
                )
            )
        return candles


def test_evidence_maturity_thresholds() -> None:
    assert evidence_maturity(0) == EvidenceMaturity.EXPLORATORY
    assert evidence_maturity(49) == EvidenceMaturity.EXPLORATORY
    assert evidence_maturity(50) == EvidenceMaturity.PROVISIONAL
    assert evidence_maturity(149) == EvidenceMaturity.PROVISIONAL
    assert evidence_maturity(150) == EvidenceMaturity.VALIDATED


def test_ledger_is_idempotent_and_records_all_observation_horizons(tmp_path) -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    candidate = result.candidates[0]
    with ResearchLedger(tmp_path / "research.sqlite3") as ledger:
        first_run_id = ledger.record_scan(result)
        second_run_id = ledger.record_scan(result)
        assert first_run_id == second_run_id
        assert ledger.connection.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0] == 1
        assert ledger.connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 1
        assert (
            ledger.connection.execute("SELECT COUNT(*) FROM contract_snapshots").fetchone()[0]
            == 3
        )

        provider = FutureFixtureProvider(
            candidate.entry_plan.trigger,
            candidate.entry_plan.invalidation,
            candidate.trend.close,
        )
        assert ledger.evaluate_pending(provider) == 5
        assert ledger.evaluate_pending(provider) == 0
        horizons = {
            row[0]
            for row in ledger.connection.execute(
                "SELECT horizon_sessions FROM observations"
            )
        }
        assert horizons == {1, 2, 3, 4, 5}
        orders = {
            row[0]
            for row in ledger.connection.execute(
                "SELECT DISTINCT trigger_invalidation_order FROM observations"
            )
        }
        assert "trigger_first" in orders
        assert "invalidation_first" not in orders
        assert "same_bar_ambiguous" not in orders
        summary = ledger.summary(horizon_sessions=5)
        assert len(summary) == 1
        assert summary[0].maturity == EvidenceMaturity.EXPLORATORY
        assert summary[0].confirmed_count == 1


def test_same_bar_trigger_and_invalidation_is_not_assumed_profitable(tmp_path) -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    candidate = result.candidates[0]
    with ResearchLedger(tmp_path / "research.sqlite3") as ledger:
        ledger.record_scan(result)
        row = ledger.connection.execute("SELECT * FROM signals").fetchone()
        assert row is not None
        source = Candle(
            symbol="SSTR",
            timeframe="1D",
            timestamp=FIXTURE_TIMESTAMP,
            open=candidate.trend.close,
            high=candidate.trend.close,
            low=candidate.trend.close,
            close=candidate.trend.close,
            volume=1_000,
        )
        ambiguous = replace(
            source,
            timestamp=FIXTURE_TIMESTAMP + timedelta(days=1),
            high=candidate.entry_plan.trigger + 0.10,
            low=candidate.entry_plan.invalidation - 0.10,
        )
        observation = _observe_signal(row, [source, ambiguous], 0, 1)
        assert observation.outcome == OutcomeState.INVALIDATED
        assert observation.trigger_invalidation_order == "same_bar_ambiguous"
        assert observation.triggered_at == ambiguous.timestamp
        assert observation.invalidated_at == ambiguous.timestamp


def test_ledger_migrates_previous_schema_without_dropping_history(tmp_path) -> None:
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE scan_runs (
            id TEXT PRIMARY KEY,
            generated_at TEXT NOT NULL,
            scan_type TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            config_hash TEXT NOT NULL,
            market_regime TEXT NOT NULL,
            market_score INTEGER NOT NULL,
            fixture INTEGER NOT NULL
        );
        CREATE TABLE signals (
            id TEXT PRIMARY KEY,
            scan_run_id TEXT NOT NULL,
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
            config_hash TEXT NOT NULL
        );
        CREATE TABLE contract_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
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
            feed TEXT NOT NULL
        );
        CREATE TABLE observations (
            signal_id TEXT NOT NULL,
            horizon_sessions INTEGER NOT NULL,
            observed_at TEXT NOT NULL,
            underlying_close REAL NOT NULL,
            forward_return REAL NOT NULL,
            maximum_favorable_excursion REAL NOT NULL,
            maximum_adverse_excursion REAL NOT NULL,
            outcome TEXT NOT NULL,
            contract_bid_exit REAL,
            PRIMARY KEY(signal_id, horizon_sessions)
        );
        INSERT INTO scan_runs VALUES (
            'legacy', '2025-01-01T00:00:00+00:00', 'post_close', 4,
            'hash', 'Supportive', 80, 1
        );
        """
    )
    connection.commit()
    connection.close()

    with ResearchLedger(path) as ledger:
        assert (
            ledger.connection.execute(
                "SELECT validation_state FROM scan_runs WHERE id = 'legacy'"
            ).fetchone()[0]
            == "research_default"
        )
        signal_columns = {
            row[1]
            for row in ledger.connection.execute("PRAGMA table_info(signals)")
        }
        contract_columns = {
            row[1]
            for row in ledger.connection.execute(
                "PRAGMA table_info(contract_snapshots)"
            )
        }
        assert {
            "timing_timestamp",
            "tactical_warning",
            "structural_invalidation",
            "planning_objective_2r",
            "event_source_timestamp",
        }.issubset(signal_columns)
        assert {
            "bid_size",
            "theta_ask_percent",
            "quote_age_minutes",
            "expiration_style",
            "requoted_count",
        }.issubset(contract_columns)
