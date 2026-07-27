from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from datetime import timedelta

from scanner.models import EventRisk, EventRiskStatus, ScanType, StrategyLane
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider

scan_module = importlib.import_module("scanner.run_scan")


class CountingFixtureProvider(FixtureDataProvider):
    def __init__(self, scenario: str) -> None:
        super().__init__(scenario)
        self.event_calls = 0
        self.chain_calls = 0
        self.refresh_calls = 0
        self.refresh_sizes: list[int] = []

    def event_risk(self, symbol, as_of, lane):
        self.event_calls += 1
        return super().event_risk(symbol, as_of, lane)

    def call_chain(self, symbol, expiration_date_gte, expiration_date_lte, as_of):
        self.chain_calls += 1
        return super().call_chain(
            symbol,
            expiration_date_gte,
            expiration_date_lte,
            as_of,
        )

    def latest_quotes(self, contracts, as_of):
        self.refresh_calls += 1
        self.refresh_sizes.append(len(contracts))
        return super().latest_quotes(contracts, as_of)


class BlockedEventProvider(CountingFixtureProvider):
    def event_risk(
        self,
        symbol: str,
        as_of,
        lane: StrategyLane,
    ) -> EventRisk:
        self.event_calls += 1
        return EventRisk(
            symbol=symbol,
            status=EventRiskStatus.BLOCKED,
            earnings_date=as_of.date() + timedelta(days=2),
            summary="Test event is inside the protected window.",
            source="test",
            checked_at=as_of,
            source_timestamp=as_of,
        )


class StaleEventProvider(CountingFixtureProvider):
    def event_risk(
        self,
        symbol: str,
        as_of,
        lane: StrategyLane,
    ) -> EventRisk:
        self.event_calls += 1
        return EventRisk(
            symbol=symbol,
            status=EventRiskStatus.CLEAR,
            earnings_date=None,
            summary="Test event source is stale.",
            source="test",
            checked_at=as_of,
            source_timestamp=as_of - timedelta(hours=25),
        )


class UnavailableEventProvider(CountingFixtureProvider):
    def event_risk(self, symbol, as_of, lane):
        self.event_calls += 1
        raise RuntimeError("event service unavailable")


class UnavailableChainProvider(CountingFixtureProvider):
    def call_chain(self, symbol, expiration_date_gte, expiration_date_lte, as_of):
        self.chain_calls += 1
        raise RuntimeError("option chain unavailable")


class UnavailableRequoteProvider(CountingFixtureProvider):
    def latest_quotes(self, contracts, as_of):
        self.refresh_calls += 1
        raise RuntimeError("option quote service unavailable")


def _install(monkeypatch, provider: FixtureDataProvider) -> None:
    monkeypatch.setattr(
        scan_module,
        "_providers",
        lambda fixture, scenario: (provider, provider, provider),
    )


def test_asymmetric_research_finalist_fetches_events_and_options(monkeypatch) -> None:
    provider = CountingFixtureProvider("developing")
    _install(monkeypatch, provider)
    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="developing",
    )
    assert len(result.developing) == 1
    assert provider.event_calls == 1
    assert provider.chain_calls == 1
    assert provider.refresh_calls == 1
    assert result.developing[0].opportunity_tier.value == "asymmetric"


def test_hostile_market_keeps_strong_setup_on_watchlist(monkeypatch) -> None:
    provider = CountingFixtureProvider("ready")
    _install(monkeypatch, provider)
    baseline = scan_module.calculate_market_context(
        provider,
        ["SSTR", "APLUS", "BTIER", "ZERO"],
        scan_module.PROFILE,
    )
    monkeypatch.setattr(
        scan_module,
        "calculate_market_context",
        lambda *args, **kwargs: replace(baseline, score=40, regime="Hostile"),
    )

    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    )

    assert [candidate.symbol for candidate in result.developing] == ["SSTR"]
    assert "hostile_market_regime" in result.developing[0].reasons
    assert provider.event_calls == 0
    assert provider.chain_calls == 0


def test_technical_finalist_fetches_chain_then_requotes_top_three(monkeypatch) -> None:
    provider = CountingFixtureProvider("ready")
    _install(monkeypatch, provider)
    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    )
    assert len(result.ready_verify) == 1
    assert provider.event_calls == 1
    assert provider.chain_calls == 1
    assert provider.refresh_calls == 1
    assert provider.refresh_sizes == [3]
    assert result.ready_verify[0].contracts.requoted_count == 3


def test_blocked_event_stops_before_option_chain(monkeypatch) -> None:
    provider = BlockedEventProvider("ready")
    _install(monkeypatch, provider)
    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    )
    assert provider.event_calls == 1
    assert provider.chain_calls == 0
    assert result.rejected[0].stage == "event"
    assert "event_risk_blocked" in result.rejected[0].reason_codes


def test_stale_event_source_stops_before_option_chain(monkeypatch) -> None:
    provider = StaleEventProvider("ready")
    _install(monkeypatch, provider)
    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    )
    assert provider.event_calls == 1
    assert provider.chain_calls == 0
    assert result.rejected[0].stage == "event"
    assert result.rejected[0].reason_codes == ("event_source_stale",)
    assert result.generated_at == FIXTURE_TIMESTAMP


def test_unavailable_event_service_is_rejected_without_aborting_scan(monkeypatch) -> None:
    provider = UnavailableEventProvider("ready")
    _install(monkeypatch, provider)

    result = scan_module.run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")

    assert provider.event_calls == 1
    assert provider.chain_calls == 0
    assert result.evaluated_count == 1
    assert result.rejected[0].stage == "event"
    assert result.rejected[0].reason_codes == ("event_data_unavailable",)
    assert result.rejected[0].details["provider_error_type"] == "RuntimeError"


def test_unavailable_option_chain_is_rejected_without_aborting_scan(monkeypatch) -> None:
    provider = UnavailableChainProvider("ready")
    _install(monkeypatch, provider)

    result = scan_module.run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")

    assert provider.chain_calls == 1
    assert provider.refresh_calls == 0
    assert result.rejected[0].stage == "contract"
    assert result.rejected[0].reason_codes == ("option_chain_unavailable",)


def test_unavailable_requote_is_rejected_without_aborting_scan(monkeypatch) -> None:
    provider = UnavailableRequoteProvider("ready")
    _install(monkeypatch, provider)

    result = scan_module.run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")

    assert provider.chain_calls == 1
    assert provider.refresh_calls == 1
    assert result.rejected[0].stage == "contract"
    assert result.rejected[0].reason_codes == ("option_requote_unavailable",)


def test_live_cli_skips_non_trading_session(monkeypatch, capsys) -> None:
    monkeypatch.setattr(scan_module, "is_trading_day", lambda day: False)
    monkeypatch.setattr(sys, "argv", ["scanner.run_scan", "intraday"])
    monkeypatch.setattr(
        scan_module,
        "run_scan",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not scan")),
    )

    assert scan_module.main() == 0
    assert "not an NYSE trading session" in capsys.readouterr().out
