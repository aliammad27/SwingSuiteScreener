from dataclasses import replace
from datetime import UTC, datetime

from scanner.models import ScanType
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.strategy_profile import PROFILE
from scanner.timing import analyze_timing, market_hourly_confirmation


def _timing(*, scan_type: ScanType, as_of=FIXTURE_TIMESTAMP):
    provider = FixtureDataProvider("ready")
    return analyze_timing(
        "SSTR",
        provider.one_hour("SSTR"),
        daily_filter_passed=True,
        market_confirmation=market_hourly_confirmation(
            provider.one_hour("SPY"),
            provider.one_hour("QQQ"),
        ),
        as_of=as_of,
        scan_type=scan_type,
        profile=PROFILE,
    )


def test_completed_hour_timing_confirms_inside_entry_window() -> None:
    timing = _timing(scan_type=ScanType.INTRADAY)
    assert timing.bullish_confirmation
    assert timing.entry_window_open
    assert not timing.management_only
    assert timing.completed_at.minute == 30
    assert timing.completed_at <= FIXTURE_TIMESTAMP
    assert timing.ema9 > timing.ema21
    assert timing.tactical_warning > timing.tactical_failure


def test_entry_cutoff_and_non_intraday_scans_are_management_only() -> None:
    after_cutoff = _timing(
        scan_type=ScanType.INTRADAY,
        as_of=FIXTURE_TIMESTAMP.replace(hour=19),
    )
    assert not after_cutoff.entry_window_open
    assert after_cutoff.management_only
    assert not after_cutoff.bullish_confirmation
    post_close = _timing(scan_type=ScanType.POST_CLOSE)
    assert post_close.management_only


def test_entry_window_includes_1445_et_but_excludes_1446() -> None:
    at_cutoff = _timing(
        scan_type=ScanType.INTRADAY,
        as_of=datetime(2026, 6, 18, 18, 45, tzinfo=UTC),
    )
    after_cutoff = _timing(
        scan_type=ScanType.INTRADAY,
        as_of=datetime(2026, 6, 18, 18, 46, tzinfo=UTC),
    )
    assert at_cutoff.entry_window_open
    assert not after_cutoff.entry_window_open


def test_uncompleted_hour_is_ignored() -> None:
    provider = FixtureDataProvider("ready")
    base = provider.one_hour("SSTR")
    future = replace(
        base[-1],
        timestamp=base[-1].timestamp.replace(hour=base[-1].timestamp.hour + 1),
        close=base[-1].close * 0.5,
        completed=False,
    )
    expected = analyze_timing(
        "SSTR",
        base,
        daily_filter_passed=True,
        market_confirmation=True,
        as_of=FIXTURE_TIMESTAMP,
        scan_type=ScanType.INTRADAY,
        profile=PROFILE,
    )
    actual = analyze_timing(
        "SSTR",
        [*base, future],
        daily_filter_passed=True,
        market_confirmation=True,
        as_of=FIXTURE_TIMESTAMP,
        scan_type=ScanType.INTRADAY,
        profile=PROFILE,
    )
    assert actual == expected


def test_hour_whose_close_is_after_scan_time_is_ignored() -> None:
    provider = FixtureDataProvider("ready")
    base = provider.one_hour("SSTR")
    future = replace(
        base[-1],
        timestamp=base[-1].timestamp.replace(
            hour=base[-1].timestamp.hour + 1,
        ),
        close=base[-1].close * 0.5,
        completed=True,
    )
    expected = analyze_timing(
        "SSTR",
        base,
        daily_filter_passed=True,
        market_confirmation=True,
        as_of=FIXTURE_TIMESTAMP,
        scan_type=ScanType.INTRADAY,
        profile=PROFILE,
    )
    actual = analyze_timing(
        "SSTR",
        [*base, future],
        daily_filter_passed=True,
        market_confirmation=True,
        as_of=FIXTURE_TIMESTAMP,
        scan_type=ScanType.INTRADAY,
        profile=PROFILE,
    )
    assert actual == expected
