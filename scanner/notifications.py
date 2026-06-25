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

from scanner.clocks import NY
from scanner.config import ROOT, load_local_env
from scanner.models import Candidate, PutCandidate, PutScanResult, ScanResult

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
                description = redact_secret(
                    str(body.get("description", "Telegram rejected message"))
                )
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
        with request.urlopen(
            self._api("getMe"), timeout=12, context=self._ssl_context()
        ) as response:
            identity = json.loads(response.read().decode("utf-8"))
        username = identity.get("result", {}).get("username")
        if username != self.username:
            raise RuntimeError("Configured Telegram bot username does not match Bot API identity.")
        with request.urlopen(
            self._api("getUpdates"), timeout=12, context=self._ssl_context()
        ) as response:
            updates = json.loads(response.read().decode("utf-8"))
        for item in reversed(updates.get("result", [])):
            chat = item.get("message", {}).get("chat", {})
            if chat.get("type") == "private" and "id" in chat:
                return int(chat["id"])
        raise RuntimeError("No private chat found. Send a message to @AlisScreenerBot first.")


def local_macos_fallback(summary: str) -> bool:
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{summary}" with title "SwingSuiteScreener"',
            ],
            check=False,
            timeout=5,
            capture_output=True,
        )
        return True
    except Exception:
        return False


def _dist_to_trigger(candidate: Candidate) -> str:
    price = candidate.command.close
    trigger = candidate.entry_plan.trigger
    if price <= 0:
        return ""
    pct = (trigger - price) / price * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def _compact_plan_line(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    price = candidate.command.close
    bucket = "TW" if candidate.grade.value == "Technical Watch" else candidate.grade.value
    dist = _dist_to_trigger(candidate)
    dist_str = f" ({dist})" if dist else ""
    return (
        f"{candidate.symbol} {bucket} | "
        f"${price:.2f} → ${entry.trigger:.2f}{dist_str} | "
        f"Sup ${entry.support:.2f} | "
        f"Tgt ${entry.target_price:.2f} | "
        f"{entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}DTE | "
        f"{entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum}d hold"
    )


def _levels_line(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    price = candidate.command.close
    dist = _dist_to_trigger(candidate)
    dist_str = f" ({dist})" if dist else ""
    return (
        f"${price:.2f} → ${entry.trigger:.2f}{dist_str} | "
        f"Sup ${entry.support:.2f} | "
        f"Res ${entry.nearest_resistance:.2f} | "
        f"Tgt ${entry.target_price:.2f}"
    )


def _scores_line(candidate: Candidate) -> str:
    cmd = candidate.command
    daily = candidate.daily_momentum
    four = candidate.four_hour_momentum
    return (
        f"C{cmd.score} | D{daily.score} | 4H{four.score} | "
        f"RS {cmd.relative_strength} | Liquidity {candidate.option_liquidity}"
    )


def _option_line(candidate: Candidate) -> str:
    entry = candidate.entry_plan
    return (
        f"Strike ${entry.research_call_strike:.2f} | "
        f"{entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}DTE | "
        f"{entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum}d hold"
    )


def candidate_message(candidate: Candidate, report_path: Path) -> str:
    grade = candidate.grade.value
    if grade == "S":
        return (
            f"S TIER SETUP — {candidate.symbol}\n\n"
            f"{_levels_line(candidate)}\n"
            f"{_scores_line(candidate)}\n"
            f"{_option_line(candidate)}\n"
            f"Earnings: {candidate.catalyst.earnings_date or 'Unknown'} | "
            f"Catalyst: {candidate.catalyst.summary[:60]}\n\n"
            f"Report: {report_path}"
        )
    if grade == "A+":
        return (
            f"A PLUS SETUP — {candidate.symbol}\n\n"
            f"{_levels_line(candidate)}\n"
            f"{_scores_line(candidate)}\n"
            f"{_option_line(candidate)}\n"
            f"Missing: {candidate.missing_confirmation or 'None'}\n\n"
            f"Report: {report_path}"
        )
    if grade == "B":
        return (
            f"B TIER SETUP — {candidate.symbol}\n\n"
            f"{_levels_line(candidate)}\n"
            f"{_scores_line(candidate)}\n"
            f"{_option_line(candidate)}\n"
            "Status: Developing — verify levels before entry\n\n"
            f"Report: {report_path}"
        )
    return (
        f"TECHNICAL WATCH — {candidate.symbol}\n\n"
        f"{_levels_line(candidate)}\n"
        f"{_scores_line(candidate)}\n"
        f"{_option_line(candidate)}\n"
        f"Option Liquidity: {candidate.option_liquidity} — verify live chain before entry\n\n"
        f"Report: {report_path}"
    )


def completion_message(result: ScanResult, report_path: Path) -> str:
    now_et = datetime.now(NY).strftime("%-I:%M %p ET")
    title = result.scan_type.value.replace("_", " ").upper()
    all_setups = result.s_tier + result.a_plus + result.b_tier + result.technical_watch
    if all_setups:
        count_line = (
            f"S: {len(result.s_tier)} | A+: {len(result.a_plus)} | "
            f"B: {len(result.b_tier)} | TW: {len(result.technical_watch)}"
        )
        setup_lines = [_compact_plan_line(c) for c in all_setups]
        return (
            f"{title} SCAN COMPLETE\n"
            f"Market: {result.market_regime} | Scanned: {result.universe_count} | {now_et}\n\n"
            f"{count_line}\n\n"
            f"{chr(10).join(setup_lines)}\n\n"
            f"Full report: {report_path}"
        )
    return (
        f"{title} SCAN COMPLETE\n"
        f"Market: {result.market_regime} | Scanned: {result.universe_count} | {now_et}\n\n"
        "No setups qualified. Standards not lowered."
    )


def _put_dist_to_trigger(candidate: PutCandidate) -> str:
    price = candidate.command.close
    trigger = candidate.entry_plan.trigger
    if price <= 0:
        return ""
    pct = (price - trigger) / price * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def _put_compact_plan_line(candidate: PutCandidate) -> str:
    entry = candidate.entry_plan
    price = candidate.command.close
    bucket = "TW" if candidate.grade.value == "Technical Watch" else candidate.grade.value
    dist = _put_dist_to_trigger(candidate)
    dist_str = f" ({dist} to breakdown)" if dist else ""
    return (
        f"{candidate.symbol} {bucket}P | "
        f"${price:.2f} ↓ ${entry.trigger:.2f}{dist_str} | "
        f"Inv ${entry.invalidation:.2f} | "
        f"Tgt ${entry.target_price:.2f} | "
        f"{entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}DTE | "
        f"{entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum}d hold"
    )


def _put_levels_line(candidate: PutCandidate) -> str:
    entry = candidate.entry_plan
    price = candidate.command.close
    dist = _put_dist_to_trigger(candidate)
    dist_str = f" ({dist})" if dist else ""
    return (
        f"${price:.2f} ↓ ${entry.trigger:.2f}{dist_str} | "
        f"Res ${entry.resistance:.2f} | "
        f"Inv ${entry.invalidation:.2f} | "
        f"Tgt ${entry.target_price:.2f}"
    )


def _put_scores_line(candidate: PutCandidate) -> str:
    cmd = candidate.command
    daily = candidate.daily_momentum
    four = candidate.four_hour_momentum
    return (
        f"PC{cmd.score} | D{daily.score} | 4H{four.score} | "
        f"RW {cmd.relative_weakness} | Liquidity {candidate.option_liquidity}"
    )


def _put_option_line(candidate: PutCandidate) -> str:
    entry = candidate.entry_plan
    return (
        f"Strike ${entry.research_put_strike:.2f} | "
        f"{entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}DTE | "
        f"{entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum}d hold"
    )


def put_candidate_message(candidate: PutCandidate, report_path: Path) -> str:
    grade = candidate.grade.value
    if grade == "S":
        return (
            f"S-PUT TIER SETUP — {candidate.symbol}\n\n"
            f"{_put_levels_line(candidate)}\n"
            f"{_put_scores_line(candidate)}\n"
            f"{_put_option_line(candidate)}\n"
            f"Earnings: {candidate.catalyst.earnings_date or 'Unknown'} | "
            f"Catalyst: {candidate.catalyst.summary[:60]}\n\n"
            f"Report: {report_path}"
        )
    if grade == "A+":
        return (
            f"A-PLUS PUT SETUP — {candidate.symbol}\n\n"
            f"{_put_levels_line(candidate)}\n"
            f"{_put_scores_line(candidate)}\n"
            f"{_put_option_line(candidate)}\n"
            f"Missing: {candidate.missing_confirmation or 'None'}\n\n"
            f"Report: {report_path}"
        )
    if grade == "B":
        return (
            f"B-PUT TIER SETUP — {candidate.symbol}\n\n"
            f"{_put_levels_line(candidate)}\n"
            f"{_put_scores_line(candidate)}\n"
            f"{_put_option_line(candidate)}\n"
            "Status: Developing put — verify levels before entry\n\n"
            f"Report: {report_path}"
        )
    return (
        f"PUT TECHNICAL WATCH — {candidate.symbol}\n\n"
        f"{_put_levels_line(candidate)}\n"
        f"{_put_scores_line(candidate)}\n"
        f"{_put_option_line(candidate)}\n"
        f"Option Liquidity: {candidate.option_liquidity} — verify live chain before entry\n\n"
        f"Report: {report_path}"
    )


def put_completion_message(result: PutScanResult, report_path: Path) -> str:
    now_et = datetime.now(NY).strftime("%-I:%M %p ET")
    title = result.scan_type.value.replace("_", " ").upper()
    all_setups = result.s_tier + result.a_plus + result.b_tier + result.technical_watch
    regime_note = (
        "Hostile (put-supportive)"
        if result.market_regime == "Hostile"
        else result.market_regime
    )
    if all_setups:
        count_line = (
            f"S: {len(result.s_tier)} | A+: {len(result.a_plus)} | "
            f"B: {len(result.b_tier)} | TW: {len(result.technical_watch)}"
        )
        setup_lines = [_put_compact_plan_line(c) for c in all_setups]
        return (
            f"{title} SCAN COMPLETE\n"
            f"Market: {regime_note} | Scanned: {result.universe_count} | {now_et}\n\n"
            f"{count_line}\n\n"
            f"{chr(10).join(setup_lines)}\n\n"
            f"Full report: {report_path}"
        )
    return (
        f"{title} SCAN COMPLETE\n"
        f"Market: {regime_note} | Scanned: {result.universe_count} | {now_et}\n\n"
        "No put setups qualified. Standards not lowered."
    )


def log_delivery(
    identifier: str, status: str, ticker: str = "", event_type: str = "", error: str = ""
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
