from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib import parse, request

from scanner.charts import render_candidate_summary
from scanner.clocks import NY
from scanner.config import ROOT, load_config, load_local_env
from scanner.models import (
    Candidate,
    ContractMode,
    OpportunityTier,
    ScanResult,
    ScanType,
)
from scanner.premium_scenarios import premium_target_scenarios
from scanner.state import NotificationState, completion_snapshot, should_send_completion
from scanner.storage.factory import configured_storage
from scanner.strategy_profile import PROFILE

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
                description = redact_secret(
                    str(body.get("description", "Telegram rejected message"))
                )
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
        f"D{contract.delta:.2f} | {contract.dte}DTE | "
        f"{candidate.contract_mode.label} | {contract.spread_percent:.1f}% spread"
    )


def _economics_lines(candidate: Candidate) -> list[str]:
    economics = candidate.contract_economics
    if economics is None:
        return []
    expected = (
        f"${economics.expected_move:.2f}"
        if economics.expected_move is not None
        else "unavailable"
    )
    ratio = (
        f"{economics.target_to_expected_move:.2f}x"
        if economics.target_to_expected_move is not None
        else "unavailable"
    )
    theta = (
        f"${economics.theta_cost:.2f}, {economics.theta_cost_percent:.1f}% of ask"
        if economics.theta_cost is not None
        and economics.theta_cost_percent is not None
        else "unavailable"
    )
    lines = [
        f"Economics: expected move {expected} "
        f"({'ATM straddle' if economics.expected_move_source == 'atm_straddle_mid' else 'call IV'}) | "
        f"target/expected {ratio} | {economics.target_feasibility}",
        f"Call breakeven ${economics.long_call_breakeven:.2f} "
        f"({economics.breakeven_move_percent:+.1f}%) | "
        f"{economics.theta_cost_sessions} session theta {theta}",
    ]
    if (
        economics.spread_short_strike is not None
        and economics.spread_debit is not None
        and economics.spread_max_profit is not None
    ):
        lines.append(
            f"Debit spread comparison: short ${economics.spread_short_strike:g} | "
            f"debit ${economics.spread_debit:.2f} | "
            f"max profit ${economics.spread_max_profit:.2f}"
        )
    lines.append(
        f"Preferred structure: {economics.recommended_structure.replace('_', ' ')}"
    )
    return lines


def _short_target_basis(value: str) -> str:
    return "confirmed pivot" if value == "nearest confirmed daily pivot" else "2R plan"


def _target_lines(candidate: Candidate, *, show_premium_scenarios: bool) -> list[str]:
    lines: list[str] = []
    for scenario in premium_target_scenarios(candidate):
        prefix = (
            f"{scenario.target_label} ${scenario.underlying_target:.2f} "
            f"({_short_target_basis(scenario.target_basis)})"
        )
        if not show_premium_scenarios:
            lines.append(prefix)
        elif scenario.available:
            lines.append(
                f"{prefix} | est call ${scenario.premium_low:.2f}-${scenario.premium_high:.2f} "
                f"(0-{scenario.modeled_sessions[1]} sessions)"
            )
        else:
            lines.append(f"{prefix} | {scenario.unavailable_reason}")
    return lines


def candidate_caption(
    candidate: Candidate,
    *,
    show_premium_scenarios: bool = True,
) -> str:
    entry = candidate.entry_plan
    contract = candidate.contracts.primary
    lines = [
        f"{candidate.symbol} | {candidate.opportunity_tier.label} | "
        f"{candidate.lane.label} | {candidate.state.label}",
        f"{candidate.pattern.pattern_type.replace('_', ' ')} / "
        f"{candidate.pattern.status.value} / age {candidate.pattern.age_bars}",
        f"Underlying ${candidate.trend.close:.2f} | trigger ${entry.trigger:.2f}",
    ]
    if contract is None:
        lines.append("Call: live OPRA verification required")
    else:
        risk = candidate.contracts.primary_risk
        lines.extend(
            [
                f"Call {contract.expiration_date.strftime('%b %d')} ${contract.strike:g} | "
                f"{contract.dte}DTE | delta {contract.delta:.2f} | "
                f"{candidate.contract_mode.label}",
                f"Quote ${contract.bid:.2f}/${contract.ask:.2f} | "
                f"{contract.spread_percent:.1f}% | OI {contract.open_interest:,} | "
                f"Vol {contract.volume:,}",
            ]
        )
        if risk is not None:
            lines.append(
                f"Feed {candidate.contracts.feed.upper()} | quote {risk.quote_age_minutes:.1f}m | "
                f"{'stable' if risk.quote_stable else 'unstable'}"
            )
        if candidate.contracts.alternatives:
            alternatives = ", ".join(
                f"{item.expiration_date.strftime('%b %d')} ${item.strike:g}"
                for item in candidate.contracts.alternatives[:2]
            )
            lines.append(f"Alternatives: {alternatives}")
        lines.extend(_economics_lines(candidate))
    if candidate.catalyst is not None:
        lines.append(
            f"Catalyst style: {candidate.catalyst.kind.replace('_', ' ')} | "
            f"{candidate.catalyst.gap_atr:.2f} ATR gap | "
            f"{candidate.catalyst.relative_volume:.2f}x volume | event unverified"
        )
    visible_reasons = tuple(
        reason for reason in candidate.reasons if reason != "asymmetric_research_only"
    )
    if visible_reasons:
        lines.append(
            "Why not core: "
            + ", ".join(_reason_label(reason) for reason in visible_reasons[:3])
        )
    lines.extend(_target_lines(candidate, show_premium_scenarios=show_premium_scenarios))
    aggressive = candidate.contract_mode == ContractMode.AGGRESSIVE_WEEKLY
    hold = (
        PROFILE.aggressive_weekly.intended_hold_sessions
        if aggressive
        else entry.intended_hold_sessions
    )
    requalify_dte = (
        PROFILE.aggressive_weekly.requalify_dte
        if aggressive
        else entry.requalify_dte
    )
    no_progress = (
        PROFILE.aggressive_weekly.no_progress_sessions
        if aggressive
        else entry.no_progress_sessions
    )
    lines.extend(
        [
            f"Risk: tactical failure ${entry.tactical_failure:.2f} | "
            f"structural ${entry.invalidation:.2f}",
            f"Hold {hold[0]}-{hold[1]} sessions | no-progress review "
            f"{no_progress} session{'s' if no_progress != 1 else ''} | "
            f"requalify {requalify_dte}DTE",
            "Exit boundary: completed hourly close below tactical failure; "
            "never average down.",
            f"Event {candidate.event_risk.status.value} | data "
            f"{'trusted' if candidate.data_trust.trustworthy else 'verify'}",
        ]
    )
    if show_premium_scenarios and any(
        scenario.available for scenario in premium_target_scenarios(candidate)
    ):
        lines.append("Premium scenarios: quote-anchored Greeks, stable IV; not forecasts.")
    lines.append("Manual research only. A long call can lose the full premium.")
    return "\n".join(lines)[:1024]


def _actionable_candidates(result: ScanResult) -> tuple[Candidate, ...]:
    return result.ready + result.ready_verify + result.verify_contract


def _card_candidates(result: ScanResult) -> tuple[Candidate, ...]:
    asymmetric = tuple(
        candidate
        for candidate in result.developing
        if candidate.opportunity_tier == OpportunityTier.ASYMMETRIC
        and candidate.contracts.primary is not None
    )
    return _actionable_candidates(result) + asymmetric


def _reason_label(reason: str) -> str:
    labels = {
        "hostile_market_regime": "market regime",
        "hourly_timing_not_confirmed": "hourly confirmation",
        "timing_below_ready_threshold": "hourly timing",
        "market_below_ready_threshold": "market score",
        "risk_below_ready_threshold": "risk geometry",
        "trend_below_ready_threshold": "trend score",
        "setup_below_ready_threshold": "setup quality",
        "leadership_below_ready_threshold": "relative strength",
        "pattern_not_ready": "pattern trigger",
        "event_data_unavailable": "event data",
        "option_chain_unavailable": "option chain",
        "option_requote_unavailable": "option quote",
        "trade_economics_review_only": "trade economics",
    }
    return labels.get(reason, reason.replace("_", " "))


def _top_rejection_summary(result: ScanResult, maximum: int = 3) -> str:
    counts = Counter(
        reason
        for rejected in result.rejected
        for reason in rejected.reason_codes
    )
    return ", ".join(
        f"{_reason_label(reason)} {count}"
        for reason, count in counts.most_common(maximum)
    )


def completion_message(result: ScanResult, report_path: Path) -> str:
    now_et = result.generated_at.astimezone(NY).strftime("%-I:%M %p ET")
    candidates = result.candidates
    fixture_label = (
        "SIMULATED FIXTURE - NOT CURRENT MARKET DATA\n" if result.fixture else ""
    )
    header = fixture_label + (
        f"{result.scan_type.value.replace('_', ' ').upper()} - BULLISH WEEKLY V5\n"
        f"Market {result.market.regime} {result.market.score}/100 | "
        f"Breadth {result.market.breadth_above_sma50:.0f}% >50D / "
        f"{result.market.breadth_above_ema21:.0f}% >21D | {now_et}\n\n"
        f"Ready {len(result.ready)} | Ready-check {len(result.ready_verify)} | "
        f"Verify {len(result.verify_contract)} | Watchlist {len(result.developing)}\n"
        f"Coverage {result.evaluated_count}/{result.universe_count} | "
        f"Rejected {len(result.rejected)}"
    )
    if not candidates:
        blockers = _top_rejection_summary(result)
        detail = f"\nTop blockers: {blockers}" if blockers else ""
        return (
            header
            + "\n\nNo bullish setup is ready for review. Cash is a valid state."
            + detail
        )
    configured = load_config("notifications")
    maximum_summary_candidates = max(
        int(configured.get("maximum_candidates_per_message", 5)), 0
    )
    include_developing = bool(configured.get("include_developing_watchlist", True))
    lines: list[str] = [header, ""]
    for candidate in _actionable_candidates(result)[:maximum_summary_candidates]:
        lines.extend(
            [
                f"{candidate.symbol} | {candidate.opportunity_tier.label} | "
                f"{candidate.lane.label} | {candidate.state.label}",
                f"{candidate.pattern.pattern_type.replace('_', ' ')} | "
                f"${candidate.trend.close:.2f} -> trigger ${candidate.entry_plan.trigger:.2f}",
                _contract_line(candidate),
                "",
            ]
        )
    if include_developing and result.developing:
        lines.append("WATCHLIST - NOT ENTRY READY")
        for candidate in result.developing[:maximum_summary_candidates]:
            leadership = (
                "-"
                if candidate.scores.leadership is None
                else str(candidate.scores.leadership)
            )
            blockers = ", ".join(_reason_label(reason) for reason in candidate.reasons[:3])
            lines.extend(
                [
                    f"{candidate.symbol} | "
                    f"{candidate.opportunity_tier.label} | "
                    f"{candidate.lane.label} | "
                    f"{candidate.pattern.pattern_type.replace('_', ' ')} | "
                    f"${candidate.trend.close:.2f} -> ${candidate.entry_plan.trigger:.2f}",
                    f"T{candidate.scores.trend} L{leadership} "
                    f"S{candidate.scores.setup} H{candidate.scores.timing} | "
                    f"Needs: {blockers}",
                ]
            )
            lines.extend(_economics_lines(candidate)[:1])
        lines.append("")
    rejection_summary = _top_rejection_summary(result)
    if rejection_summary:
        lines.extend([f"Top scan blockers: {rejection_summary}", ""])
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


def notify_scan(
    result: ScanResult,
    report_path: Path,
    *,
    fixture: bool,
) -> DeliveryResult:
    message = completion_message(result, report_path)
    configured = load_config("notifications")
    maximum_cards = max(int(configured.get("maximum_candidate_cards", 5)), 0)
    show_scenarios = bool(configured.get("show_premium_scenarios", True))
    card_candidates = _card_candidates(result)[:maximum_cards]
    if fixture:
        print(message)
        for candidate in card_candidates:
            print("\n--- TELEGRAM RESEARCH CARD ---\n")
            print(candidate_caption(candidate, show_premium_scenarios=show_scenarios))
        return DeliveryResult(True, "fixture_preview")
    notifier = TelegramNotifier()
    if not notifier.available():
        delivery = notifier.send(message, silent=result.scan_type != ScanType.POST_CLOSE)
        log_delivery(
            "digest", delivery.status, event_type="digest", error=delivery.safe_error or ""
        )
        return delivery
    state = NotificationState(configured_storage())
    snapshot = completion_snapshot(result)
    only_on_change = result.scan_type in {ScanType.PREMARKET, ScanType.INTRADAY}
    if only_on_change:
        setting = configured.get(
            "send_premarket_only_on_change"
            if result.scan_type == ScanType.PREMARKET
            else "send_intraday_only_on_change",
            True,
        )
        only_on_change = bool(setting)
    previous = state.last_completion_snapshot(result.scan_type.value)
    if not should_send_completion(previous, snapshot, only_on_change):
        log_delivery("digest", "suppressed_unchanged", event_type="digest")
        return DeliveryResult(True, "suppressed_unchanged")
    delivery = notifier.send(message, silent=result.scan_type != ScanType.POST_CLOSE)
    log_delivery("digest", delivery.status, event_type="digest", error=delivery.safe_error or "")
    if not delivery.delivered:
        return delivery
    state.record_completion_snapshot(result.scan_type.value, snapshot)
    for candidate in card_candidates:
        caption = candidate_caption(candidate, show_premium_scenarios=show_scenarios)
        try:
            chart_path = render_candidate_summary(candidate)
            photo = notifier.send_photo(chart_path, caption)
        except Exception as exc:
            photo = DeliveryResult(False, "chart_failure", redact_secret(str(exc)))
        log_delivery(
            f"chart_{candidate.symbol}",
            photo.status,
            ticker=candidate.symbol,
            event_type="candidate_chart",
            error=photo.safe_error or "",
        )
        if photo.delivered:
            continue
        fallback = notifier.send(caption, silent=result.scan_type != ScanType.POST_CLOSE)
        log_delivery(
            f"card_{candidate.symbol}",
            fallback.status,
            ticker=candidate.symbol,
            event_type="candidate_text_fallback",
            error=fallback.safe_error or "",
        )
    return delivery


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
