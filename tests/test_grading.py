from dataclasses import replace

from scanner.grading import classify_candidate
from scanner.models import EventRiskStatus, PatternStatus, ReviewState, ScanType
from scanner.run_scan import run_scan
from scanner.strategy_profile import PROFILE


def _ready_candidate():
    return run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]


def _classify(candidate, **changes):
    values = {
        "lane": candidate.lane,
        "scores": candidate.scores,
        "trend": candidate.trend,
        "pattern": candidate.pattern,
        "timing": candidate.timing,
        "market": candidate.market,
        "event": candidate.event_risk,
        "contracts": candidate.contracts,
        "data_trust": candidate.data_trust,
        "profile": PROFILE,
    }
    values.update(changes)
    return classify_candidate(**values)


def test_ready_threshold_is_inclusive_but_research_capped() -> None:
    candidate = _ready_candidate()
    at_boundary = replace(
        candidate.scores,
        trend=80,
        leadership=70,
        setup=75,
        timing=75,
        market=70,
        contract=80,
        risk=70,
    )
    state, reasons = _classify(candidate, scores=at_boundary)
    assert state == ReviewState.READY_VERIFY
    assert reasons == ("research_validation_required",)
    below = replace(at_boundary, trend=79)
    state, reasons = _classify(candidate, scores=below)
    assert state == ReviewState.DEVELOPING
    assert "trend_below_ready_threshold" in reasons


def test_unknown_event_fails_closed() -> None:
    candidate = _ready_candidate()
    event = replace(
        candidate.event_risk,
        status=EventRiskStatus.UNKNOWN,
        earnings_date=None,
    )
    state, reasons = _classify(candidate, event=event)
    assert state == ReviewState.REJECTED
    assert "event_risk_unknown_fail_closed" in reasons


def test_forming_pattern_stays_developing() -> None:
    candidate = _ready_candidate()
    pattern = replace(candidate.pattern, status=PatternStatus.FORMING)
    state, reasons = _classify(candidate, pattern=pattern)
    assert state == ReviewState.DEVELOPING
    assert "pattern_not_ready" in reasons


def test_stale_pattern_is_rejected_after_one_bar_lifecycle() -> None:
    candidate = _ready_candidate()
    pattern = replace(candidate.pattern, status=PatternStatus.STALE, age_bars=2)
    state, reasons = _classify(candidate, pattern=pattern)
    assert state == ReviewState.REJECTED
    assert "pattern_stale" in reasons
