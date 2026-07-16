from dataclasses import replace

from scanner.models import PatternStatus, ScanType
from scanner.run_scan import run_scan
from scanner.state import (
    completion_snapshot,
    notification_identifier,
    should_send_completion,
)


def test_notification_identifier_changes_with_state_or_levels() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    first = notification_identifier(
        "2026-06-18", "intraday", candidate, "transition"
    )
    changed = replace(
        candidate,
        pattern=replace(candidate.pattern, status=PatternStatus.CONFIRMED),
    )
    second = notification_identifier(
        "2026-06-18", "intraday", changed, "transition"
    )
    assert first != second


def test_completion_snapshot_tracks_timing_contract_and_trust() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    snapshot = completion_snapshot(result)
    setup = snapshot["setups"]["SSTR"]
    assert snapshot["market_regime"] == "Supportive"
    assert setup["state"] == "ready_verify"
    assert setup["contract"].startswith("SSTR")
    assert setup["entry_window_open"] is True
    assert setup["data_trust"] is True


def test_only_on_change_suppresses_identical_intraday_digest() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    snapshot = completion_snapshot(result)
    assert should_send_completion(None, snapshot, True)
    assert not should_send_completion(snapshot, snapshot, True)
    assert should_send_completion(snapshot, snapshot, False)
