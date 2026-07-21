from __future__ import annotations

import importlib
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


class IneligibleLeaderProvider(CountingFixtureProvider):
    def eligible_underlyings(
        self,
        symbols,
        expiration_date_gte,
        expiration_date_lte,
    ):
        return set()


class UnavailableEligibilityProvider(CountingFixtureProvider):
    def eligible_underlyings(
        self,
        symbols,
        expiration_date_gte,
        expiration_date_lte,
    ):
        raise RuntimeError("contract metadata unavailable")


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


def test_developing_chart_does_not_fetch_events_or_options(monkeypatch) -> None:
    provider = CountingFixtureProvider("developing")
    _install(monkeypatch, provider)
    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="developing",
    )
    assert len(result.developing) == 1
    assert provider.event_calls == 0
    assert provider.chain_calls == 0
    assert provider.refresh_calls == 0


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


def test_ineligible_leader_stops_before_chart_and_chain_fetch(monkeypatch) -> None:
    provider = IneligibleLeaderProvider("ready")
    _install(monkeypatch, provider)

    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    )

    assert result.rejected[0].stage == "universe"
    assert result.rejected[0].reason_codes == (
        "leader_no_eligible_weekly_expiration",
    )
    assert provider.event_calls == 0
    assert provider.chain_calls == 0


def test_unavailable_leader_eligibility_fails_closed(monkeypatch) -> None:
    provider = UnavailableEligibilityProvider("ready")
    _install(monkeypatch, provider)

    result = scan_module.run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    )

    assert result.rejected[0].reason_codes == (
        "leader_options_eligibility_unavailable",
    )
    assert result.rejected[0].details["eligibility_error"] == (
        "contract metadata unavailable"
    )
    assert provider.chain_calls == 0


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
