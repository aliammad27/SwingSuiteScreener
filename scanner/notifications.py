from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib import parse, request

from scanner.config import ROOT, load_local_env
from scanner.models import Candidate, ScanResult

TELEGRAM_TEST_MESSAGE = (
    "ALI'S SCREENER BOT TEST\n\n"
    "Telegram notifications are connected successfully.\n"
    "This was a test only. No market scan was performed."
)


def redact_secret(value: str) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        value = value.replace(token, "[REDACTED_TELEGRAM_TOKEN]")
    return value


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

    def send(self, message: str) -> DeliveryResult:
        if not self.available():
            return DeliveryResult(False, "not_configured", "Telegram token or chat id is missing.")
        payload = parse.urlencode({"chat_id": self.chat_id, "text": message}).encode()
        for attempt in range(3):
            try:
                req = request.Request(self._api("sendMessage"), data=payload, method="POST")
                with request.urlopen(req, timeout=12, context=self._ssl_context()) as response:
                    body = json.loads(response.read().decode("utf-8"))
                if body.get("ok") is True:
                    return DeliveryResult(True, "delivered")
                description = redact_secret(str(body.get("description", "Telegram rejected message")))
                if "Unauthorized" in description:
                    return DeliveryResult(False, "invalid_credentials", description)
                return DeliveryResult(False, "rejected", description)
            except Exception as exc:
                safe = redact_secret(str(exc))
                if attempt == 2:
                    return DeliveryResult(False, "temporary_failure", safe)
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
                        data={"chat_id": self.chat_id or "", "caption": caption},
                        files={"photo": (photo_path.name, handle, "image/png")},
                        timeout=20,
                    )
                body = response.json()
                if body.get("ok") is True:
                    return DeliveryResult(True, "delivered")
                description = redact_secret(str(body.get("description", "Telegram rejected photo")))
                if "Unauthorized" in description:
                    return DeliveryResult(False, "invalid_credentials", description)
                return DeliveryResult(False, "rejected", description)
            except Exception as exc:
                safe = redact_secret(str(exc))
                if attempt == 2:
                    return DeliveryResult(False, "temporary_failure", safe)
                time.sleep(0.5 * (2**attempt))
        return DeliveryResult(False, "temporary_failure", "unknown failure")

    def discover_chat_id(self) -> int:
        if not self.token:
            raise RuntimeError("Telegram token is not configured.")
        with request.urlopen(self._api("getMe"), timeout=12, context=self._ssl_context()) as response:
            identity = json.loads(response.read().decode("utf-8"))
        username = identity.get("result", {}).get("username")
        if username != self.username:
            raise RuntimeError("Configured Telegram bot username does not match Bot API identity.")
        with request.urlopen(self._api("getUpdates"), timeout=12, context=self._ssl_context()) as response:
            updates = json.loads(response.read().decode("utf-8"))
        for item in reversed(updates.get("result", [])):
            chat = item.get("message", {}).get("chat", {})
            if chat.get("type") == "private" and "id" in chat:
                return int(chat["id"])
        raise RuntimeError("No private chat found. Send a message to @AlisScreenerBot first.")


def local_macos_fallback(summary: str) -> bool:
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{summary}" with title "SwingSuiteScreener"'],
            check=False,
            timeout=5,
            capture_output=True,
        )
        return True
    except Exception:
        return False


def _entry_plan_lines(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    return (
        f"Trigger: {entry.trigger:.2f}\n"
        f"Support: {entry.support:.2f}\n"
        f"Invalidation: {entry.invalidation:.2f}\n"
        f"Target Stock Price: {entry.target_price:.2f}\n"
        f"Research Call Strike: {entry.research_call_strike:.2f}\n"
        f"DTE Window: {entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}\n"
        f"Hold Window: {entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum} days"
    )


def _compact_plan_line(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    bucket = "TW" if candidate.grade.value == "Technical Watch" else candidate.grade.value
    return (
        f"{candidate.symbol} {bucket} | "
        f"Tgt {entry.target_price:.2f} | "
        f"Strike {entry.research_call_strike:.2f} | "
        f"{entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}DTE | "
        f"hold {entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum}d"
    )


def candidate_message(candidate: Candidate, report_path: Path) -> str:
    if candidate.grade.value == "S":
        return (
            "S TIER SETUP\n\n"
            f"Ticker: {candidate.symbol}\n"
            f"Company: {candidate.company}\n"
            f"Current price: {candidate.command.close:.2f}\n\n"
            f"Daily Command: {candidate.command.score}\n"
            f"Daily Momentum: {candidate.daily_momentum.score}\n"
            f"Four Hour Momentum: {candidate.four_hour_momentum.score}\n"
            f"Daily Filter: {'passed' if candidate.four_hour_momentum.daily_filter_passed else 'blocked'}\n\n"
            f"Entry Mode: {candidate.entry_plan.entry_mode}\n"
            f"{_entry_plan_lines(candidate)}\n"
            f"Nearest Resistance: {candidate.entry_plan.nearest_resistance:.2f}\n\n"
            f"Relative Strength: {candidate.command.relative_strength}\n"
            f"Relative Volume: {candidate.command.relative_volume:.2f}\n"
            f"Option Liquidity: {candidate.option_liquidity}\n\n"
            f"Catalyst: {candidate.catalyst.summary}\n"
            f"Earnings: {candidate.catalyst.earnings_date or 'Unknown'}\n"
            f"Status: {candidate.entry_plan.status}\n\n"
            f"Report: {report_path}"
        )
    if candidate.grade.value == "Technical Watch":
        return (
            "TECHNICAL WATCH\n\n"
            f"Ticker: {candidate.symbol}\n"
            f"Current price: {candidate.command.close:.2f}\n\n"
            f"Daily Command: {candidate.command.score}\n"
            f"Daily Momentum: {candidate.daily_momentum.score}\n"
            f"Four Hour Momentum: {candidate.four_hour_momentum.score}\n\n"
            f"{_entry_plan_lines(candidate)}\n\n"
            f"Option Liquidity: {candidate.option_liquidity}\n"
            f"Missing Confirmation: {candidate.missing_confirmation or 'None'}\n"
            "Status: technical watch only; verify live option chain before entry.\n\n"
            f"Report: {report_path}"
        )
    return (
        "A PLUS SETUP\n\n"
        f"Ticker: {candidate.symbol}\n"
        f"Current price: {candidate.command.close:.2f}\n\n"
        f"Daily Command: {candidate.command.score}\n"
        f"Daily Momentum: {candidate.daily_momentum.score}\n"
        f"Four Hour Momentum: {candidate.four_hour_momentum.score}\n\n"
        f"{_entry_plan_lines(candidate)}\n\n"
        f"Missing Confirmation: {candidate.missing_confirmation or 'None'}\n"
        f"Reason It Is Not S Tier: {candidate.not_s_tier_reason or 'N/A'}\n\n"
        f"Report: {report_path}"
    )


def completion_message(result: ScanResult, report_path: Path) -> str:
    if result.s_tier or result.a_plus or result.technical_watch:
        top = (result.s_tier + result.a_plus + result.technical_watch)[0]
        setup_lines = [
            _compact_plan_line(candidate)
            for candidate in (result.s_tier + result.a_plus + result.technical_watch)
        ]
        return (
            f"{result.scan_type.value.replace('_', ' ').upper()} SCAN COMPLETE\n\n"
            f"Market regime: {result.market_regime}\n"
            f"S tier: {len(result.s_tier)}\n"
            f"A plus: {len(result.a_plus)}\n"
            f"Free technical watch: {len(result.technical_watch)}\n"
            f"Securities scanned: {result.universe_count}\n"
            f"Completed: {datetime.now(UTC).isoformat()}\n\n"
            f"Top setup: {top.symbol}\n"
            f"Grade: {top.grade.value}\n"
            f"Trigger: {top.entry_plan.trigger:.2f}\n"
            f"Support: {top.entry_plan.support:.2f}\n"
            f"Target Stock Price: {top.entry_plan.target_price:.2f}\n"
            f"Research Call Strike: {top.entry_plan.research_call_strike:.2f}\n"
            f"DTE Window: {top.entry_plan.preferred_dte_minimum}-{top.entry_plan.preferred_dte_maximum}\n"
            f"Hold Window: {top.entry_plan.intended_hold_days_minimum}-{top.entry_plan.intended_hold_days_maximum} days\n\n"
            "Setups:\n"
            f"{chr(10).join(setup_lines)}\n\n"
            f"Full report: {report_path}"
        )
    return (
        f"{result.scan_type.value.replace('_', ' ').upper()} SCAN COMPLETE\n\n"
        "No S tier or A plus setups qualified today.\n\n"
        "Standards were not lowered.\n\n"
        f"Market regime: {result.market_regime}\n"
        f"Securities scanned: {result.universe_count}\n"
        f"Completed: {datetime.now(UTC).isoformat()}"
    )


def log_delivery(identifier: str, status: str, ticker: str = "", event_type: str = "", error: str = "") -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["discover_chat_id"])
    args = parser.parse_args()
    if args.command == "discover_chat_id":
        notifier = TelegramNotifier()
        try:
            chat_id = notifier.discover_chat_id()
        except Exception as exc:
            print(f"Unable to discover Telegram chat id safely: {redact_secret(str(exc))}")
            return 0
        print(f"Detected private chat id for @{notifier.username}: {chat_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
