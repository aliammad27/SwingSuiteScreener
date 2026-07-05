from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scanner.clocks import format_et
from scanner.config import ROOT
from scanner.models import Candidate, Grade, ScanResult

FIXTURE_LABEL = "SIMULATED FIXTURE OUTPUT — NOT CURRENT MARKET DATA"

MANAGEMENT_FOOTER = (
    "Management: -50% premium hard stop | 2-3 day time stop | sell half at +100% | "
    "exit or roll by 5 DTE | max 5% of account per trade | max 4 concurrent "
    "positions, correlated sector names count as one"
)

STRIKE_VALIDATION_NOTE = (
    "Strike note: research strike only — validate against a 0.25-0.35 absolute "
    "delta band in the broker; the delta band is primary, the computed strike is "
    "a sanity check."
)


def _candidate_block(candidate: Candidate, index: int, include_a_plus: bool = False) -> list[str]:
    command = candidate.command
    daily = candidate.daily_momentum
    four = candidate.four_hour_momentum
    entry = candidate.entry_plan
    lines = [
        f"{index}. {candidate.symbol}",
        "",
        f"Grade: {candidate.grade.value}",
        f"Status: {entry.status}",
        f"Company: {candidate.company}",
        f"Sector: {candidate.sector}",
        f"Benchmark: {candidate.benchmark}",
        f"Current price: {command.close:.2f}",
        f"Daily Command Score: {command.score}",
        f"Daily call bias: {command.call_bias}",
        f"Daily Momentum Score: {daily.score}",
        f"Daily momentum state: {daily.state}",
        f"Four Hour Momentum Score: {four.score}",
        f"Four hour momentum state: {four.state}",
        f"Daily filter: {'passed' if four.daily_filter_passed else 'blocked'}",
        f"Relative strength: {command.relative_strength}",
        f"Relative volume: {command.relative_volume:.2f}",
        f"Monthly anchored VWAP: {command.anchored_vwap:.2f}",
        f"Weekly alignment: {'passed' if command.weekly_alignment else 'blocked'}",
        f"Market structure: {command.structure}",
        "Trend line structure: calculated from confirmed pivots",
        f"Breakout trigger: {entry.trigger:.2f}",
        f"Pullback support: {entry.support:.2f}",
        f"Invalidation: {entry.invalidation:.2f}",
        f"Nearest resistance: {entry.nearest_resistance:.2f}",
        f"Target stock price: {entry.target_price:.2f}",
        f"Target gain from current price: {entry.target_gain_percent:.2f}%",
        f"Entry mode: {entry.entry_mode}",
        f"Entry status: {entry.status}",
        f"Option liquidity: {candidate.option_liquidity}",
        f"Research call strike: {entry.research_call_strike:.2f}",
        STRIKE_VALIDATION_NOTE,
        f"Preferred DTE range: {entry.preferred_dte_minimum}-{entry.preferred_dte_maximum}",
        (
            "Intended hold window: "
            f"{entry.intended_hold_days_minimum}-{entry.intended_hold_days_maximum} days"
        ),
        "Contract note: verify live bid, ask, volume, open interest, IV, and expiration before entry.",
        f"Catalyst: {candidate.catalyst.summary}",
        f"Catalyst source: {candidate.catalyst.source_title} ({candidate.catalyst.source_url})",
        f"Earnings date: {candidate.catalyst.earnings_date or 'Unknown'}",
        f"Event risk: {'major unresolved risk' if candidate.catalyst.major_event_risk else 'none identified'}",
        f"Market regime: {candidate.market_regime}",
        "Why it qualifies: deterministic Command, Momentum, liquidity, and risk gates passed.",
        "What must happen next: user reviews the report and authorizes any trade decision manually.",
        "What invalidates it: support loss, stale data, hostile regime, event risk, or extension.",
        f"Reason it is S tier: {'all S tier requirements passed' if candidate.grade.value == 'S' else 'not S tier'}",
    ]
    if candidate.grade in {Grade.S_TIER, Grade.A_PLUS}:
        lines.append(MANAGEMENT_FOOTER)
    if include_a_plus:
        lines.extend(
            [
                f"Missing confirmation: {candidate.missing_confirmation or 'None'}",
                f"Reason it is not S tier: {candidate.not_s_tier_reason or 'N/A'}",
            ]
        )
    return lines


def result_to_json(result: ScanResult) -> dict[str, Any]:
    return {
        "scan_type": result.scan_type.value,
        "generated_at": result.generated_at.isoformat(),
        "market_data_timestamp": result.market_data_timestamp.isoformat(),
        "market_regime": result.market_regime,
        "universe_count": result.universe_count,
        "deterministic_pass_count": result.deterministic_pass_count,
        "research_count": result.research_count,
        "s_tier": [asdict(c) for c in result.s_tier],
        "a_plus": [asdict(c) for c in result.a_plus],
        "b_tier": [asdict(c) for c in result.b_tier],
        "technical_watch": [asdict(c) for c in result.technical_watch],
        "rejected": [asdict(r) for r in result.rejected],
    }


def write_reports(result: ScanResult) -> tuple[Path, Path]:
    folder = ROOT / "reports" / result.scan_type.value
    folder.mkdir(parents=True, exist_ok=True)
    md_path = folder / "latest.md"
    json_path = folder / "latest.json"
    lines: list[str] = []
    if result.fixture:
        lines.extend([FIXTURE_LABEL, ""])
    lines.extend(
        [
            f"Scan type: {result.scan_type.value}",
            f"Generated at: {format_et(result.generated_at)}",
            f"Market data timestamp: {result.market_data_timestamp.isoformat()}",
            f"Market regime: {result.market_regime}",
            f"Securities scanned: {result.universe_count}",
            f"Passed deterministic filters: {result.deterministic_pass_count}",
            f"Received catalyst review: {result.research_count}",
            f"B tier developing: {len(result.b_tier)}",
            f"Free technical watch: {len(result.technical_watch)}",
            "",
            "S TIER",
            "",
        ]
    )
    if result.s_tier:
        for idx, candidate in enumerate(result.s_tier, 1):
            lines.extend(_candidate_block(candidate, idx))
            lines.append("")
    lines.extend(["A PLUS TIER", ""])
    if result.a_plus:
        for idx, candidate in enumerate(result.a_plus, 1):
            lines.extend(_candidate_block(candidate, idx, include_a_plus=True))
            lines.append("")
    lines.extend(["B TIER — DEVELOPING SETUPS", ""])
    if result.b_tier:
        lines.extend(
            [
                "These setups pass basic technical structure but do not yet meet A+ thresholds. "
                "Monitor for score improvement before committing capital.",
                "",
            ]
        )
        for idx, candidate in enumerate(result.b_tier, 1):
            lines.extend(_candidate_block(candidate, idx, include_a_plus=True))
            lines.append("")
    lines.extend(["FREE TECHNICAL WATCH", ""])
    if result.technical_watch:
        lines.extend(
            [
                "These are not trade-ready options setups. They passed the technical gates, "
                "but current tradable option liquidity is unavailable or only indicative.",
                "",
            ]
        )
        for idx, candidate in enumerate(result.technical_watch, 1):
            lines.extend(_candidate_block(candidate, idx, include_a_plus=True))
            lines.append("")
    if not result.s_tier and not result.a_plus and not result.b_tier and not result.technical_watch:
        lines.extend(
            ["No S tier or A plus setups qualified today.", "", "Standards were not lowered.", ""]
        )
    lines.extend(
        [
            "NO TRADE CONDITIONS",
            "",
            "1. Gap exceeds one ATR above the trigger.",
            "2. Support fails before entry.",
            "3. Option spread exceeds the configured limit.",
            "4. Option data becomes stale.",
            "5. New earnings or event risk appears.",
            "6. Market regime turns hostile.",
            "7. Price becomes extended.",
            "8. Catalyst is contradicted.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps(result_to_json(result), indent=2, default=str), encoding="utf-8"
    )
    return md_path, json_path
