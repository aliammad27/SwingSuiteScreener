from __future__ import annotations

import os
import re
from datetime import UTC, date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from zoneinfo import ZoneInfo

import requests

from scanner.calendars import next_trading_day
from scanner.config import load_config
from scanner.models import (
    EventRisk,
    EventRiskStatus,
    EventType,
    EventWindow,
    StrategyLane,
)
from scanner.providers.base import EventRiskProvider
from scanner.strategy_profile import PROFILE

NY = ZoneInfo("America/New_York")
_USER_AGENT = "SwingSuiteScreener/5.0 read-only market research"


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _trading_session_cutoff(start: date, sessions: int) -> date:
    current = start
    remaining = sessions
    while remaining > 0:
        current = next_trading_day(current)
        remaining -= 1
    return current


def _source_time(headers: Any, fallback: datetime) -> datetime:
    for name in ("Last-Modified", "Date"):
        value = headers.get(name, "") if headers is not None else ""
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            continue
        return parsed.astimezone(UTC)
    return fallback.astimezone(UTC)


class ConfiguredEventRiskProvider(EventRiskProvider):
    def event_risk(
        self,
        symbol: str,
        as_of: datetime,
        lane: StrategyLane,
    ) -> EventRisk:
        del lane
        config = load_config("events")
        default = str(config.get("default_status", EventRiskStatus.UNKNOWN.value))
        raw_events = config.get("events", {})
        raw = raw_events.get(symbol, {}) if isinstance(raw_events, dict) else {}
        if not isinstance(raw, dict):
            raw = {}
        try:
            status = EventRiskStatus(str(raw.get("status", default)))
        except ValueError:
            status = EventRiskStatus.UNKNOWN
        raw_date = raw.get("earnings_date")
        earnings_date: date | None = None
        if isinstance(raw_date, date):
            earnings_date = raw_date
        elif raw_date:
            try:
                earnings_date = date.fromisoformat(str(raw_date))
            except ValueError:
                status = EventRiskStatus.UNKNOWN
        source_timestamp = _parse_datetime(raw.get("source_timestamp"))
        return EventRisk(
            symbol=symbol,
            status=status,
            earnings_date=earnings_date,
            summary=str(raw.get("summary", "Trusted event data is unavailable.")),
            source=str(raw.get("source", "config/events.yaml")),
            checked_at=as_of,
            source_timestamp=source_timestamp,
        )


class TrustedEventRiskProvider(EventRiskProvider):
    """Read-only earnings and macro-event adapter with fail-closed fallbacks."""

    def __init__(self) -> None:
        self.massive_key = os.environ.get("MASSIVE_API_KEY")
        self.massive_base_url = os.environ.get(
            "MASSIVE_BASE_URL", "https://api.massive.com"
        )
        self.fallback = ConfiguredEventRiskProvider()
        self._macro_cache: tuple[datetime, tuple[EventWindow, ...]] | None = None

    def _get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[str, Any]:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": _USER_AGENT},
            timeout=20,
        )
        response.raise_for_status()
        return response.text, response.headers

    def _earnings(self, symbol: str, as_of: datetime) -> EventRisk | None:
        if not self.massive_key:
            return None
        horizon = as_of.date() + timedelta(days=20)
        response = requests.get(
            f"{self.massive_base_url}/benzinga/v1/earnings",
            params={
                "apiKey": self.massive_key,
                "ticker": symbol,
                "date.gte": as_of.date().isoformat(),
                "date.lte": horizon.isoformat(),
                "sort": "date.asc",
                "limit": "10",
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=20,
        )
        response.raise_for_status()
        source_timestamp = _source_time(response.headers, as_of)
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Massive earnings response must be a mapping.")
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise RuntimeError("Massive earnings results must be a list.")
        records = [item for item in raw_results if isinstance(item, dict)]
        if not records:
            return EventRisk(
                symbol=symbol,
                status=EventRiskStatus.CLEAR,
                earnings_date=None,
                summary="No earnings event returned inside the v5 research horizon.",
                source="Massive Benzinga earnings",
                checked_at=as_of,
                source_timestamp=source_timestamp,
            )
        raw_date = records[0].get("date")
        if not raw_date:
            return None
        earnings_date = date.fromisoformat(str(raw_date))
        cutoff = _trading_session_cutoff(
            as_of.date(),
            PROFILE.lane(StrategyLane.LEADER_WEEKLY).intended_hold_sessions[1]
            + PROFILE.leader_earnings_buffer_sessions,
        )
        blocked = earnings_date <= cutoff
        status_text = str(records[0].get("date_status", "unconfirmed"))
        updated = str(records[0].get("last_updated", "not supplied"))
        event_at = datetime.combine(earnings_date, time(9, 30), NY)
        window = EventWindow(
            event_type=EventType.EARNINGS,
            starts_at=datetime.combine(earnings_date, time(0, 0), NY),
            event_at=event_at,
            blocked_until=datetime.combine(earnings_date, time(16, 0), NY),
            source="Massive Benzinga earnings",
            source_timestamp=source_timestamp,
            summary=(
                f"Earnings {status_text} for {earnings_date.isoformat()}; "
                f"record updated {updated}."
            ),
        )
        return EventRisk(
            symbol=symbol,
            status=EventRiskStatus.BLOCKED if blocked else EventRiskStatus.CLEAR,
            earnings_date=earnings_date,
            summary=window.summary,
            source=window.source,
            checked_at=as_of,
            windows=(window,),
            source_timestamp=source_timestamp,
        )

    @staticmethod
    def _parse_bls_ics(text: str, source_timestamp: datetime) -> list[EventWindow]:
        unfolded = re.sub(r"\r?\n[ \t]", "", text)
        windows: list[EventWindow] = []
        for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", unfolded, re.S):
            summary_match = re.search(r"\nSUMMARY:(.+)", block)
            start_match = re.search(
                r"\nDTSTART(?:;TZID=[^:]+)?:([0-9]{8}T[0-9]{6})", block
            )
            if summary_match is None or start_match is None:
                continue
            summary = summary_match.group(1).strip()
            event_type = {
                "Consumer Price Index": EventType.CPI,
                "Employment Situation": EventType.EMPLOYMENT_SITUATION,
            }.get(summary)
            if event_type is None:
                continue
            event_at = datetime.strptime(
                start_match.group(1), "%Y%m%dT%H%M%S"
            ).replace(tzinfo=NY)
            regular_open = datetime.combine(event_at.date(), time(9, 30), NY)
            first_completed_hour = datetime.combine(
                event_at.date(), time(10, 30), NY
            )
            blocked_until = (
                first_completed_hour
                if event_at <= regular_open
                else event_at + timedelta(hours=PROFILE.macro_post_event_completed_hours)
            )
            windows.append(
                EventWindow(
                    event_type=event_type,
                    starts_at=min(event_at, regular_open),
                    event_at=event_at,
                    blocked_until=blocked_until,
                    source="U.S. Bureau of Labor Statistics release calendar",
                    source_timestamp=source_timestamp,
                    summary=f"{summary} release at {event_at.strftime('%Y-%m-%d %H:%M %Z')}.",
                )
            )
        return windows

    @staticmethod
    def _parse_fomc_html(
        text: str,
        source_timestamp: datetime,
        years: tuple[int, ...],
    ) -> list[EventWindow]:
        windows: list[EventWindow] = []
        for year in years:
            section_match = re.search(
                rf">{year} FOMC Meetings</a>.*?<div class=\"panel-footer\">",
                text,
                re.S,
            )
            if section_match is None:
                continue
            section = section_match.group(0)
            meetings = re.findall(
                r"fomc-meeting__month[^>]*><strong>([A-Za-z]+)</strong>.*?"
                r"fomc-meeting__date[^>]*>([0-9]{1,2})(?:-([0-9]{1,2}))?\*?</div>",
                section,
                re.S,
            )
            for month_name, first_day, second_day in meetings:
                month = datetime.strptime(month_name, "%B").month
                release_day = int(second_day or first_day)
                event_at = datetime(year, month, release_day, 14, 0, tzinfo=NY)
                starts_at = datetime(year, month, release_day, 9, 30, tzinfo=NY)
                windows.append(
                    EventWindow(
                        event_type=EventType.FOMC,
                        starts_at=starts_at,
                        event_at=event_at,
                        blocked_until=event_at
                        + timedelta(
                            hours=PROFILE.macro_post_event_completed_hours
                        ),
                        source="Federal Reserve FOMC calendar",
                        source_timestamp=source_timestamp,
                        summary=(
                            "FOMC statement window at "
                            f"{event_at.strftime('%Y-%m-%d %H:%M %Z')}."
                        ),
                    )
                )
        return windows

    def _macro_windows(self, as_of: datetime) -> tuple[EventWindow, ...]:
        if self._macro_cache is not None:
            cache_age = as_of - self._macro_cache[0]
            if timedelta(0) <= cache_age < timedelta(hours=1):
                return self._macro_cache[1]
        bls_text, bls_headers = self._get(
            "https://www.bls.gov/schedule/news_release/bls.ics"
        )
        fed_text, fed_headers = self._get(
            "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        )
        bls_source = _source_time(bls_headers, as_of)
        fed_source = _source_time(fed_headers, as_of)
        windows = self._parse_bls_ics(bls_text, bls_source)
        windows.extend(
            self._parse_fomc_html(
                unescape(fed_text),
                fed_source,
                (as_of.year, as_of.year + 1),
            )
        )
        result = tuple(sorted(windows, key=lambda item: item.event_at))
        if not result:
            raise RuntimeError("Official macro calendars returned no recognized events.")
        self._macro_cache = (as_of, result)
        return result

    def event_risk(
        self,
        symbol: str,
        as_of: datetime,
        lane: StrategyLane,
    ) -> EventRisk:
        try:
            if lane == StrategyLane.LEADER_WEEKLY:
                earnings = self._earnings(symbol, as_of)
                if earnings is not None:
                    return earnings
            else:
                windows = self._macro_windows(as_of)
                active = tuple(
                    window
                    for window in windows
                    if window.starts_at <= as_of.astimezone(NY) < window.blocked_until
                )
                source_timestamp = min(window.source_timestamp for window in windows)
                return EventRisk(
                    symbol=symbol,
                    status=(
                        EventRiskStatus.BLOCKED
                        if active
                        else EventRiskStatus.CLEAR
                    ),
                    earnings_date=None,
                    summary=(
                        "; ".join(window.summary for window in active)
                        if active
                        else "Official Fed and BLS macro windows are clear."
                    ),
                    source="Federal Reserve and U.S. BLS calendars",
                    checked_at=as_of,
                    windows=active,
                    source_timestamp=source_timestamp,
                )
        except (OSError, RuntimeError, ValueError, requests.RequestException):
            pass
        return self.fallback.event_risk(symbol, as_of, lane)
