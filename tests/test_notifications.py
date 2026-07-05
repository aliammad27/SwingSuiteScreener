from dataclasses import replace
from datetime import datetime

from scanner.clocks import NY
from scanner.daily_prep import nightly_prep_message, ranked_nightly_items, weekly_radar_message
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
    candidate_text = candidate_message(result.s_tier[0], md)
    completion_text = completion_message(result, md)
    # candidate format — compact and scannable
    assert "S TIER SETUP" in candidate_text
    assert "Tgt $" in candidate_text
    assert "Strike $" in candidate_text
    assert "14-21DTE" in candidate_text
    assert "-50% premium hard stop" in candidate_text
    assert "max 4 concurrent" in candidate_text
    # completion format
    assert "POST CLOSE SCAN COMPLETE" in completion_text
    assert "14-21DTE" in completion_text
    assert "SSTR S | $" in completion_text
    assert "Tgt $" in completion_text
    assert "ET" in completion_text  # ET timestamp present


def test_technical_watch_messages_include_option_plan() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="technical_watch")
    md, _ = write_reports(result)
    candidate_text = candidate_message(result.technical_watch[0], md)
    completion_text = completion_message(result, md)

    assert "TECHNICAL WATCH" in candidate_text
    assert "Tgt $" in candidate_text
    assert "Strike $" in candidate_text
    assert "14-21DTE" in candidate_text
    assert "SSTR TW | $" in completion_text
    assert "14-21DTE" in completion_text


def test_post_close_zero_setup_notification() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    md, _ = write_reports(result)
    message = completion_message(result, md)
    assert "No setups qualified. Standards not lowered." in message
    assert "POST CLOSE SCAN COMPLETE" in message
    assert "ET" in message


def test_nightly_prep_message_for_monday_open() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="s_tier")
    md, _ = write_reports(result)
    message = nightly_prep_message(result, md, datetime(2026, 6, 21, 21, 0, tzinfo=NY))

    assert "NIGHTLY WATCHLIST" in message
    assert "Next: Monday, June 22, 2026" in message
    assert "S: SSTR" in message
    assert "A+: None" in message
    assert "B: None" in message
    assert "TW: None" in message
    assert "Watch: None" in message
    assert "Top setups:" in message
    assert "SSTR S | " in message
    assert "→ " in message
    assert "Sup " in message
    assert "https://www.tradingview.com/chart/?symbol=SSTR" in message
    assert "What to look for:" not in message
    assert "Levels to watch:" not in message
    assert "Report:" not in message


def test_nightly_prep_a_plus_reason_does_not_render_none() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True)
    md, _ = write_reports(result)
    message = nightly_prep_message(result, md, datetime(2026, 6, 21, 21, 0, tzinfo=NY))

    aplus_lines = [line for line in message.splitlines() if "APLUS A+" in line]
    assert aplus_lines, "APLUS A+ line not found in message"
    assert "minor gap" in aplus_lines[0]
    assert ", None" not in aplus_lines[0]


def test_nightly_prep_zero_candidate_message_keeps_standards() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    md, _ = write_reports(result)
    message = nightly_prep_message(result, md, datetime(2026, 6, 21, 21, 0, tzinfo=NY))

    assert "S: None" in message
    assert "A+: None" in message
    assert "B: None" in message
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
    assert "AAPL Watch | " in message
    assert "Tgt " not in message
    assert "Strike " not in message
    assert "ZERO" not in message


def test_weekly_radar_uses_same_ranked_watchlist() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="technical_watch")
    md, _ = write_reports(result)
    message = weekly_radar_message(result, md, datetime(2026, 6, 21, 20, 0, tzinfo=NY))

    assert "WEEKLY RADAR" in message
    assert "TW: SSTR" in message
    assert "SSTR TW | " in message
    assert "https://www.tradingview.com/chart/?symbol=SSTR" in message


def test_setup_items_survive_watch_ranking_limit() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="technical_watch")
    result = replace(
        result,
        rejected=[
            RejectedRecord(
                f"WATCH{idx}",
                "grading",
                ["waiting_for_timing"],
                {
                    "watch_eligible": True,
                    "command_score": 100,
                    "daily_momentum_score": 100,
                    "four_hour_momentum_score": 100,
                },
            )
            for idx in range(12)
        ],
    )

    items = ranked_nightly_items(result)

    assert items[0].bucket == "TW"
    assert items[0].target_price is not None
    assert items[0].research_call_strike is not None
    assert len(items) == 8


def test_telegram_photo_missing_credentials_safe(tmp_path) -> None:
    image = tmp_path / "chart.png"
    image.write_bytes(b"not-a-real-image")
    notifier = TelegramNotifier(token="", chat_id="")

    result = notifier.send_photo(image, "chart")

    assert result.delivered is False
    assert result.status == "not_configured"
