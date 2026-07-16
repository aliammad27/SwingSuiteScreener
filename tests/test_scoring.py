from scanner.models import ReviewState, ScanType, StrategyLane
from scanner.run_scan import run_scan


def test_ready_fixture_passes_every_hard_gate() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready")
    assert len(result.ready) == 1
    candidate = result.ready[0]
    assert candidate.state == ReviewState.READY
    assert candidate.lane == StrategyLane.LEADER_SWING
    assert candidate.scores.trend >= 80
    assert candidate.scores.leadership is not None and candidate.scores.leadership >= 70
    assert candidate.scores.setup >= 75
    assert candidate.scores.momentum >= 75
    assert candidate.scores.contract >= 80
    assert candidate.contracts.primary is not None


def test_ready_verify_fixture_has_trustworthy_soft_contract_miss() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready_verify")
    assert len(result.ready_verify) == 1
    candidate = result.ready_verify[0]
    assert candidate.state == ReviewState.READY_VERIFY
    assert candidate.contracts.trustworthy
    assert 65 <= candidate.scores.contract < 80


def test_indicative_feed_forces_verify_contract() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="technical_watch")
    assert len(result.verify_contract) == 1
    assert result.verify_contract[0].state == ReviewState.VERIFY_CONTRACT
    assert result.verify_contract[0].contracts.feed == "indicative"


def test_developing_fixture_never_uses_legacy_tiers() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="developing")
    assert len(result.developing) == 1
    candidate = result.developing[0]
    assert candidate.state == ReviewState.DEVELOPING
    assert "S" not in candidate.state.value


def test_blocked_event_and_broken_trend_are_rejected() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    assert not result.candidates
    reasons = set(result.rejected[0].reason_codes)
    assert "below_sma200" in reasons
    assert "earnings_inside_blackout" in reasons
