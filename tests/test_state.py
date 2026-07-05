from scanner.market_regime import classify_market_regime
from scanner.models import ScanType
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol, run_scan
from scanner.state import (
    NotificationState,
    completion_snapshot,
    notification_identifier,
    should_send_completion,
)
from scanner.storage.local_json import LocalJsonStorage


def test_notification_deduplication(tmp_path) -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    identifier = notification_identifier("2026-06-18", "post_close", candidate, "new_s_tier")
    state = NotificationState(LocalJsonStorage(tmp_path))
    assert state.already_sent(identifier) is False
    state.mark_sent(identifier, {"symbol": candidate.symbol})
    assert state.already_sent(identifier) is True


def test_premarket_unchanged_result_is_suppressed(tmp_path) -> None:
    result = run_scan(ScanType.PREMARKET, fixture=True, scenario="s_tier")
    snapshot = completion_snapshot(result)
    state = NotificationState(LocalJsonStorage(tmp_path))

    # First run: no prior snapshot, must send.
    previous = state.last_completion_snapshot("premarket")
    assert should_send_completion(previous, snapshot, only_on_change=True) is True
    state.record_completion_snapshot("premarket", snapshot)

    # Second identical run: suppressed.
    previous = state.last_completion_snapshot("premarket")
    assert should_send_completion(previous, snapshot, only_on_change=True) is False


def test_changed_snapshot_sends_again(tmp_path) -> None:
    result = run_scan(ScanType.FOUR_HOUR, fixture=True, scenario="s_tier")
    snapshot = completion_snapshot(result)
    state = NotificationState(LocalJsonStorage(tmp_path))
    state.record_completion_snapshot("four_hour", snapshot)

    changed = dict(snapshot)
    changed["market_regime"] = "Hostile"
    previous = state.last_completion_snapshot("four_hour")
    assert should_send_completion(previous, changed, only_on_change=True) is True


def test_only_on_change_disabled_always_sends() -> None:
    snapshot = {"market_regime": "Mixed", "setups": {}}
    assert should_send_completion(snapshot, snapshot, only_on_change=False) is True


def test_snapshot_state_survives_reload(tmp_path) -> None:
    result = run_scan(ScanType.PREMARKET, fixture=True, scenario="s_tier")
    snapshot = completion_snapshot(result)
    NotificationState(LocalJsonStorage(tmp_path)).record_completion_snapshot(
        "premarket", snapshot
    )
    reloaded = NotificationState(LocalJsonStorage(tmp_path))
    assert reloaded.last_completion_snapshot("premarket") == snapshot


def test_weekly_radar_event_marker(tmp_path) -> None:
    state = NotificationState(LocalJsonStorage(tmp_path))
    assert state.last_event("weekly_radar_sent_date") is None
    state.record_event("weekly_radar_sent_date", "2026-07-05")
    reloaded = NotificationState(LocalJsonStorage(tmp_path))
    assert reloaded.last_event("weekly_radar_sent_date") == "2026-07-05"
