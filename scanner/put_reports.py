from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scanner.clocks import format_et
from scanner.config import ROOT
from scanner.models import PutCandidate, PutScanResult

FIXTURE_LABEL = "SIMULATED FIXTURE OUTPUT — NOT CURRENT MARKET DATA"


def _put_candidate_block(
    candidate: PutCandidate, index: int, include_detail: bool = False
) -> list[str]:
    command = candidate.command
    daily = candidate.daily_momentum
    four = candidate.four_hour_momentum
    entry = candidate.entry_plan
    lines = [
        f"{index}. {candidate.symbol}",
        "",
        f"Grade: {candidate.grade.value} (Put)",
        f"Status: {entry.status}",
        f"Company: {candidate.company}",
        f"Sector: {candidate.sector}",
        f"Benchmark: {candidate.benchmark}",
        f"Current price: {command.close:.2f}",
        f"Put Command Score: {command.score}",
        f"Put bias: {command.put_bias}",
        f"Daily Momentum Score: {daily.score}",
        f"Daily momentum state: {daily.state}",
        f"Four Hour Momentum Score: {four.score}",
        f"Four hour momentum state: {four.state}",
        f"Daily bearish filter: {'passed' if four.daily_filter_passed else 'blocked'}",
        f"Relative weakness: {command.relative_weakness}",
        f"Relative volume: {command.relative_volume:.2f}",
        f"Monthly anchored VWAP: {command.anchored_vwap:.2f}",
        f"Weekly bearish alignment: {'passed' if command.weekly_alignment else 'blocked'}",
        f"Market structure: {command.structure}",
        "Trend line structure: calculated from confirmed pivots",
        f"Breakdown trigger: {entry.trigger:.2f}",
        f"Overhead resistance: {entry.resistance:.2f}",
        f"Invalidation: {entry.invalidation:.2f}",
        f"Downside target: {entry.target_price:.2f}",
        f"Target downside gain: {entry.target_gain_percent:.2f}%",
        f"Entry mode: {entry.entry_mode}",
        f"Entry status: {entry.status}",
        f"Option liquidity: {candidate.option_liquidity}",
        f"Research put strike: {entry.research_put_strike:.2f}",
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
        f"Market regime: {candidate.market_regime} (put note: Hostile = put-supportive)",
        "Why it qualifies: deterministic Put Command, Momentum, liquidity, and risk gates passed.",
        "What must happen next: user reviews the report and authorizes any trade decision manually.",
        "What invalidates it: resistance reclaimed, stale data, supportive regime, event risk, or extension.",
        f"Reason it is S-Put tier: {'all S-Put tier requirements passed' if candidate.grade.value == 'S' else 'not S-Put tier'}",
    ]
    if include_detail:
        lines.extend(
            [
                f"Missing confirmation: {candidate.missing_confirmation or 'None'}",
                f"Reason it is not S-Put tier: {candidate.not_s_tier_reason or 'N/A'}",
            ]
        )
    return lines


def put_result_to_json(result: PutScanResult) -> dict[str, Any]:
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


def write_put_reports(result: PutScanResult) -> tuple[Path, Path]:
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
            f"Market regime: {result.market_regime} (Hostile = put-supportive)",
            f"Securities scanned: {result.universe_count}",
            f"Passed deterministic filters: {result.deterministic_pass_count}",
            f"Received catalyst review: {result.research_count}",
            f"B tier developing: {len(result.b_tier)}",
            f"Free technical watch: {len(result.technical_watch)}",
            "",
            "S-PUT TIER",
            "",
        ]
    )
    if result.s_tier:
        for idx, candidate in enumerate(result.s_tier, 1):
            lines.extend(_put_candidate_block(candidate, idx))
            lines.append("")
    lines.extend(["A-PLUS PUT TIER", ""])
    if result.a_plus:
        for idx, candidate in enumerate(result.a_plus, 1):
            lines.extend(_put_candidate_block(candidate, idx, include_detail=True))
            lines.append("")
    lines.extend(["B PUT TIER — DEVELOPING SETUPS", ""])
    if result.b_tier:
        lines.extend(
            [
                "These put setups pass basic bearish structure but do not yet meet A+ thresholds. "
                "Monitor for score improvement before committing capital.",
                "",
            ]
        )
        for idx, candidate in enumerate(result.b_tier, 1):
            lines.extend(_put_candidate_block(candidate, idx, include_detail=True))
            lines.append("")
    lines.extend(["FREE TECHNICAL WATCH (PUT)", ""])
    if result.technical_watch:
        lines.extend(
            [
                "These are not trade-ready put setups. They passed the bearish technical gates, "
                "but current tradable put option liquidity is unavailable or only indicative.",
                "",
            ]
        )
        for idx, candidate in enumerate(result.technical_watch, 1):
            lines.extend(_put_candidate_block(candidate, idx, include_detail=True))
            lines.append("")
    if not result.s_tier and not result.a_plus and not result.b_tier and not result.technical_watch:
        lines.extend(
            ["No S-Put or A-Plus put setups qualified today.", "", "Standards were not lowered.", ""]
        )
    lines.extend(
        [
            "NO TRADE CONDITIONS (PUT)",
            "",
            "1. Gap exceeds one ATR below the breakdown trigger.",
            "2. Overhead resistance reclaimed before entry.",
            "3. Option spread exceeds the configured limit.",
            "4. Option data becomes stale.",
            "5. New earnings or event risk appears.",
            "6. Market regime turns Supportive (bullish reversal).",
            "7. Price becomes extended to the downside.",
            "8. Catalyst is contradicted.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps(put_result_to_json(result), indent=2, default=str), encoding="utf-8"
    )
    return md_path, json_path
