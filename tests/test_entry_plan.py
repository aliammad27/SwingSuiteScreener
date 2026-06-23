from scanner.market_regime import classify_market_regime
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol


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
    assert entry.preferred_dte_minimum == 45
    assert entry.preferred_dte_maximum == 60
    assert entry.intended_hold_days_minimum == 5
    assert entry.intended_hold_days_maximum == 14
