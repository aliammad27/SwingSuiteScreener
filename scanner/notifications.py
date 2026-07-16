from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib import parse, request

from scanner.charts import render_candidate_summary
from scanner.clocks import NY
from scanner.config import ROOT, load_config, load_local_env
from scanner.models import Candidate, ScanResult, ScanType
from scanner.state import NotificationState, completion_snapshot, should_send_completion
from scanner.storage.local_json import LocalJsonStorage

TELEGRAM_TEST_MESSAGE = (
    "ALI'S SCREENER BOT TEST\n\n"
    "Bullish Weekly Participation v5 notifications are connected.\n"
    "This is a delivery test only; no market scan was performed."
)


def redact_secret(value: str) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    return value.replace(token, "[REDACTED_TELEGRAM_TOKEN]") if token else value


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    status: str
    safe_error: str | None = None


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        load_local_env()
        self.token = token if token is not None else os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id if chat_id is not None else os.environ.get("TELEGRAM_CHAT_ID")
        self.username = os.environ.get("TELEGRAM_BOT_USERNAME", "AlisScreenerBot")

    def available(self) -> bool:
        return bool(self.token and self.chat_id)

    def _api(self, method: str) -> str:
        if not self.token:
            raise RuntimeError("Telegram token is not configured.")
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def _ssl_context(self) -> ssl.SSLContext | None:
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return None

    def send(self, message: str, *, silent: bool = False) -> DeliveryResult:
        if not self.available():
            return DeliveryResult(False, "not_configured", "Telegram token or chat id is missing.")
        payload = parse.urlencode(
            {
                "chat_id": self.chat_id,
                "text": message[:4096],
                "disable_notification": "true" if silent else "false",
            }
        ).encode()
        for attempt in range(3):
            try:
                req = request.Request(self._api("sendMessage"), data=payload, method="POST")
                with request.urlopen(req, timeout=12, context=self._ssl_context()) as response:
                    body = json.loads(response.read().decode("utf-8"))
                if body.get("ok") is True:
                    return DeliveryResult(True, "delivered")
                description = redact_secret(str(body.get("description", "Telegram rejected message")))
                return DeliveryResult(False, "rejected", description)
            except Exception as exc:
                if attempt == 2:
                    return DeliveryResult(False, "temporary_failure", redact_secret(str(exc)))
                time.sleep(0.5 * (2**attempt))
        return DeliveryResult(False, "temporary_failure", "unknown failure")

    def send_photo(self, photo_path: Path, caption: str = "") -> DeliveryResult:
        if not self.available():
            return DeliveryResult(False, "not_configured", "Telegram token or chat id is missing.")
        if not photo_path.exists():
            return DeliveryResult(False, "missing_file", f"Chart file not found: {photo_path}")
        for attempt in range(3):
            try:
                import requests

                with photo_path.open("rb") as handle:
                    response = requests.post(
                        self._api("sendPhoto"),
                        data={"chat_id": self.chat_id or "", "caption": caption[:1024]},
                        files={"photo": (photo_path.name, handle, "image/png")},
                        timeout=20,
                    )
                body = response.json()
                if body.get("ok") is True:
                    return DeliveryResult(True, "delivered")
                return DeliveryResult(
                    False,
                    "rejected",
                    redact_secret(str(body.get("description", "Telegram rejected photo"))),
                )
            except Exception as exc:
                if attempt == 2:
                    return DeliveryResult(False, "temporary_failure", redact_secret(str(exc)))
                time.sleep(0.5 * (2**attempt))
        return DeliveryResult(False, "temporary_failure", "unknown failure")

    def discover_chat_id(self) -> int:
        if not self.token:
            raise RuntimeError("Telegram token is not configured.")
        with request.urlopen(
            self._api("getUpdates"), timeout=12, context=self._ssl_context()
        ) as response:
            updates = json.loads(response.read().decode("utf-8"))
        for item in reversed(updates.get("result", [])):
            chat = item.get("message", {}).get("chat", {})
            if chat.get("type") == "private" and "id" in chat:
                return int(chat["id"])
        raise RuntimeError("No private chat found. Send the bot a message first.")


def _score_line(candidate: Candidate) -> str:
    scores = candidate.scores
    leadership = "-" if scores.leadership is None else str(scores.leadership)
    return (
        f"T{scores.trend} L{leadership} S{scores.setup} H{scores.timing} "
        f"Mk{scores.market} C{scores.contract} R{scores.risk}"
    )


def _contract_line(candidate: Candidate) -> str:
    contract = candidate.contracts.primary
    if contract is None:
        return f"Contract: verify live chain ({candidate.contracts.feed})"
    return (
        f"Call: {contract.expiration_date.strftime('%b %d')} ${contract.strike:g} "
        f"D{contract.delta:.2f} | {contract.dte}DTE | {contract.spread_percent:.1f}% spread"
    )


def candidate_caption(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    return (
        f"{candidate.symbol} | {candidate.lane.label} | {candidate.state.label}\n"
        f"{candidate.pattern.pattern_type.replace('_', ' ')} / {candidate.pattern.status.value} / age {candidate.pattern.age_bars}\n"
        f"${candidate.trend.close:.2f} -> ${entry.trigger:.2f} | "
        f"Tac ${entry.tactical_failure:.2f} | Struct ${entry.invalidation:.2f} | "
        f"Obj ${entry.target_price:.2f}\n"
        f"{_score_line(candidate)}\n{_contract_line(candidate)}\n"
        "Manual review only. A long call can lose the full premium."
    )


def completion_message(result: ScanResult, report_path: Path) -> str:
    now_et = datetime.now(NY).strftime("%-I:%M %p ET")
    candidates = result.candidates
    header = (
        f"{result.scan_type.value.replace('_', ' ').upper()} - BULLISH WEEKLY V5\n"
        f"Market {result.market.regime} {result.market.score}/100 | "
        f"Breadth {result.market.breadth_above_sma50:.0f}% >50D / "
        f"{result.market.breadth_above_ema21:.0f}% >21D | {now_et}\n\n"
        f"Ready {len(result.ready)} | Ready-check {len(result.ready_verify)} | "
        f"Verify {len(result.verify_contract)} | Developing {len(result.developing)}"
    )
    if not candidates:
        return header + "\n\nNo bullish setup is ready for review. Cash is a valid state."
    lines: list[str] = [header, ""]
    for candidate in candidates[:8]:
        lines.extend(
            [
                f"{candidate.symbol} | {candidate.lane.label} | {candidate.state.label}",
                f"{candidate.pattern.pattern_type.replace('_', ' ')} {candidate.pattern.status.value} age {candidate.pattern.age_bars}",
                f"${candidate.trend.close:.2f} -> ${candidate.entry_plan.trigger:.2f} | "
                f"Tac ${candidate.entry_plan.tactical_failure:.2f} | "
                f"Struct ${candidate.entry_plan.invalidation:.2f} | "
                f"Obj ${candidate.entry_plan.target_price:.2f}",
                _score_line(candidate),
                _contract_line(candidate),
                "",
            ]
        )
    lines.append(f"Audit report: {report_path}")
    return "\n".join(lines)[:4096]


def log_delivery(
    identifier: str,
    status: str,
    ticker: str = "",
    event_type: str = "",
    error: str = "",
) -> None:
    log_path = ROOT / "logs" / "notifications.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "provider": "telegram",
            "notification_identifier": identifier,
            "ticker": ticker,
            "event_type": event_type,
            "delivery_status": status,
            "safe_error_message": redact_secret(error),
        }
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def notify_scan(result: ScanResult, report_path: Path, *, fixture: bool) -> None:
    message = completion_message(result, report_path)
    if fixture:
        print(message)
        return
    state = NotificationState(LocalJsonStorage())
    snapshot = completion_snapshot(result)
    only_on_change = result.scan_type in {ScanType.PREMARKET, ScanType.INTRADAY}
    configured = load_config("notifications")
    if only_on_change:
        setting = configured.get(
            "send_premarket_only_on_change"
            if result.scan_type == ScanType.PREMARKET
            else "send_intraday_only_on_change",
            True,
        )
        only_on_change = bool(setting)
    previous = state.last_completion_snapshot(result.scan_type.value)
    state.record_completion_snapshot(result.scan_type.value, snapshot)
    if not should_send_completion(previous, snapshot, only_on_change):
        log_delivery("digest", "suppressed_unchanged", event_type="digest")
        return
    notifier = TelegramNotifier()
    delivery = notifier.send(message, silent=result.scan_type != ScanType.POST_CLOSE)
    log_delivery("digest", delivery.status, event_type="digest", error=delivery.safe_error or "")
    if not delivery.delivered:
        return
    for candidate in result.candidates[:3]:
        chart_path = render_candidate_summary(candidate)
        photo = notifier.send_photo(chart_path, candidate_caption(candidate))
        log_delivery(
            f"chart_{candidate.symbol}",
            photo.status,
            ticker=candidate.symbol,
            event_type="candidate_chart",
            error=photo.safe_error or "",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["discover_chat_id"])
    args = parser.parse_args()
    if args.command == "discover_chat_id":
        notifier = TelegramNotifier()
        try:
            print(f"Detected private chat id: {notifier.discover_chat_id()}")
        except Exception as exc:
            print(f"Unable to discover Telegram chat id safely: {redact_secret(str(exc))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
