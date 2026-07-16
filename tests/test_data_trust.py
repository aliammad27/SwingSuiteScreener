from dataclasses import replace
from datetime import timedelta

from scanner.data_trust import assess_data_trust
from scanner.models import EventRiskStatus, ScanType
from scanner.providers.fixtures import FIXTURE_TIMESTAMP
from scanner.run_scan import run_scan
from scanner.strategy_profile import PROFILE


def _candidate():
    return run_scan(
        ScanType.INTRADAY,
        fixture=True,
        scenario="ready",
    ).ready_verify[0]


def test_full_trust_requires_sip_opra_fresh_stable_evidence() -> None:
    candidate = _candidate()
    trusted = assess_data_trust(
        stock_feed="sip",
        contracts=candidate.contracts,
        event=candidate.event_risk,
        as_of=FIXTURE_TIMESTAMP,
        profile=PROFILE,
    )
    assert trusted.trustworthy

    stock_untrusted = assess_data_trust(
        stock_feed="iex",
        contracts=candidate.contracts,
        event=candidate.event_risk,
        as_of=FIXTURE_TIMESTAMP,
        profile=PROFILE,
    )
    assert not stock_untrusted.stock_trusted
    assert "stock_feed_not_sip" in stock_untrusted.reasons


def test_unstable_quote_and_stale_event_are_not_trusted() -> None:
    candidate = _candidate()
    assert candidate.contracts.primary_risk is not None
    unstable_contracts = replace(
        candidate.contracts,
        primary_risk=replace(
            candidate.contracts.primary_risk,
            quote_stable=False,
        ),
    )
    stale_event = replace(
        candidate.event_risk,
        status=EventRiskStatus.CLEAR,
        source_timestamp=FIXTURE_TIMESTAMP - timedelta(hours=25),
    )
    trust = assess_data_trust(
        stock_feed="sip",
        contracts=unstable_contracts,
        event=stale_event,
        as_of=FIXTURE_TIMESTAMP,
        profile=PROFILE,
    )
    assert not trust.option_trusted
    assert not trust.event_trusted
    assert "option_quote_unstable" in trust.reasons
    assert "event_source_stale" in trust.reasons
