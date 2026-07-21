from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from scanner.data_trust import event_trust_reasons
from scanner.models import (
    EventRisk,
    EventRiskStatus,
    EventType,
    EventWindow,
    StrategyLane,
)
from scanner.providers.events import NY, TrustedEventRiskProvider, _source_time
from scanner.strategy_profile import PROFILE


def test_bls_calendar_parses_cpi_and_employment_windows() -> None:
    source_timestamp = datetime(2026, 7, 1, tzinfo=UTC)
    payload = """
BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20260714T083000
SUMMARY:Consumer Price Index
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20260807T083000
SUMMARY:Employment Situation
END:VEVENT
END:VCALENDAR
"""
    windows = TrustedEventRiskProvider._parse_bls_ics(
        payload,
        source_timestamp,
    )
    assert [window.event_type for window in windows] == [
        EventType.CPI,
        EventType.EMPLOYMENT_SITUATION,
    ]
    assert all(window.blocked_until.hour == 10 for window in windows)
    assert all(window.blocked_until.minute == 30 for window in windows)


def test_fomc_calendar_blocks_through_first_completed_post_event_hour() -> None:
    source_timestamp = datetime(2026, 7, 1, tzinfo=UTC)
    payload = """
<a>2026 FOMC Meetings</a>
<div class="fomc-meeting__month"><strong>July</strong></div>
<div class="fomc-meeting__date">28-29</div>
<div class="panel-footer"></div>
"""
    windows = TrustedEventRiskProvider._parse_fomc_html(
        payload,
        source_timestamp,
        (2026,),
    )
    assert len(windows) == 1
    window = windows[0]
    assert window.event_type == EventType.FOMC
    assert window.event_at.hour == 14
    assert window.blocked_until == datetime(2026, 7, 29, 15, 30, tzinfo=NY)


def test_index_event_window_is_blocked_then_clears(monkeypatch) -> None:
    provider = TrustedEventRiskProvider()
    event_at = datetime(2026, 7, 29, 14, 0, tzinfo=NY)
    window = EventWindow(
        event_type=EventType.FOMC,
        starts_at=event_at.replace(hour=9, minute=30),
        event_at=event_at,
        blocked_until=event_at + timedelta(hours=1),
        source="Federal Reserve FOMC calendar",
        source_timestamp=event_at.astimezone(UTC),
        summary="Test FOMC window.",
    )
    monkeypatch.setattr(provider, "_macro_windows", lambda as_of: (window,))
    blocked = provider.event_risk(
        "SPY",
        event_at,
        StrategyLane.INDEX_WEEKLY,
    )
    clear = provider.event_risk(
        "SPY",
        event_at + timedelta(hours=1),
        StrategyLane.INDEX_WEEKLY,
    )
    assert blocked.status == EventRiskStatus.BLOCKED
    assert clear.status == EventRiskStatus.CLEAR


def test_source_time_prefers_content_last_modified_timestamp() -> None:
    fallback = datetime(2026, 7, 16, 18, 0, tzinfo=UTC)
    headers = {
        "Date": "Thu, 16 Jul 2026 18:00:00 GMT",
        "Last-Modified": "Wed, 15 Jul 2026 12:00:00 GMT",
    }
    assert _source_time(headers, fallback) == datetime(
        2026,
        7,
        15,
        12,
        0,
        tzinfo=UTC,
    )


def test_index_event_trust_uses_oldest_official_source_timestamp(
    monkeypatch,
) -> None:
    provider = TrustedEventRiskProvider()
    as_of = datetime(2026, 7, 16, 12, 0, tzinfo=NY)
    older_source = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    newer_source = datetime(2026, 7, 16, 11, 0, tzinfo=UTC)
    windows = (
        EventWindow(
            event_type=EventType.CPI,
            starts_at=as_of + timedelta(days=10),
            event_at=as_of + timedelta(days=10, hours=1),
            blocked_until=as_of + timedelta(days=10, hours=2),
            source="U.S. Bureau of Labor Statistics release calendar",
            source_timestamp=older_source,
            summary="Future CPI window.",
        ),
        EventWindow(
            event_type=EventType.FOMC,
            starts_at=as_of + timedelta(days=20),
            event_at=as_of + timedelta(days=20, hours=1),
            blocked_until=as_of + timedelta(days=20, hours=2),
            source="Federal Reserve FOMC calendar",
            source_timestamp=newer_source,
            summary="Future FOMC window.",
        ),
    )
    monkeypatch.setattr(provider, "_macro_windows", lambda _as_of: windows)

    result = provider.event_risk("SPY", as_of, StrategyLane.INDEX_WEEKLY)

    assert result.source_timestamp == older_source


def test_event_http_failure_falls_back_to_unknown(
    monkeypatch,
) -> None:
    provider = TrustedEventRiskProvider()
    as_of = datetime(2026, 7, 16, 12, 0, tzinfo=NY)

    def fail_fetch(_as_of: datetime) -> tuple[EventWindow, ...]:
        raise requests.Timeout("calendar unavailable")

    monkeypatch.setattr(provider, "_macro_windows", fail_fetch)

    result = provider.event_risk("SPY", as_of, StrategyLane.INDEX_WEEKLY)

    assert result.status == EventRiskStatus.UNKNOWN


def test_event_trust_requires_fresh_source_timestamp() -> None:
    as_of = datetime(2026, 7, 16, 18, 0, tzinfo=UTC)
    missing = EventRisk(
        symbol="SPY",
        status=EventRiskStatus.CLEAR,
        earnings_date=None,
        summary="No timestamp.",
        source="test",
        checked_at=as_of,
    )
    stale = EventRisk(
        symbol="SPY",
        status=EventRiskStatus.CLEAR,
        earnings_date=None,
        summary="Stale timestamp.",
        source="test",
        checked_at=as_of,
        source_timestamp=as_of - timedelta(hours=25),
    )
    future = EventRisk(
        symbol="SPY",
        status=EventRiskStatus.CLEAR,
        earnings_date=None,
        summary="Future timestamp.",
        source="test",
        checked_at=as_of,
        source_timestamp=as_of + timedelta(seconds=1),
    )
    assert event_trust_reasons(missing, as_of, PROFILE) == ("event_source_timestamp_missing",)
    assert event_trust_reasons(stale, as_of, PROFILE) == ("event_source_stale",)
    assert event_trust_reasons(future, as_of, PROFILE) == ("event_source_timestamp_in_future",)
