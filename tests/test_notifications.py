from dataclasses import replace
from pathlib import Path

from scanner.models import ReviewState, ScanType
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


class PhotoFailureNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.photo_calls = 0

    def available(self) -> bool:
        return True

    def send(self, message: str, *, silent: bool = False) -> DeliveryResult:
        del silent
        self.messages.append(message)
        return DeliveryResult(True, "delivered")

    def send_photo(self, photo_path: Path, caption: str = "") -> DeliveryResult:
        del photo_path, caption
        self.photo_calls += 1
        return DeliveryResult(False, "temporary_failure", "temporary")


def test_digest_is_compact_and_contains_required_context() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True)
    message = completion_message(result, Path("reports/intraday/latest.md"))
    assert len(message) <= 4096
    assert "Market Supportive" in message
    assert "Index Weekly" in message
    assert "Leader Weekly" in message
    assert "Call:" in message
    assert "BULLISH WEEKLY V5" in message
    assert len(message) <= 4096


def test_candidate_caption_has_tactical_structural_levels_and_risk() -> None:
    candidate = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready").ready_verify[0]
    caption = candidate_caption(candidate)
    assert len(caption) <= 1024
    assert candidate.pattern.pattern_type.replace("_", " ") in caption
    assert "tactical failure $" in caption
    assert "structural $" in caption
    assert "est call $" in caption
    assert "stable IV" in caption
    assert "Call " in caption
    assert "OI " in caption
    assert "Feed OPRA | quote " in caption
    assert "| stable" in caption
    assert "Alternatives:" in caption
    assert "long call can lose the full premium" in caption.lower()


def test_verify_contract_card_requires_live_opra_and_omits_estimate() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="technical_watch"
    ).verify_contract[0]
    caption = candidate_caption(candidate)
    assert "live OPRA verification required" in caption
    assert "est call $" not in caption


def test_ready_index_card_without_contract_fails_closed() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="missing_contracts")
    candidate = replace(result.developing[0], state=ReviewState.READY)
    caption = candidate_caption(candidate)
    assert "Index Weekly | Ready" in caption
    assert "Call: live OPRA verification required" in caption
    assert "est call $" not in caption
    assert len(caption) <= 1024


def test_premium_scenarios_can_be_hidden_without_hiding_underlying_tp() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    caption = candidate_caption(candidate, show_premium_scenarios=False)
    assert "TP1 $" in caption
    assert "est call $" not in caption
    assert "stable IV" not in caption


def test_developing_candidates_stay_in_compact_watchlist() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="developing")
    message = completion_message(result, Path("report.md"))
    assert "Developing watchlist:" in message
    assert result.developing[0].symbol in message


def test_fixture_digest_is_labeled_simulated() -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    assert "SIMULATED FIXTURE - NOT CURRENT MARKET DATA" in completion_message(
        result, Path("report.md")
    )


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


def test_failed_photo_falls_back_to_text_card(monkeypatch) -> None:
    import scanner.notifications as notifications

    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    result = replace(result, fixture=False)
    storage = MemoryStorage()
    notifier = PhotoFailureNotifier()
    deliveries: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(notifications, "TelegramNotifier", lambda: notifier)
    monkeypatch.setattr(notifications, "configured_storage", lambda: storage)
    monkeypatch.setattr(
        notifications,
        "render_candidate_summary",
        lambda candidate: Path(f"{candidate.symbol}.png"),
    )
    monkeypatch.setattr(
        notifications,
        "log_delivery",
        lambda *args, **kwargs: deliveries.append((args, kwargs)),
    )

    notify_scan(result, Path("report.md"), fixture=False)

    assert notifier.photo_calls == 1
    assert len(notifier.messages) == 2
    assert "est call $" in notifier.messages[1]
    assert any(args[0] == f"card_{result.ready_verify[0].symbol}" for args, _ in deliveries)
