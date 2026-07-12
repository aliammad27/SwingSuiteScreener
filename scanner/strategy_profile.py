from __future__ import annotations

from dataclasses import dataclass

from scanner.config import load_config


@dataclass(frozen=True)
class StrategyProfile:
    name: str
    direction: str
    preferred_dte_minimum: int
    preferred_dte_maximum: int
    hard_dte_minimum: int
    hard_dte_maximum: int
    preferred_delta_minimum: float
    preferred_delta_maximum: float
    delta_hard_floor: float
    intended_hold_days_minimum: int
    intended_hold_days_maximum: int
    exit_or_roll_dte: int
    maximum_spread_percent: float
    minimum_open_interest: int
    minimum_contract_volume: int
    maximum_iv_rank: float
    enable_put_scans: bool


def load_strategy_profile() -> StrategyProfile:
    values = load_config("strategy")
    return StrategyProfile(
        name=str(values["profile_name"]),
        direction=str(values["direction"]),
        preferred_dte_minimum=int(values["preferred_dte_target_minimum"]),
        preferred_dte_maximum=int(values["preferred_dte_target_maximum"]),
        hard_dte_minimum=int(values["preferred_dte_hard_minimum"]),
        hard_dte_maximum=int(values["preferred_dte_maximum"]),
        preferred_delta_minimum=float(values["preferred_delta_minimum"]),
        preferred_delta_maximum=float(values["preferred_delta_maximum"]),
        delta_hard_floor=float(values["delta_hard_floor"]),
        intended_hold_days_minimum=int(values["intended_hold_days_minimum"]),
        intended_hold_days_maximum=int(values["intended_hold_days_maximum"]),
        exit_or_roll_dte=int(values["exit_or_roll_dte"]),
        maximum_spread_percent=float(values["maximum_bid_ask_spread_percent_of_mid"]),
        minimum_open_interest=int(values["minimum_open_interest"]),
        minimum_contract_volume=int(values["minimum_contract_daily_volume"]),
        maximum_iv_rank=float(values["maximum_iv_rank"]),
        enable_put_scans=bool(values["enable_put_scans"]),
    )


PROFILE = load_strategy_profile()
