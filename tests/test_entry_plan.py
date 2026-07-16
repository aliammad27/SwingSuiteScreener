from scanner.models import ScanType
from scanner.run_scan import run_scan


def test_entry_plan_uses_pattern_levels_and_lane_window() -> None:
    candidate = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready").ready[0]
    entry = candidate.entry_plan
    assert entry.trigger == candidate.pattern.trigger
    assert entry.invalidation == candidate.pattern.invalidation
    assert entry.target_price == candidate.pattern.target
    assert entry.target_price > candidate.trend.close
    assert entry.invalidation < candidate.trend.close
    assert entry.reward_to_risk is not None and entry.reward_to_risk >= 1.5
    assert entry.intended_hold_sessions == (5, 15)
    assert entry.requalify_dte == 21


def test_index_core_uses_slower_contract_and_thesis_window() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True)
    spy = next(candidate for candidate in result.candidates if candidate.symbol == "SPY")
    assert spy.entry_plan.intended_hold_sessions == (10, 30)
    assert spy.entry_plan.requalify_dte == 30
    assert spy.contracts.primary is not None
    assert 45 <= spy.contracts.primary.dte <= 90
    assert 0.60 <= spy.contracts.primary.delta <= 0.75
