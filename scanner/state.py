from __future__ import annotations

import hashlib
from typing import Any

from scanner.models import Candidate
from scanner.storage.base import Storage


def notification_identifier(
    scan_date: str, run_type: str, candidate: Candidate, event_type: str
) -> str:
    raw = "|".join(
        [
            scan_date,
            run_type,
            candidate.symbol,
            candidate.grade.value,
            event_type,
            f"{candidate.entry_plan.trigger:.2f}",
            f"{candidate.entry_plan.support:.2f}",
            f"{candidate.entry_plan.invalidation:.2f}",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
