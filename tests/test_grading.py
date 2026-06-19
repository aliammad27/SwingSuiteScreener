from dataclasses import replace

from scanner.grading import grade_candidate
from scanner.market_regime import classify_market_regime
from scanner.models import Grade
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol


def test_hostile_market_blocks_primary_grade() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY"))
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    hostile = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        candidate.command,
        candidate.daily_momentum,
        candidate.four_hour_momentum,
        candidate.option_liquidity,
        candidate.catalyst,
        "Hostile",
        candidate.entry_plan,
    )
    assert hostile.grade == Grade.REJECTED
    assert "hostile_market_regime" in hostile.rejection_reasons


def test_major_event_risk_rejects() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY"))
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    risky = replace(candidate.catalyst, major_event_risk=True)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        candidate.command,
        candidate.daily_momentum,
        candidate.four_hour_momentum,
        candidate.option_liquidity,
        risky,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
