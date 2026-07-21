from pathlib import Path

from scanner.models import ScanType
from scanner.notifications import (
    DeliveryResult,
    candidate_caption,
    completion_message,
    notify_scan,
)
from scanner.run_scan import run_scan
from scanner.storage.base import Storage


class MemoryStorage(Storage):
    def __init__(self) -> None:
        self.values: dict[str, dict] = {}

    def load_json(self, key: str) -> dict:
        return self.values.get(key, {}).copy()

    def save_json(self, key: str, value: dict) -> None:
        self.values[key] = value.copy()


class SequencedNotifier:
    def __init__(self) -> None:
        self.send_results = [
            DeliveryResult(False, "temporary_failure", "temporary"),
            DeliveryResult(True, "delivered"),
        ]
        self.send_calls = 0

    def available(self) -> bool:
        return True

    def send(self, message: str, *, silent: bool = False) -> DeliveryResult:
        del message, silent
        result = self.send_results[self.send_calls]
        self.send_calls += 1
        return result

    def send_photo(self, photo_path: Path, caption: str = "") -> DeliveryResult:
        del photo_path, caption
        return DeliveryResult(True, "delivered")


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
    candidate = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready").ready_verify[0]
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


def test_failed_digest_is_retried_before_snapshot_is_recorded(
    monkeypatch,
) -> None:
    import scanner.notifications as notifications

    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="zero")
    storage = MemoryStorage()
    notifier = SequencedNotifier()
    monkeypatch.setattr(notifications, "TelegramNotifier", lambda: notifier)
    monkeypatch.setattr(notifications, "configured_storage", lambda: storage)
    monkeypatch.setattr(notifications, "log_delivery", lambda *args, **kwargs: None)

    notify_scan(result, Path("report.md"), fixture=False)
    assert storage.values == {}

    notify_scan(result, Path("report.md"), fixture=False)
    assert notifier.send_calls == 2
    assert "completion_snapshots" in storage.values["notification_state"]
