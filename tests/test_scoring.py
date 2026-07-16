from scanner.models import ReviewState, ScanType, StrategyLane
from scanner.run_scan import run_scan


def test_perfect_fixture_is_research_capped_at_ready_verify() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    assert not result.ready
    assert len(result.ready_verify) == 1
    candidate = result.ready_verify[0]
    assert candidate.state == ReviewState.READY_VERIFY
    assert candidate.lane == StrategyLane.LEADER_WEEKLY
    assert candidate.scores.trend >= 80
    assert candidate.scores.leadership is not None
    assert candidate.scores.leadership >= 70
    assert candidate.scores.setup >= 75
    assert candidate.scores.timing >= 75
    assert candidate.scores.contract >= 80
    assert candidate.contracts.primary is not None
    assert candidate.contracts.requoted_count == 3
    assert candidate.data_trust.trustworthy
    assert candidate.reasons == ("research_validation_required",)


def test_soft_contract_miss_remains_ready_verify() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready_verify")
    assert len(result.ready_verify) == 1
    candidate = result.ready_verify[0]
    assert candidate.state == ReviewState.READY_VERIFY
    assert 65 <= candidate.scores.contract < 80
    assert candidate.reasons == ("contract_score_requires_verification",)


def test_indicative_feed_forces_verify_contract() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="technical_watch")
    assert len(result.verify_contract) == 1
    candidate = result.verify_contract[0]
    assert candidate.state == ReviewState.VERIFY_CONTRACT
    assert candidate.contracts.feed == "indicative"
    assert "option_feed_not_opra" in candidate.reasons


def test_developing_fixture_stops_before_option_fetch() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="developing")
    assert len(result.developing) == 1
    candidate = result.developing[0]
    assert candidate.state == ReviewState.DEVELOPING
    assert candidate.contracts.primary is None
    assert candidate.contracts.requoted_count == 0
    assert candidate.contracts.rejection_reasons == (
        "not_fetched_until_technical_finalist",
    )


def test_post_close_is_management_only_and_does_not_fetch_contracts() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready")
    candidate = result.developing[0]
    assert candidate.timing.management_only
    assert "hourly_timing_not_confirmed" in candidate.reasons
    assert candidate.contracts.primary is None


def test_broken_trend_is_rejected() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="zero")
    assert not result.candidates
    reasons = set(result.rejected[0].reason_codes)
    assert "below_sma200" in reasons
