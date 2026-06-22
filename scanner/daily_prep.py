from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from scanner.calendars import next_trading_day
from scanner.clocks import NY
from scanner.models import Candidate, ScanResult
from scanner.reports import FIXTURE_LABEL


def _format_day(value: date) -> str:
    return f"{value.strftime('%A, %B')} {value.day}, {value.year}"


def _symbols(candidates: list[Candidate]) -> str:
    if not candidates:
        return "None"
    return ", ".join(candidate.symbol for candidate in candidates)


def _watch_symbols(result: ScanResult) -> str:
    symbols = [
        rejected.symbol
        for rejected in result.rejected
        if rejected.details.get("watch_eligible") is True
    ]
    deduped = list(dict.fromkeys(symbols))
    return ", ".join(deduped[:20]) if deduped else "None"


def ticker_watchlist_section(result: ScanResult, report_path: Path | None = None) -> str:
    lines: list[str] = []
    if result.fixture:
        lines.extend([FIXTURE_LABEL, ""])
    lines.extend(
        [
            f"S: {_symbols(result.s_tier)}",
            f"A+: {_symbols(result.a_plus)}",
            f"TW: {_symbols(result.technical_watch)}",
            f"Watch: {_watch_symbols(result)}",
        ]
    )
    if (
        not result.s_tier
        and not result.a_plus
        and not result.technical_watch
        and _watch_symbols(result) == "None"
    ):
        lines.extend(
            [
                "",
                "No qualified or watch tickers tonight.",
                "Standards were not lowered.",
            ]
        )
    if result.technical_watch:
        lines.extend(["", "TW = technical watch only; verify options."])
    return "\n".join(lines)


def nightly_prep_message(
    result: ScanResult,
    report_path: Path | None = None,
    as_of: datetime | None = None,
) -> str:
    now = as_of.astimezone(NY) if as_of is not None else datetime.now(NY)
    session_day = next_trading_day(now.date())

    return (
        "NIGHTLY WATCHLIST\n"
        f"Next: {_format_day(session_day)}\n\n"
        f"{ticker_watchlist_section(result, report_path)}"
    )
