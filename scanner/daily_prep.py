from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from scanner.calendars import next_trading_day
from scanner.clocks import NY
from scanner.models import Candidate, ScanResult
from scanner.reports import FIXTURE_LABEL
from scanner.watchlist import (
    SETUP_BUCKETS,
    WatchlistItem,
    ranked_watchlist_items,
)


def _format_day(value: date) -> str:
    return f"{value.strftime('%A, %B')} {value.day}, {value.year}"


def _symbols(candidates: list[Candidate]) -> str:
    if not candidates:
        return "None"
    return ", ".join(candidate.symbol for candidate in candidates)


def _item_symbols(items: list[WatchlistItem], bucket: str) -> str:
    symbols = [item.symbol for item in items if item.bucket == bucket]
    deduped = list(dict.fromkeys(symbols))
    return ", ".join(deduped) if deduped else "None"


def ranked_nightly_items(result: ScanResult) -> list[WatchlistItem]:
    candidates = result.s_tier + result.a_plus + result.b_tier + result.technical_watch
    rejected_details = [(record.symbol, record.details) for record in result.rejected]
    return ranked_watchlist_items(candidates, rejected_details, limit=8)


def _top_lines(items: list[WatchlistItem]) -> list[str]:
    if not items:
        return []
    lines = ["", "Top setups:"]
    setup_items = [item for item in items if item.bucket in SETUP_BUCKETS]
    watch_items = [item for item in items if item.bucket == "Watch"]
    detailed_items = setup_items + watch_items[: max(0, 5 - len(setup_items))]
    for item in detailed_items:
        parts = [f"{item.symbol} {item.bucket}", item.reason]
        if item.trigger is not None:
            parts.append(f"→ {item.trigger:.2f}")
        if item.support is not None:
            parts.append(f"Sup {item.support:.2f}")
        parts.append(item.tradingview_url)
        lines.append(" | ".join(parts))
    return lines


def ticker_watchlist_section(result: ScanResult, report_path: Path | None = None) -> str:
    items = ranked_nightly_items(result)
    lines: list[str] = []
    if result.fixture:
        lines.extend([FIXTURE_LABEL, ""])
    lines.extend(
        [
            f"S: {_item_symbols(items, 'S')}",
            f"A+: {_item_symbols(items, 'A+')}",
            f"B: {_item_symbols(items, 'B')}",
            f"TW: {_item_symbols(items, 'TW')}",
            f"Watch: {_item_symbols(items, 'Watch')}",
        ]
    )
    if not items:
        lines.extend(
            [
                "",
                "No qualified or watch tickers tonight.",
                "Standards were not lowered.",
            ]
        )
    else:
        lines.extend(_top_lines(items))
    if any(item.bucket == "TW" for item in items):
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


def weekly_radar_message(
    result: ScanResult,
    report_path: Path | None = None,
    as_of: datetime | None = None,
) -> str:
    now = as_of.astimezone(NY) if as_of is not None else datetime.now(NY)
    session_day = next_trading_day(now.date())
    return (
        "WEEKLY RADAR\n"
        f"Next: {_format_day(session_day)}\n"
        f"Scanned: {result.universe_count}\n\n"
        f"{ticker_watchlist_section(result, report_path)}"
    )
