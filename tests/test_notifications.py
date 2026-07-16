from pathlib import Path

from scanner.models import ScanType
from scanner.notifications import candidate_caption, completion_message
from scanner.run_scan import run_scan


def test_digest_is_compact_and_contains_required_context() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True)
    message = completion_message(result, Path("reports/post_close/latest.md"))
    assert len(message) <= 4096
    assert "Market Supportive" in message
    assert "Index Core" in message
    assert "Leader Swing" in message
    assert "Call:" in message
    assert "S tier" not in message


def test_candidate_caption_has_pattern_levels_evidence_and_risk() -> None:
    candidate = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready").ready[0]
    caption = candidate_caption(candidate)
    assert len(caption) <= 1024
    assert candidate.pattern.pattern_type.replace("_", " ") in caption
    assert "Inv $" in caption
    assert "T100" in caption
    assert "long call can lose the full premium" in caption.lower()


def test_no_setups_message_treats_cash_as_a_valid_state() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    message = completion_message(result, Path("report.md"))
    assert "Cash is a valid state" in message
