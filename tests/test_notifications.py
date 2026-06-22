from dataclasses import replace
from datetime import datetime

from scanner.clocks import NY
from scanner.daily_prep import nightly_prep_message
from scanner.models import RejectedRecord, ScanType
from scanner.notifications import (
    TELEGRAM_TEST_MESSAGE,
    TelegramNotifier,
    candidate_message,
    completion_message,
)
from scanner.reports import write_reports
from scanner.run_scan import run_scan


def test_telegram_message_generation() -> None:
    assert "ALI'S SCREENER BOT TEST" in TELEGRAM_TEST_MESSAGE


def test_telegram_missing_credentials_safe() -> None:
    notifier = TelegramNotifier(token="", chat_id="")
    result = notifier.send("hello")
    assert result.delivered is False
    assert result.status == "not_configured"


def test_candidate_and_completion_messages() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="s_tier")
    md, _ = write_reports(result)
    assert result.s_tier
    assert "S TIER SETUP" in candidate_message(result.s_tier[0], md)
    assert "POST CLOSE SCAN COMPLETE" in completion_message(result, md)


def test_post_close_zero_setup_notification() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    md, _ = write_reports(result)
    message = completion_message(result, md)
    assert "No S tier or A plus setups qualified today." in message


def test_nightly_prep_message_for_monday_open() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="s_tier")
    md, _ = write_reports(result)
    message = nightly_prep_message(result, md, datetime(2026, 6, 21, 21, 0, tzinfo=NY))

    assert "NIGHTLY WATCHLIST" in message
    assert "Next: Monday, June 22, 2026" in message
    assert "S: SSTR" in message
    assert "A+: None" in message
    assert "TW: None" in message
    assert "Watch: None" in message
    assert "What to look for:" not in message
    assert "Levels to watch:" not in message
    assert "Report:" not in message


def test_nightly_prep_zero_candidate_message_keeps_standards() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    md, _ = write_reports(result)
    message = nightly_prep_message(result, md, datetime(2026, 6, 21, 21, 0, tzinfo=NY))

    assert "S: None" in message
    assert "A+: None" in message
    assert "TW: None" in message
    assert "Watch: None" in message
    assert "No qualified or watch tickers tonight." in message
    assert "Standards were not lowered." in message
    assert "ZERO" not in message


def test_nightly_prep_watch_bucket_requires_strategy_flag() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    result = replace(
        result,
        rejected=[
            RejectedRecord(
                "AAPL",
                "grading",
                ["waiting_for_timing"],
                {"watch_eligible": True},
            ),
            RejectedRecord(
                "ZERO",
                "grading",
                ["weak_daily_structure"],
                {"watch_eligible": False},
            ),
        ],
    )
    md, _ = write_reports(result)
    message = nightly_prep_message(result, md, datetime(2026, 6, 21, 21, 0, tzinfo=NY))

    assert "Watch: AAPL" in message
    assert "ZERO" not in message
