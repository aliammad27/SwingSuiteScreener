from pathlib import Path

from scanner.models import ScanType
from scanner.notifications import candidate_caption, completion_message
from scanner.run_scan import run_scan


def test_digest_is_compact_and_contains_required_context() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True)
    message = completion_message(result, Path("reports/intraday/latest.md"))
    assert len(message) <= 4096
    assert "Market Supportive" in message
    assert "Index Weekly" in message
    assert "Leader Weekly" in message
    assert "Call:" in message
    assert "BULLISH WEEKLY V5" in message


def test_candidate_caption_has_tactical_structural_levels_and_risk() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    caption = candidate_caption(candidate)
    assert len(caption) <= 1024
    assert candidate.pattern.pattern_type.replace("_", " ") in caption
    assert "Tac $" in caption
    assert "Struct $" in caption
    assert "H95" in caption
    assert "long call can lose the full premium" in caption.lower()


def test_no_setups_message_treats_cash_as_a_valid_state() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="zero")
    message = completion_message(result, Path("report.md"))
    assert "Cash is a valid state" in message
