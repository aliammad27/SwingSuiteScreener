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
    no_progress_sessions: int
    maximum_spread_percent: float
    minimum_open_interest: int
    minimum_volume: int
    minimum_bid_ask_size: int
    maximum_theta_ask_percent: float
    prefer_nonstandard_weekly: bool
    monthly_liquidity_advantage_percent: float


@dataclass(frozen=True)
class ReviewThresholds:
    trend: int
    leadership: int
    setup: int
    timing: int
    market: int
    contract: int
    risk: int
    ready_verify_contract_minimum: int


@dataclass(frozen=True)
class WatchlistThresholds:
    trend: int
    leadership: int
    setup: int
    maximum_candidates: int


@dataclass(frozen=True)
class OpportunityTierProfile:
    s_tier_minimum_composite: int
    s_tier_minimum_contract: int
    a_plus_minimum_composite: int
    a_plus_minimum_contract: int
    asymmetric_trend: int
    asymmetric_leadership: int
    asymmetric_setup: int
    asymmetric_timing: int
    asymmetric_market: int
    asymmetric_risk: int
    asymmetric_contract: int
    asymmetric_minimum_target_to_expected_move: float
    asymmetric_maximum_iv_to_realized_volatility: float


@dataclass(frozen=True)
class CatalystProfile:
    gap_minimum_atr: float
    relative_volume_minimum: float
    maximum_age_bars: int
    require_gap_midpoint_hold: bool


@dataclass(frozen=True)
class AggressiveWeeklyProfile:
    enabled: bool
    preferred_dte: tuple[int, int]
    hard_dte: tuple[int, int]
    intended_hold_sessions: tuple[int, int]
    requalify_dte: int
    no_progress_sessions: int
    minimum_trend: int
    minimum_leadership: int
    minimum_setup: int
    minimum_timing: int
    minimum_market: int
    minimum_risk: int
    require_pattern_confirmed: bool
    allowed_patterns: tuple[str, ...]


@dataclass(frozen=True)
class TradeEconomicsProfile:
    minimum_target_to_expected_move: float
    realistic_target_to_expected_move: float
    attractive_target_to_expected_move: float
    maximum_target_to_expected_move: float
    debit_spread_iv_to_realized_minimum: float
    minimum_spread_reward_to_risk: float


@dataclass(frozen=True)
class StrategyProfile:
    schema_version: int
    name: str
    direction: str
    validation_state: str
    thresholds: ReviewThresholds
    watchlist_thresholds: WatchlistThresholds
    opportunity_tiers: OpportunityTierProfile
    catalyst: CatalystProfile
    aggressive_weekly: AggressiveWeeklyProfile
    trade_economics: TradeEconomicsProfile
    supportive_market_minimum: int
    mixed_market_minimum: int
    production_patterns: tuple[str, ...]
    context_patterns: tuple[str, ...]
    ready_distance_atr: float
    maximum_confirmed_extension_atr: float
    maximum_confirmed_age_bars: int
    leader_earnings_buffer_sessions: int
    macro_post_event_completed_hours: int
    maximum_event_source_age_hours: int
    index_macro_events: tuple[str, ...]
    entry_window_start_et: str
    entry_window_end_et: str
    final_hour_management_only: bool
    minimum_hourly_bars: int
    required_stock_feed: str
    required_option_feed: str
    maximum_quote_age_minutes: int
    minimum_price: float
    minimum_average_daily_dollar_volume_usd: float
    options_required: bool
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
        no_progress_sessions=int(values["no_progress_sessions"]),
        maximum_spread_percent=float(values["maximum_spread_percent"]),
        minimum_open_interest=int(values["minimum_open_interest"]),
        minimum_volume=int(values["minimum_volume"]),
        minimum_bid_ask_size=int(values["minimum_bid_ask_size"]),
        maximum_theta_ask_percent=float(values["maximum_theta_ask_percent"]),
        prefer_nonstandard_weekly=bool(values["prefer_nonstandard_weekly"]),
        monthly_liquidity_advantage_percent=float(
            values["monthly_liquidity_advantage_percent"]
        ),
    )


def load_strategy_profile() -> StrategyProfile:
    values = load_config("strategy")
    raw_thresholds = values["review_thresholds"]
    raw_watchlist = values["watchlist_thresholds"]
    raw_tiers = values["opportunity_tiers"]
    raw_catalyst = values["catalyst"]
    raw_aggressive = values["aggressive_weekly"]
    raw_economics = values["trade_economics"]
    raw_market = values["market"]
    raw_patterns = values["patterns"]
    raw_events = values["event_risk"]
    raw_timing = values["timing"]
    raw_trust = values["data_trust"]
    raw_universe = values["universe"]
    raw_lanes = values["lanes"]
    if not all(
        isinstance(item, dict)
        for item in (
            raw_thresholds,
            raw_watchlist,
            raw_tiers,
            raw_catalyst,
            raw_aggressive,
            raw_economics,
            raw_market,
            raw_patterns,
            raw_events,
            raw_timing,
            raw_trust,
            raw_universe,
            raw_lanes,
        )
    ):
        raise ConfigurationError("Strategy configuration sections must be mappings.")
    thresholds = ReviewThresholds(
        trend=int(raw_thresholds["trend"]),
        leadership=int(raw_thresholds["leadership"]),
        setup=int(raw_thresholds["setup"]),
        timing=int(raw_thresholds["timing"]),
        market=int(raw_thresholds["market"]),
        contract=int(raw_thresholds["contract"]),
        risk=int(raw_thresholds["risk"]),
        ready_verify_contract_minimum=int(
            raw_thresholds["ready_verify_contract_minimum"]
        ),
    )
    watchlist_thresholds = WatchlistThresholds(
        trend=int(raw_watchlist["trend"]),
        leadership=int(raw_watchlist["leadership"]),
        setup=int(raw_watchlist["setup"]),
        maximum_candidates=int(raw_watchlist["maximum_candidates"]),
    )
    opportunity_tiers = OpportunityTierProfile(
        s_tier_minimum_composite=int(raw_tiers["s_tier"]["minimum_composite"]),
        s_tier_minimum_contract=int(raw_tiers["s_tier"]["minimum_contract"]),
        a_plus_minimum_composite=int(raw_tiers["a_plus"]["minimum_composite"]),
        a_plus_minimum_contract=int(raw_tiers["a_plus"]["minimum_contract"]),
        asymmetric_trend=int(raw_tiers["asymmetric"]["trend"]),
        asymmetric_leadership=int(raw_tiers["asymmetric"]["leadership"]),
        asymmetric_setup=int(raw_tiers["asymmetric"]["setup"]),
        asymmetric_timing=int(raw_tiers["asymmetric"]["timing"]),
        asymmetric_market=int(raw_tiers["asymmetric"]["market"]),
        asymmetric_risk=int(raw_tiers["asymmetric"]["risk"]),
        asymmetric_contract=int(raw_tiers["asymmetric"]["contract"]),
        asymmetric_minimum_target_to_expected_move=float(
            raw_tiers["asymmetric"]["minimum_target_to_expected_move"]
        ),
        asymmetric_maximum_iv_to_realized_volatility=float(
            raw_tiers["asymmetric"]["maximum_iv_to_realized_volatility"]
        ),
    )
    catalyst = CatalystProfile(
        gap_minimum_atr=float(raw_catalyst["gap_minimum_atr"]),
        relative_volume_minimum=float(raw_catalyst["relative_volume_minimum"]),
        maximum_age_bars=int(raw_catalyst["maximum_age_bars"]),
        require_gap_midpoint_hold=bool(raw_catalyst["require_gap_midpoint_hold"]),
    )
    aggressive_preferred_dte = _pair(
        raw_aggressive["preferred_dte"],
        int,
        "aggressive_weekly.preferred_dte",
    )
    aggressive_hard_dte = _pair(
        raw_aggressive["hard_dte"],
        int,
        "aggressive_weekly.hard_dte",
    )
    aggressive_hold = _pair(
        raw_aggressive["intended_hold_sessions"],
        int,
        "aggressive_weekly.intended_hold_sessions",
    )
    aggressive_weekly = AggressiveWeeklyProfile(
        enabled=bool(raw_aggressive["enabled"]),
        preferred_dte=(
            int(aggressive_preferred_dte[0]),
            int(aggressive_preferred_dte[1]),
        ),
        hard_dte=(
            int(aggressive_hard_dte[0]),
            int(aggressive_hard_dte[1]),
        ),
        intended_hold_sessions=(
            int(aggressive_hold[0]),
            int(aggressive_hold[1]),
        ),
        requalify_dte=int(raw_aggressive["requalify_dte"]),
        no_progress_sessions=int(raw_aggressive["no_progress_sessions"]),
        minimum_trend=int(raw_aggressive["minimum_trend"]),
        minimum_leadership=int(raw_aggressive["minimum_leadership"]),
        minimum_setup=int(raw_aggressive["minimum_setup"]),
        minimum_timing=int(raw_aggressive["minimum_timing"]),
        minimum_market=int(raw_aggressive["minimum_market"]),
        minimum_risk=int(raw_aggressive["minimum_risk"]),
        require_pattern_confirmed=bool(raw_aggressive["require_pattern_confirmed"]),
        allowed_patterns=tuple(str(value) for value in raw_aggressive["allowed_patterns"]),
    )
    trade_economics = TradeEconomicsProfile(
        minimum_target_to_expected_move=float(
            raw_economics["minimum_target_to_expected_move"]
        ),
        realistic_target_to_expected_move=float(
            raw_economics["realistic_target_to_expected_move"]
        ),
        attractive_target_to_expected_move=float(
            raw_economics["attractive_target_to_expected_move"]
        ),
        maximum_target_to_expected_move=float(
            raw_economics["maximum_target_to_expected_move"]
        ),
        debit_spread_iv_to_realized_minimum=float(
            raw_economics["debit_spread_iv_to_realized_minimum"]
        ),
        minimum_spread_reward_to_risk=float(
            raw_economics["minimum_spread_reward_to_risk"]
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
        validation_state=str(values["validation_state"]),
        thresholds=thresholds,
        watchlist_thresholds=watchlist_thresholds,
        opportunity_tiers=opportunity_tiers,
        catalyst=catalyst,
        aggressive_weekly=aggressive_weekly,
        trade_economics=trade_economics,
        supportive_market_minimum=int(raw_market["supportive_minimum"]),
        mixed_market_minimum=int(raw_market["mixed_minimum"]),
        production_patterns=tuple(str(name) for name in raw_patterns["production"]),
        context_patterns=tuple(str(name) for name in raw_patterns["context_only"]),
        ready_distance_atr=float(raw_patterns["ready_distance_atr"]),
        maximum_confirmed_extension_atr=float(
            raw_patterns["maximum_confirmed_extension_atr"]
        ),
        maximum_confirmed_age_bars=int(raw_patterns["maximum_confirmed_age_bars"]),
        leader_earnings_buffer_sessions=int(
            raw_events["leader_earnings_buffer_sessions"]
        ),
        macro_post_event_completed_hours=int(
            raw_events["macro_post_event_completed_hours"]
        ),
        maximum_event_source_age_hours=int(raw_events["maximum_source_age_hours"]),
        index_macro_events=tuple(str(item) for item in raw_events["index_macro_events"]),
        entry_window_start_et=str(raw_timing["entry_window_start_et"]),
        entry_window_end_et=str(raw_timing["entry_window_end_et"]),
        final_hour_management_only=bool(raw_timing["final_hour_management_only"]),
        minimum_hourly_bars=int(raw_timing["minimum_completed_bars"]),
        required_stock_feed=str(raw_trust["required_stock_feed"]),
        required_option_feed=str(raw_trust["required_option_feed"]),
        maximum_quote_age_minutes=int(raw_trust["maximum_quote_age_minutes"]),
        minimum_price=float(raw_universe["minimum_price"]),
        minimum_average_daily_dollar_volume_usd=float(
            raw_universe["minimum_average_daily_dollar_volume_usd"]
        ),
        options_required=bool(raw_universe["options_required"]),
        lanes=lanes,
    )


PROFILE = load_strategy_profile()
