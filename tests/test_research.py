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
    assert evidence_maturity(29) == EvidenceMaturity.EXPLORATORY
    assert evidence_maturity(30) == EvidenceMaturity.PROVISIONAL
    assert evidence_maturity(99) == EvidenceMaturity.PROVISIONAL
    assert evidence_maturity(100) == EvidenceMaturity.VALIDATED


def test_ledger_is_idempotent_and_records_all_observation_horizons(tmp_path) -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready")
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
        assert horizons == {1, 3, 5, 10, 15}
        assert {
            row[0]
            for row in ledger.connection.execute(
                "SELECT DISTINCT trigger_invalidation_order FROM observations"
            )
        } == {"trigger_first"}
        summary = ledger.summary(horizon_sessions=10)
        assert len(summary) == 1
        assert summary[0].maturity == EvidenceMaturity.EXPLORATORY
        assert summary[0].confirmed_count == 1


def test_same_bar_trigger_and_invalidation_is_not_assumed_profitable(tmp_path) -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready")
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
