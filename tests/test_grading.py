from dataclasses import replace

from scanner.grading import classify_candidate
from scanner.market_context import calculate_market_context
from scanner.models import EventRiskStatus, PatternStatus, ReviewState
from scanner.providers.fixtures import FIXTURE_TIMESTAMP
from scanner.run_scan import _providers, _scan_symbol
from scanner.strategy_profile import PROFILE


def _ready_candidate():
    market, options, events = _providers(True, "ready")
    context = calculate_market_context(market, ["SSTR", "APLUS", "BTIER", "ZERO"], PROFILE)
    return _scan_symbol("SSTR", market, options, events, context, FIXTURE_TIMESTAMP)


def _classify(candidate, **changes):
    values = {
        "lane": candidate.lane,
        "scores": candidate.scores,
        "trend": candidate.trend,
        "pattern": candidate.pattern,
        "four_hour": candidate.four_hour_momentum,
        "market": candidate.market,
        "event": candidate.event_risk,
        "contracts": candidate.contracts,
        "profile": PROFILE,
        "as_of": FIXTURE_TIMESTAMP,
    }
    values.update(changes)
    return classify_candidate(**values)


def test_ready_threshold_is_inclusive() -> None:
    candidate = _ready_candidate()
    at_boundary = replace(candidate.scores, trend=80, setup=75, momentum=75, risk=70)
    state, _ = _classify(candidate, scores=at_boundary)
    assert state == ReviewState.READY
    below = replace(at_boundary, trend=79)
    state, reasons = _classify(candidate, scores=below)
    assert state == ReviewState.DEVELOPING
    assert "trend_below_ready_threshold" in reasons


def test_unknown_event_caps_opra_candidate_at_ready_verify() -> None:
    candidate = _ready_candidate()
    event = replace(candidate.event_risk, status=EventRiskStatus.UNKNOWN, earnings_date=None)
    state, reasons = _classify(candidate, event=event)
    assert state == ReviewState.READY_VERIFY
    assert "event_calendar_requires_verification" in reasons


def test_forming_pattern_stays_developing() -> None:
    candidate = _ready_candidate()
    pattern = replace(candidate.pattern, status=PatternStatus.FORMING)
    state, reasons = _classify(candidate, pattern=pattern)
    assert state == ReviewState.DEVELOPING
    assert "pattern_not_ready" in reasons


def test_stale_pattern_is_rejected() -> None:
    candidate = _ready_candidate()
    pattern = replace(candidate.pattern, status=PatternStatus.STALE, age_bars=4)
    state, reasons = _classify(candidate, pattern=pattern)
    assert state == ReviewState.REJECTED
    assert "pattern_stale" in reasons
