from __future__ import annotations

from dataclasses import dataclass

from scanner.models import Candidate

WATCHABLE_CALL_BIASES = {
    "Watch",
    "Breakout watch",
    "Bullish",
    "Pullback setup",
    "Breakout confirmed",
}

BLOCKING_DAILY_MOMENTUM_STATES = {
    "Warning active",
    "HTF blocked",
    "Bearish",
    "Weakening",
}

SETUP_BUCKETS = {"S", "A+", "B", "TW"}


@dataclass(frozen=True)
class WatchlistItem:
    symbol: str
    bucket: str
    rank_score: int
    reason: str
    tradingview_url: str
    trigger: float | None = None
    support: float | None = None
    target_price: float | None = None
    research_call_strike: float | None = None
    preferred_dte_minimum: int | None = None
    preferred_dte_maximum: int | None = None
    intended_hold_days_minimum: int | None = None
    intended_hold_days_maximum: int | None = None


def is_setup_bucket(bucket: str) -> bool:
    return bucket in SETUP_BUCKETS


def watchlist_level_summary(item: WatchlistItem) -> str:
    if not is_setup_bucket(item.bucket):
        return ""
    parts: list[str] = []
    if item.target_price is not None:
        parts.append(f"Tgt {item.target_price:.2f}")
    if item.research_call_strike is not None:
        parts.append(f"Strike {item.research_call_strike:.2f}")
    if item.preferred_dte_minimum is not None and item.preferred_dte_maximum is not None:
        parts.append(f"{item.preferred_dte_minimum}-{item.preferred_dte_maximum}DTE")
    if item.intended_hold_days_minimum is not None and item.intended_hold_days_maximum is not None:
        parts.append(f"hold {item.intended_hold_days_minimum}-{item.intended_hold_days_maximum}d")
    return " | ".join(parts)


def is_strategy_watch_candidate(candidate: Candidate) -> bool:
    """Return true only for real strategy watch names, not broad-universe placeholders."""
    command = candidate.command
    daily = candidate.daily_momentum
    return all(
        [
            command.score >= 60,
            command.call_bias in WATCHABLE_CALL_BIASES,
            command.close > command.sma200,
            not command.extended,
            command.relative_strength != "Lagging",
            command.above_vwap,
            command.weekly_alignment,
            daily.rsi >= 50,
            daily.state not in BLOCKING_DAILY_MOMENTUM_STATES,
            candidate.option_liquidity != "Poor",
            candidate.market_regime != "Hostile",
            not candidate.catalyst.major_event_risk,
        ]
    )


def watch_details(candidate: Candidate) -> dict[str, object]:
    command = candidate.command
    daily = candidate.daily_momentum
    four_hour = candidate.four_hour_momentum
    return {
        "command_score": command.score,
        "call_bias": command.call_bias,
        "relative_strength": command.relative_strength,
        "daily_momentum_score": daily.score,
        "daily_momentum_state": daily.state,
        "four_hour_momentum_score": four_hour.score,
        "four_hour_momentum_state": four_hour.state,
        "option_liquidity": candidate.option_liquidity,
        "trigger": candidate.entry_plan.trigger,
        "support": candidate.entry_plan.support,
        "invalidation": candidate.entry_plan.invalidation,
        "target_price": candidate.entry_plan.target_price,
        "target_gain_percent": candidate.entry_plan.target_gain_percent,
        "research_call_strike": candidate.entry_plan.research_call_strike,
        "preferred_dte_minimum": candidate.entry_plan.preferred_dte_minimum,
        "preferred_dte_maximum": candidate.entry_plan.preferred_dte_maximum,
        "intended_hold_days_minimum": candidate.entry_plan.intended_hold_days_minimum,
        "intended_hold_days_maximum": candidate.entry_plan.intended_hold_days_maximum,
        "entry_status": candidate.entry_plan.status,
        "watch_eligible": is_strategy_watch_candidate(candidate),
    }


def tradingview_url(symbol: str) -> str:
    return f"https://www.tradingview.com/chart/?symbol={symbol}"


def rank_candidate(candidate: Candidate) -> int:
    command = candidate.command.score
    daily = candidate.daily_momentum.score
    four_hour = candidate.four_hour_momentum.score
    rs_bonus = 10 if candidate.command.relative_strength == "Leading" else 5
    bias_bonus = 5 if candidate.command.call_bias in {"Breakout confirmed", "Pullback setup"} else 0
    return command + daily + four_hour + rs_bonus + bias_bonus


def _grade_bucket(candidate: Candidate) -> str:
    if candidate.grade.value == "S":
        return "S"
    if candidate.grade.value == "A+":
        return "A+"
    if candidate.grade.value == "B":
        return "B"
    return "TW"


def _missing_confirmation_reason(value: str | None) -> str:
    if value is None:
        return "minor gap"
    normalized = value.strip()
    if not normalized or normalized.lower() == "none":
        return "minor gap"
    return normalized


def reason_for_candidate(candidate: Candidate) -> str:
    command = candidate.command
    daily = candidate.daily_momentum
    four_hour = candidate.four_hour_momentum
    if candidate.grade.value == "S":
        return (
            f"C{command.score} D{daily.score} 4H{four_hour.score}, RS {command.relative_strength}"
        )
    if candidate.grade.value == "A+":
        missing = _missing_confirmation_reason(candidate.missing_confirmation)
        return f"C{command.score} D{daily.score} 4H{four_hour.score}, {missing}"
    if candidate.grade.value == "B":
        return f"C{command.score} D{daily.score} 4H{four_hour.score}, developing"
    if candidate.grade.value == "Technical Watch":
        return f"C{command.score} D{daily.score} 4H{four_hour.score}, options need broker check"
    return f"C{command.score}, {command.call_bias}, D{daily.score}, 4H{four_hour.score}"


def reason_for_rejected(symbol: str, details: dict[str, object]) -> str:
    command_score = details.get("command_score", "?")
    call_bias = details.get("call_bias", "Watch")
    daily_score = details.get("daily_momentum_score", "?")
    four_hour_score = details.get("four_hour_momentum_score", "?")
    return f"C{command_score}, {call_bias}, D{daily_score}, 4H{four_hour_score}"


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def ranked_watchlist_items(
    candidates: list[Candidate],
    rejected_details: list[tuple[str, dict[str, object]]],
    limit: int = 10,
) -> list[WatchlistItem]:
    setup_items: list[WatchlistItem] = []
    watch_items: list[WatchlistItem] = []
    for candidate in candidates:
        setup_items.append(
            WatchlistItem(
                symbol=candidate.symbol,
                bucket=_grade_bucket(candidate),
                rank_score=rank_candidate(candidate),
                reason=reason_for_candidate(candidate),
                tradingview_url=tradingview_url(candidate.symbol),
                trigger=candidate.entry_plan.trigger,
                support=candidate.entry_plan.support,
                target_price=candidate.entry_plan.target_price,
                research_call_strike=candidate.entry_plan.research_call_strike,
                preferred_dte_minimum=candidate.entry_plan.preferred_dte_minimum,
                preferred_dte_maximum=candidate.entry_plan.preferred_dte_maximum,
                intended_hold_days_minimum=candidate.entry_plan.intended_hold_days_minimum,
                intended_hold_days_maximum=candidate.entry_plan.intended_hold_days_maximum,
            )
        )
    for symbol, details in rejected_details:
        if details.get("watch_eligible") is True:
            rank = _int_value(details.get("command_score"))
            rank += _int_value(details.get("daily_momentum_score"))
            rank += _int_value(details.get("four_hour_momentum_score"))
            watch_items.append(
                WatchlistItem(
                    symbol=symbol,
                    bucket="Watch",
                    rank_score=rank,
                    reason=reason_for_rejected(symbol, details),
                    tradingview_url=tradingview_url(symbol),
                    trigger=_optional_float(details.get("trigger")),
                    support=_optional_float(details.get("support")),
                )
            )
    ranked_setup = sorted(setup_items, key=lambda item: item.rank_score, reverse=True)
    ranked_watch = sorted(watch_items, key=lambda item: item.rank_score, reverse=True)
    remaining = max(0, limit - len(ranked_setup))
    return ranked_setup + ranked_watch[:remaining]
