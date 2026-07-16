from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scanner.clocks import format_et
from scanner.config import ROOT
from scanner.dashboard import write_dashboard
from scanner.models import Candidate, ScanResult
from scanner.strategy_profile import PROFILE

FIXTURE_LABEL = "SIMULATED FIXTURE OUTPUT - NOT CURRENT MARKET DATA"


def _contract_lines(candidate: Candidate) -> list[str]:
    selection = candidate.contracts
    primary = selection.primary
    if primary is None:
        reasons = ", ".join(selection.rejection_reasons) or "chain unavailable"
        return [
            f"Contract feed: {selection.feed}",
            f"Contract status: broker verification required ({reasons})",
        ]
    lines = [
        f"Contract feed: {selection.feed}",
        f"Contract score: {selection.score}",
        f"Re-quoted finalists: {selection.requoted_count}",
        f"Primary call: {primary.contract_symbol}",
        f"Expiration / strike: {primary.expiration_date.isoformat()} / ${primary.strike:.2f}",
        f"DTE / delta: {primary.dte} / {primary.delta:.2f}",
        f"Bid / ask / spread: ${primary.bid:.2f} / ${primary.ask:.2f} / {primary.spread_percent:.1f}%",
        f"OI / volume: {primary.open_interest:,} / {primary.volume:,}",
        f"Bid / ask size: {primary.bid_size:,} / {primary.ask_size:,}",
        f"IV / gamma / theta / vega: {primary.implied_volatility if primary.implied_volatility is not None else 'N/A'} / "
        f"{primary.gamma if primary.gamma is not None else 'N/A'} / "
        f"{primary.theta if primary.theta is not None else 'N/A'} / "
        f"{primary.vega if primary.vega is not None else 'N/A'}",
        f"Maximum premium at risk per contract at ask: ${primary.maximum_loss_per_contract:,.0f}",
    ]
    if selection.iv_to_realized_volatility is not None:
        lines.append(f"IV / 20-session realized volatility: {selection.iv_to_realized_volatility:.2f}x")
    if selection.primary_risk is not None:
        risk = selection.primary_risk
        lines.extend(
            [
                f"Theta / ask: {_fmt_optional(risk.theta_ask_percent, '%')}",
                f"Extrinsic value / ask: {_fmt_optional(risk.extrinsic_value_percent, '%')}",
                f"Quote age / change: {risk.quote_age_minutes:.2f} minutes / "
                f"{_fmt_optional(risk.quote_change_percent, '%')}",
                f"Depth / expiration style: {risk.depth_contracts:,} / {risk.expiration_style}",
            ]
        )
    if selection.alternatives:
        lines.append(
            "Alternatives: " + ", ".join(item.contract_symbol for item in selection.alternatives)
        )
    return lines


def _fmt_optional(value: float | None, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value:.2f}{suffix}"


def _candidate_block(candidate: Candidate, index: int) -> list[str]:
    scores = candidate.scores
    plan = candidate.entry_plan
    leadership = "N/A" if scores.leadership is None else str(scores.leadership)
    lines = [
        f"{index}. {candidate.symbol} - {candidate.state.label}",
        "",
        f"Lane: {candidate.lane.label}",
        f"Sector / peer: {candidate.sector} / {candidate.peer_etf}",
        f"Market: {candidate.market.regime} ({candidate.market.score})",
        f"Pattern: {candidate.pattern.pattern_type.replace('_', ' ')} / {candidate.pattern.status.value} / quality {candidate.pattern.quality}",
        f"Evidence: Trend {scores.trend} | Leadership {leadership} | Setup {scores.setup} | Timing {scores.timing} | Market {scores.market} | Contract {scores.contract} | Risk {scores.risk}",
        f"Hourly timing: {candidate.timing.state}; completed {candidate.timing.completed_at.isoformat()}",
        f"Hourly EMA9 / EMA21 / VWAP: ${candidate.timing.ema9:.2f} / ${candidate.timing.ema21:.2f} / ${candidate.timing.session_vwap:.2f}",
        f"Hourly RSI / MACD histogram / relative volume: {candidate.timing.rsi:.1f} / {candidate.timing.macd_histogram:.3f} / {candidate.timing.relative_volume:.2f}x",
        f"Price / trigger: ${candidate.trend.close:.2f} / ${plan.trigger:.2f}",
        f"Support / structural invalidation: ${plan.support:.2f} / ${plan.invalidation:.2f}",
        f"Tactical warning / failure: ${plan.tactical_warning:.2f} / ${plan.tactical_failure:.2f}",
        "Nearest confirmed daily pivot: "
        + (f"${plan.resistance_level:.2f}" if plan.resistance_level is not None else "None confirmed"),
        f"2R planning objective / selected target: ${plan.planning_objective_2r:.2f} / ${plan.target_price:.2f}",
        f"Target basis: {plan.target_basis}",
        f"Reward-to-risk: {plan.reward_to_risk:.2f}" if plan.reward_to_risk is not None else "Reward-to-risk: N/A",
        f"Trigger age: {candidate.pattern.age_bars} bars",
        f"Entry status: {plan.status}",
        f"Thesis window: {plan.intended_hold_sessions[0]}-{plan.intended_hold_sessions[1]} sessions; reassess after {plan.no_progress_sessions} sessions without progress; requalify by {plan.requalify_dte} DTE",
        f"Event status: {candidate.event_risk.status.value} / {candidate.event_risk.summary}",
        f"Earnings date: {candidate.event_risk.earnings_date.isoformat() if candidate.event_risk.earnings_date else 'Unknown'}",
        f"Data trust: {'trusted' if candidate.data_trust.trustworthy else 'verification required'} / "
        + (", ".join(candidate.data_trust.reasons) or "SIP, OPRA, event, and quote checks passed"),
    ]
    lines.extend(_contract_lines(candidate))
    if candidate.reasons:
        lines.append("Pending checks: " + ", ".join(candidate.reasons))
    lines.extend(
        [
            "Decision boundary: manual review only; no order is authorized by this report.",
            "Risk boundary: a long call can lose the full premium paid.",
        ]
    )
    return lines


def result_to_json(result: ScanResult) -> dict[str, Any]:
    return {
        "schema_version": PROFILE.schema_version,
        "strategy_profile": PROFILE.name,
        "scan_type": result.scan_type.value,
        "generated_at": result.generated_at.isoformat(),
        "market_data_timestamp": result.market_data_timestamp.isoformat(),
        "market": asdict(result.market),
        "universe_count": result.universe_count,
        "evaluated_count": result.evaluated_count,
        "ready": [asdict(candidate) for candidate in result.ready],
        "ready_verify": [asdict(candidate) for candidate in result.ready_verify],
        "developing": [asdict(candidate) for candidate in result.developing],
        "verify_contract": [asdict(candidate) for candidate in result.verify_contract],
        "rejected": [asdict(record) for record in result.rejected],
        "fixture": result.fixture,
        "validation_state": result.validation_state,
    }


def write_reports(result: ScanResult) -> tuple[Path, Path]:
    folder = ROOT / "reports" / result.scan_type.value
    folder.mkdir(parents=True, exist_ok=True)
    markdown_path = folder / "latest.md"
    json_path = folder / "latest.json"
    lines: list[str] = []
    if result.fixture:
        lines.extend([FIXTURE_LABEL, ""])
    lines.extend(
        [
            f"# {PROFILE.name} - {result.scan_type.value.replace('_', ' ').title()}",
            "",
            f"Generated: {format_et(result.generated_at)}",
            f"Market data: {result.market_data_timestamp.isoformat()}",
            f"Market regime: {result.market.regime} ({result.market.score}/100)",
            f"Validation state: {result.validation_state}",
            f"Universe breadth: {result.market.breadth_above_sma50:.1f}% above SMA50; {result.market.breadth_above_ema21:.1f}% above EMA21",
            f"Evaluated: {result.evaluated_count} of {result.universe_count}",
            "",
        ]
    )
    sections = (
        ("READY", result.ready),
        ("READY - VERIFY", result.ready_verify),
        ("VERIFY CONTRACT", result.verify_contract),
        ("DEVELOPING", result.developing),
    )
    for heading, candidates in sections:
        lines.extend([f"## {heading}", ""])
        if not candidates:
            lines.extend(["None.", ""])
            continue
        for index, candidate in enumerate(candidates, 1):
            lines.extend(_candidate_block(candidate, index))
            lines.append("")
    lines.extend(
        [
            "## Research Standard",
            "",
            "Outcomes are recorded as confirmed, invalidated, or unresolved. No state implies a guaranteed result.",
            "V5 remains research-gated. Even complete SIP/OPRA candidates remain Ready - Verify until promotion gates pass.",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps(result_to_json(result), indent=2, default=str), encoding="utf-8"
    )
    write_dashboard(result, folder)
    return markdown_path, json_path
