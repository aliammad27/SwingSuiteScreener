from __future__ import annotations

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
        "watch_eligible": is_strategy_watch_candidate(candidate),
    }
