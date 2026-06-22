from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from scanner.calendars import is_half_day, is_trading_day, next_trading_day
from scanner.clocks import NY
from scanner.config import load_config
from scanner.models import Candidate, ScanResult
from scanner.reports import FIXTURE_LABEL


def _format_date(value: datetime) -> str:
    local = value.astimezone(NY)
    return f"{local.strftime('%A, %B')} {local.day}, {local.year}"


def _format_day(value: date) -> str:
    return f"{value.strftime('%A, %B')} {value.day}, {value.year}"


def _format_schedule_time(value: object) -> str:
    text = str(value)
    hour_text, minute_text = text.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix} ET"


def _calendar_note(as_of: datetime, session_day: date) -> str:
    tomorrow = as_of.astimezone(NY).date() + timedelta(days=1)
    if session_day == tomorrow:
        if is_half_day(session_day):
            return "Tomorrow is a scheduled half-day. Treat every alert with extra selectivity."
        return "Tomorrow is a regular trading day."
    if is_trading_day(tomorrow):
        return "Tomorrow is tradable, but the next-session calendar check selected a later date."
    return "Tomorrow is a weekend or full market holiday; use this for the next open session."


def _symbols(candidates: list[Candidate]) -> str:
    if not candidates:
        return "None"
    return ", ".join(candidate.symbol for candidate in candidates)


def _level_line(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    return (
        f"- {candidate.symbol} ({candidate.grade.value}): trigger {entry.trigger:.2f}, "
        f"support {entry.support:.2f}, invalidation {entry.invalidation:.2f}, status {entry.status}"
    )


def _monitored_symbols(result: ScanResult) -> str:
    symbols: list[str] = []
    for candidate in result.s_tier + result.a_plus + result.technical_watch:
        symbols.append(candidate.symbol)
    for rejected in result.rejected:
        symbols.append(rejected.symbol)
    deduped = list(dict.fromkeys(symbols))
    return ", ".join(deduped[:20]) if deduped else "None"


def ticker_watchlist_section(result: ScanResult, report_path: Path | None = None) -> str:
    candidates = result.s_tier + result.a_plus + result.technical_watch
    lines: list[str] = []
    if result.fixture:
        lines.extend([FIXTURE_LABEL, ""])
    lines.extend(
        [
            "TICKERS TO WATCH THIS WEEK",
            f"Market regime: {result.market_regime}",
            f"Securities scanned: {result.universe_count}",
            f"S Tier: {_symbols(result.s_tier)}",
            f"A Plus: {_symbols(result.a_plus)}",
            f"Technical Watch: {_symbols(result.technical_watch)}",
        ]
    )
    if candidates:
        lines.extend(["", "Levels to watch:"])
        lines.extend(_level_line(candidate) for candidate in candidates)
    else:
        lines.extend(
            [
                "",
                "No S Tier, A Plus, or Technical Watch tickers qualified in the attached scan.",
                "Standards were not lowered.",
            ]
        )
    lines.extend(["", f"Broader monitored universe this week: {_monitored_symbols(result)}"])
    if result.technical_watch:
        lines.extend(
            [
                "",
                "Technical Watch is not trade-ready. Verify live option bid, ask, spread, volume, "
                "open interest, DTE, delta, and IV in the broker before any call trade.",
            ]
        )
    if report_path is not None:
        lines.extend(["", f"Report: {report_path}"])
    return "\n".join(lines)


def nightly_prep_message(
    result: ScanResult,
    report_path: Path | None = None,
    as_of: datetime | None = None,
) -> str:
    now = as_of.astimezone(NY) if as_of is not None else datetime.now(NY)
    session_day = next_trading_day(now.date())
    schedule = load_config("schedule")
    premarket = _format_schedule_time(schedule.get("premarket_time", "08:45"))
    four_hour = _format_schedule_time(schedule.get("four_hour_time", "13:35"))
    post_close = _format_schedule_time(schedule.get("post_close_time", "16:20"))

    return (
        "NIGHTLY PREP — NEXT MARKET SESSION\n\n"
        f"Sent: {_format_date(now)}\n"
        f"Next market session: {_format_day(session_day)}\n"
        f"Calendar: {_calendar_note(now, session_day)}\n\n"
        "This prep uses the strict scanner to build the ticker list. "
        "No ticker is trade-ready until the option check is verified.\n\n"
        f"{ticker_watchlist_section(result, report_path)}\n\n"
        "What to look for:\n"
        "1. Daily chart first: Command Score 75+, EMA 21 above SMA 50, "
        "SMA 50 above SMA 200, price above monthly VWAP.\n"
        "2. Relative strength: stock leading or improving versus QQQ/SPY.\n"
        "3. Clean setup type: breakout close through the trigger, or pullback holding support.\n"
        "4. Four-hour timing: Momentum Score near 70+, daily filter passed, "
        "price above trigger or holding support.\n"
        "5. Option check: bid/ask spread, volume, open interest, DTE, delta, and IV must be verified "
        "before any call trade.\n\n"
        "Do not chase:\n"
        "- price more than 1 ATR above the trigger\n"
        "- support failure before entry\n"
        "- weak relative strength\n"
        "- earnings or major event risk inside the blackout window\n"
        "- unknown or poor option liquidity\n\n"
        "Automated checks:\n"
        f"- {premarket}: premarket validation\n"
        f"- {four_hour}: four-hour entry refresh\n"
        f"- {post_close}: post-close full scan\n\n"
        "Free-data rule: Technical Watch means the underlying setup may be interesting, "
        "but it is not trade-ready until live option liquidity is verified in the broker."
    )
