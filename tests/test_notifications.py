from scanner.models import ScanType
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
    notifier = TelegramNotifier(token=None, chat_id=None)
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
