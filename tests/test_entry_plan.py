from scanner.entry_plan import research_call_strike
from scanner.market_regime import classify_market_regime
from scanner.providers.fixtures import FixtureDataProvider
from scanner.put_entry_plan import research_put_strike
from scanner.run_scan import _scan_put_symbol, _scan_symbol


def test_entry_plan_includes_target_strike_and_swing_window() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"),
        provider.daily("QQQ"),
        provider.weekly("SPY"),
    )

    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    entry = candidate.entry_plan

    assert entry.target_price == entry.nearest_resistance
    assert entry.target_price > candidate.command.close
    assert entry.research_call_strike >= entry.trigger
    assert entry.preferred_dte_minimum == 14
    assert entry.preferred_dte_maximum == 21
    assert entry.intended_hold_days_minimum == 3
    assert entry.intended_hold_days_maximum == 7


def test_call_research_strike_rounds_up_between_trigger_and_target() -> None:
    # trigger 100, target 110 -> midpoint 105, increment 2.5 -> rounds UP to 105
    assert research_call_strike(100.0, 110.0) == 105.0
    # trigger 100, target 111 -> midpoint 105.5 -> rounds UP to 107.5
    strike = research_call_strike(100.0, 111.0)
    assert strike == 107.5
    assert 100.0 < strike < 111.0
    # trigger 50, target 57 -> midpoint 53.5, increment 1.0 -> rounds UP to 54
    strike = research_call_strike(50.0, 57.0)
    assert strike == 54.0
    assert 50.0 < strike < 57.0


def test_put_research_strike_rounds_down_between_target_and_trigger() -> None:
    # trigger 110, target 100 -> midpoint 105, increment 2.5 -> rounds DOWN to 105
    assert research_put_strike(110.0, 100.0) == 105.0
    # trigger 111, target 100 -> midpoint 105.5 -> rounds DOWN to 105
    strike = research_put_strike(111.0, 100.0)
    assert strike == 105.0
    assert 100.0 < strike < 111.0
    # trigger 57, target 50 -> midpoint 53.5, increment 1.0 -> rounds DOWN to 53
    strike = research_put_strike(57.0, 50.0)
    assert strike == 53.0
    assert 50.0 < strike < 57.0


def test_put_entry_plan_strike_between_target_and_trigger() -> None:
    provider = FixtureDataProvider("put_s_tier")
    regime = classify_market_regime(
        provider.daily("SPY"),
        provider.daily("QQQ"),
        provider.weekly("SPY"),
    )
    candidate = _scan_put_symbol("SPUT", provider, provider, provider, regime)
    entry = candidate.entry_plan

    assert entry.target_price < entry.research_put_strike < entry.trigger
    assert entry.preferred_dte_minimum == 14
    assert entry.preferred_dte_maximum == 21
    assert entry.intended_hold_days_minimum == 3
    assert entry.intended_hold_days_maximum == 7
