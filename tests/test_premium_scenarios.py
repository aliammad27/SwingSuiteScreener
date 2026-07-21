from dataclasses import replace
from datetime import UTC, date, datetime

from scanner.models import OptionContractSnapshot, ScanType
from scanner.premium_scenarios import (
    LIVE_OPRA_REQUIRED,
    estimate_premium_range,
    premium_target_scenarios,
)
from scanner.run_scan import run_scan


def _contract(**overrides: object) -> OptionContractSnapshot:
    values: dict[str, object] = {
        "contract_symbol": "TEST260821C00100000",
        "underlying_symbol": "TEST",
        "expiration_date": date(2026, 8, 21),
        "strike": 100.0,
        "dte": 20,
        "delta": 0.60,
        "gamma": 0.02,
        "theta": -0.10,
        "vega": 0.15,
        "implied_volatility": 0.30,
        "bid": 5.00,
        "ask": 5.20,
        "bid_size": 20,
        "ask_size": 20,
        "open_interest": 3000,
        "volume": 800,
        "feed": "opra",
        "quote_timestamp": datetime(2026, 7, 21, 15, tzinfo=UTC),
    }
    values.update(overrides)
    return OptionContractSnapshot(**values)  # type: ignore[arg-type]


def test_premium_range_uses_quote_delta_gamma_and_theta() -> None:
    low, high = estimate_premium_range(
        _contract(),
        underlying_price=100.0,
        underlying_target=110.0,
        maximum_hold_sessions=5,
    )
    assert low == 11.50
    assert high == 12.20


def test_premium_range_floors_both_ends_at_intrinsic_value() -> None:
    low, high = estimate_premium_range(
        _contract(delta=0.0, gamma=None, theta=-10.0, bid=1.0, ask=1.2),
        underlying_price=100.0,
        underlying_target=110.0,
        maximum_hold_sessions=5,
    )
    assert (low, high) == (10.0, 10.0)


def test_missing_gamma_uses_delta_only_and_discloses_assumption() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    contract = candidate.contracts.primary
    assert contract is not None
    selection = replace(candidate.contracts, primary=replace(contract, gamma=None))
    scenarios = premium_target_scenarios(replace(candidate, contracts=selection))
    assert scenarios[0].available
    assert "gamma unavailable" in scenarios[0].assumptions


def test_stale_or_non_opra_contracts_fail_closed() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    risk = candidate.contracts.primary_risk
    assert risk is not None
    stale = replace(
        candidate,
        contracts=replace(
            candidate.contracts,
            primary_risk=replace(risk, quote_age_minutes=3.0),
        ),
    )
    assert premium_target_scenarios(stale)[0].unavailable_reason == LIVE_OPRA_REQUIRED

    indicative = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="technical_watch"
    ).verify_contract[0]
    scenario = premium_target_scenarios(indicative)[0]
    assert not scenario.available
    assert scenario.unavailable_reason == LIVE_OPRA_REQUIRED


def test_invalid_contract_quote_fails_closed() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    contract = candidate.contracts.primary
    assert contract is not None
    invalid = replace(
        candidate,
        contracts=replace(
            candidate.contracts,
            primary=replace(contract, bid=0.0),
        ),
    )
    assert premium_target_scenarios(invalid)[0].unavailable_reason == LIVE_OPRA_REQUIRED

    wide_spread = replace(
        candidate,
        contracts=replace(
            candidate.contracts,
            primary=replace(contract, bid=1.0, ask=2.0),
        ),
    )
    assert (
        premium_target_scenarios(wide_spread)[0].unavailable_reason
        == LIVE_OPRA_REQUIRED
    )


def test_tp2_is_added_only_when_distinct_after_currency_rounding() -> None:
    candidate = run_scan(
        ScanType.INTRADAY, fixture=True, scenario="ready"
    ).ready_verify[0]
    plan = candidate.entry_plan
    with_tp2 = replace(
        candidate,
        entry_plan=replace(
            plan,
            target_price=plan.target_price - 1.0,
            target_basis="nearest confirmed daily pivot",
        ),
    )
    assert [item.target_label for item in premium_target_scenarios(with_tp2)] == [
        "TP1",
        "TP2",
    ]

    duplicate = replace(
        candidate,
        entry_plan=replace(
            plan,
            target_price=plan.planning_objective_2r - 0.001,
        ),
    )
    assert [item.target_label for item in premium_target_scenarios(duplicate)] == ["TP1"]
