from __future__ import annotations

import hashlib
from typing import Any

from scanner.models import Candidate, ScanResult
from scanner.storage.base import Storage


def notification_identifier(
    scan_date: str, run_type: str, candidate: Candidate, event_type: str
) -> str:
    raw = "|".join(
        [
            scan_date,
            run_type,
            candidate.symbol,
            candidate.state.value,
            candidate.pattern.pattern_type,
            candidate.pattern.status.value,
            event_type,
            f"{candidate.entry_plan.trigger:.2f}",
            f"{candidate.entry_plan.support:.2f}",
            f"{candidate.entry_plan.invalidation:.2f}",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def completion_snapshot(result: ScanResult) -> dict[str, Any]:
    """Material state of a scan result used to detect meaningful change.

    Two runs with equal snapshots carry the same actionable information, so a
    second premarket or four-hour completion message would be pure noise.
    """
    setups: dict[str, Any] = {}
    for candidate in result.candidates:
        setups[candidate.symbol] = {
            "state": candidate.state.value,
            "lane": candidate.lane.value,
            "pattern": candidate.pattern.pattern_type,
            "pattern_status": candidate.pattern.status.value,
            "entry_status": candidate.entry_plan.status,
            "trigger": round(candidate.entry_plan.trigger, 2),
            "support": round(candidate.entry_plan.support, 2),
            "invalidation": round(candidate.entry_plan.invalidation, 2),
            "contract": (
                candidate.contracts.primary.contract_symbol
                if candidate.contracts.primary is not None
                else None
            ),
            "contract_feed": candidate.contracts.feed,
            "daily_filter": candidate.four_hour_momentum.daily_filter_passed,
        }
    return {"market_regime": result.market.regime, "market_score": result.market.score, "setups": setups}


def should_send_completion(
    previous: dict[str, Any] | None,
    snapshot: dict[str, Any],
    only_on_change: bool,
) -> bool:
    """Return True when a completion message should be delivered.

    Always send when only_on_change is disabled or no prior snapshot exists;
    otherwise send only when the material snapshot changed.
    """
    if not only_on_change:
        return True
    if previous is None:
        return True
    return previous != snapshot


class NotificationState:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.data = storage.load_json("notification_state")
        self.data.setdefault("sent", {})

    def already_sent(self, identifier: str) -> bool:
        sent = self.data.get("sent", {})
        return isinstance(sent, dict) and identifier in sent

    def mark_sent(self, identifier: str, metadata: dict[str, Any]) -> None:
        sent = self.data.setdefault("sent", {})
        if isinstance(sent, dict):
            sent[identifier] = metadata
        self.storage.save_json("notification_state", self.data)

    def last_completion_snapshot(self, run_type: str) -> dict[str, Any] | None:
        snapshots = self.data.get("completion_snapshots", {})
        if isinstance(snapshots, dict):
            value = snapshots.get(run_type)
            if isinstance(value, dict):
                return value
        return None

    def record_completion_snapshot(self, run_type: str, snapshot: dict[str, Any]) -> None:
        snapshots = self.data.setdefault("completion_snapshots", {})
        if isinstance(snapshots, dict):
            snapshots[run_type] = snapshot
        self.storage.save_json("notification_state", self.data)

    def last_event(self, name: str) -> str | None:
        events = self.data.get("events", {})
        if isinstance(events, dict):
            value = events.get(name)
            if isinstance(value, str):
                return value
        return None

    def record_event(self, name: str, value: str) -> None:
        events = self.data.setdefault("events", {})
        if isinstance(events, dict):
            events[name] = value
        self.storage.save_json("notification_state", self.data)
