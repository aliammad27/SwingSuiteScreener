from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scanner.config import ConfigurationError, load_config
from scanner.models import StrategyLane


@dataclass(frozen=True)
class LaneProfile:
    lane: StrategyLane
    symbols: tuple[str, ...]
    preferred_dte: tuple[int, int]
    hard_dte: tuple[int, int]
    preferred_delta: tuple[float, float]
    hard_delta: tuple[float, float]
    intended_hold_sessions: tuple[int, int]
    requalify_dte: int
    maximum_spread_percent: float
    minimum_open_interest: int
    minimum_volume: int
    maximum_quote_age_minutes: int


@dataclass(frozen=True)
class ReviewThresholds:
    trend: int
    leadership: int
    setup: int
    momentum: int
    market: int
    contract: int
    risk: int
    ready_verify_contract_minimum: int


@dataclass(frozen=True)
class StrategyProfile:
    schema_version: int
    name: str
    direction: str
    thresholds: ReviewThresholds
    supportive_market_minimum: int
    mixed_market_minimum: int
    enabled_patterns: tuple[str, ...]
    ready_distance_atr: float
    maximum_confirmed_extension_atr: float
    maximum_confirmed_age_bars: int
    earnings_blackout_calendar_days: int
    lanes: dict[StrategyLane, LaneProfile]

    def lane(self, lane: StrategyLane) -> LaneProfile:
        return self.lanes[lane]


def _pair(values: Any, cast: type[int] | type[float], label: str) -> tuple[Any, Any]:
    if not isinstance(values, list) or len(values) != 2:
        raise ConfigurationError(f"{label} must contain exactly two values.")
    return cast(values[0]), cast(values[1])


def _lane_profile(lane: StrategyLane, values: dict[str, Any]) -> LaneProfile:
    dte = _pair(values["preferred_dte"], int, f"{lane.value}.preferred_dte")
    hard_dte = _pair(values["hard_dte"], int, f"{lane.value}.hard_dte")
    delta = _pair(values["preferred_delta"], float, f"{lane.value}.preferred_delta")
    hard_delta = _pair(values["hard_delta"], float, f"{lane.value}.hard_delta")
    hold = _pair(
        values["intended_hold_sessions"], int, f"{lane.value}.intended_hold_sessions"
    )
    return LaneProfile(
        lane=lane,
        symbols=tuple(str(symbol) for symbol in values.get("symbols", [])),
        preferred_dte=(int(dte[0]), int(dte[1])),
        hard_dte=(int(hard_dte[0]), int(hard_dte[1])),
        preferred_delta=(float(delta[0]), float(delta[1])),
        hard_delta=(float(hard_delta[0]), float(hard_delta[1])),
        intended_hold_sessions=(int(hold[0]), int(hold[1])),
        requalify_dte=int(values["requalify_dte"]),
        maximum_spread_percent=float(values["maximum_spread_percent"]),
        minimum_open_interest=int(values["minimum_open_interest"]),
        minimum_volume=int(values["minimum_volume"]),
        maximum_quote_age_minutes=int(values["maximum_quote_age_minutes"]),
    )


def load_strategy_profile() -> StrategyProfile:
    values = load_config("strategy")
    raw_thresholds = values["review_thresholds"]
    raw_market = values["market"]
    raw_patterns = values["patterns"]
    raw_events = values["event_risk"]
    raw_lanes = values["lanes"]
    if not all(
        isinstance(item, dict)
        for item in (raw_thresholds, raw_market, raw_patterns, raw_events, raw_lanes)
    ):
        raise ConfigurationError("Strategy configuration sections must be mappings.")
    thresholds = ReviewThresholds(
        trend=int(raw_thresholds["trend"]),
        leadership=int(raw_thresholds["leadership"]),
        setup=int(raw_thresholds["setup"]),
        momentum=int(raw_thresholds["momentum"]),
        market=int(raw_thresholds["market"]),
        contract=int(raw_thresholds["contract"]),
        risk=int(raw_thresholds["risk"]),
        ready_verify_contract_minimum=int(
            raw_thresholds["ready_verify_contract_minimum"]
        ),
    )
    lanes: dict[StrategyLane, LaneProfile] = {}
    for lane in StrategyLane:
        raw_lane = raw_lanes.get(lane.value)
        if not isinstance(raw_lane, dict):
            raise ConfigurationError(f"Missing strategy lane: {lane.value}")
        lanes[lane] = _lane_profile(lane, raw_lane)
    return StrategyProfile(
        schema_version=int(values["schema_version"]),
        name=str(values["profile_name"]),
        direction=str(values["direction"]),
        thresholds=thresholds,
        supportive_market_minimum=int(raw_market["supportive_minimum"]),
        mixed_market_minimum=int(raw_market["mixed_minimum"]),
        enabled_patterns=tuple(str(name) for name in raw_patterns["enabled"]),
        ready_distance_atr=float(raw_patterns["ready_distance_atr"]),
        maximum_confirmed_extension_atr=float(
            raw_patterns["maximum_confirmed_extension_atr"]
        ),
        maximum_confirmed_age_bars=int(raw_patterns["maximum_confirmed_age_bars"]),
        earnings_blackout_calendar_days=int(
            raw_events["earnings_blackout_calendar_days"]
        ),
        lanes=lanes,
    )


PROFILE = load_strategy_profile()
