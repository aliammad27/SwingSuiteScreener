from scanner.models import ScanType
from scanner.run_scan import run_scan


def test_entry_plan_separates_structural_tactical_and_target_levels() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    entry = candidate.entry_plan
    assert entry.trigger == candidate.pattern.trigger
    assert entry.invalidation == candidate.pattern.invalidation
    assert entry.tactical_warning == candidate.timing.tactical_warning
    assert entry.tactical_failure == candidate.timing.tactical_failure
    assert entry.target_price > candidate.trend.close
    assert entry.invalidation < candidate.trend.close
    assert entry.planning_objective_2r > candidate.trend.close
    assert entry.target_basis in {
        "nearest confirmed daily pivot",
        "2R planning objective; review path through nearest confirmed daily pivot",
        "2R planning objective; no confirmed overhead daily pivot",
    }
    assert entry.intended_hold_sessions == (1, 5)
    assert entry.no_progress_sessions == 2
    assert entry.requalify_dte == 7


def test_index_weekly_uses_shorter_hold_and_requalification_window() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True)
    spy = next(candidate for candidate in result.candidates if candidate.symbol == "SPY")
    assert spy.entry_plan.intended_hold_sessions == (1, 4)
    assert spy.entry_plan.no_progress_sessions == 2
    assert spy.entry_plan.requalify_dte == 5
