from dataclasses import replace

from scanner.models import PatternStatus, ScanType
from scanner.run_scan import run_scan
from scanner.state import completion_snapshot, notification_identifier, should_send_completion


def test_notification_identifier_changes_with_state_or_levels() -> None:
    candidate = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready").ready[0]
    first = notification_identifier("2026-06-18", "post_close", candidate, "transition")
    changed = replace(
        candidate,
        pattern=replace(candidate.pattern, status=PatternStatus.CONFIRMED),
    )
    second = notification_identifier("2026-06-18", "post_close", changed, "transition")
    assert first != second


def test_completion_snapshot_tracks_pattern_contract_and_market() -> None:
    result = run_scan(ScanType.PREMARKET, fixture=True, scenario="ready")
    snapshot = completion_snapshot(result)
    assert snapshot["market_regime"] == "Supportive"
    assert snapshot["setups"]["SSTR"]["state"] == "ready"
    assert snapshot["setups"]["SSTR"]["contract"].startswith("SSTR")


def test_only_on_change_suppresses_identical_digest() -> None:
    result = run_scan(ScanType.FOUR_HOUR, fixture=True, scenario="ready")
    snapshot = completion_snapshot(result)
    assert should_send_completion(None, snapshot, True)
    assert not should_send_completion(snapshot, snapshot, True)
    assert should_send_completion(snapshot, snapshot, False)
