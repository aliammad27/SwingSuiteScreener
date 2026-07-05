from dataclasses import replace

from scanner.grading import grade_candidate
from scanner.market_regime import classify_market_regime
from scanner.models import Grade
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol


def _a_plus_candidate():
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    return _scan_symbol("APLUS", provider, provider, provider, regime)


def test_hostile_market_blocks_primary_grade() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
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


def test_b_tier_developing_setup() -> None:
    candidate = _a_plus_candidate()
    lower_command = replace(candidate.command, score=68)
    lower_daily = replace(candidate.daily_momentum, score=60)
    lower_4h = replace(candidate.four_hour_momentum, score=65)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        lower_command,
        lower_daily,
        lower_4h,
        candidate.option_liquidity,
        candidate.catalyst,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.B_TIER
    assert result.missing_confirmation is not None


def test_b_tier_blocked_by_poor_liquidity() -> None:
    candidate = _a_plus_candidate()
    lower_command = replace(candidate.command, score=68)
    lower_daily = replace(candidate.daily_momentum, score=60)
    lower_4h = replace(candidate.four_hour_momentum, score=65)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        lower_command,
        lower_daily,
        lower_4h,
        "Poor",
        candidate.catalyst,
        candidate.market_regime,
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
    assert "options_illiquid" in result.rejection_reasons


def test_b_tier_blocked_by_hostile_regime() -> None:
    candidate = _a_plus_candidate()
    lower_command = replace(candidate.command, score=68)
    lower_daily = replace(candidate.daily_momentum, score=60)
    lower_4h = replace(candidate.four_hour_momentum, score=65)
    result = grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        lower_command,
        lower_daily,
        lower_4h,
        candidate.option_liquidity,
        candidate.catalyst,
        "Hostile",
        candidate.entry_plan,
    )
    assert result.grade == Grade.REJECTED
    assert "hostile_market_regime" in result.rejection_reasons


def test_major_event_risk_rejects() -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
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


def _s_tier_candidate():
    provider = FixtureDataProvider("s_tier")
    regime = classify_market_regime(
        provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY")
    )
    return _scan_symbol("SSTR", provider, provider, provider, regime)


def _regrade(candidate, command=None):
    return grade_candidate(
        candidate.symbol,
        candidate.company,
        candidate.sector,
        candidate.benchmark,
        command if command is not None else candidate.command,
        candidate.daily_momentum,
        candidate.four_hour_momentum,
        candidate.option_liquidity,
        candidate.catalyst,
        candidate.market_regime,
        candidate.entry_plan,
    )


def test_movement_filter_blocks_s_tier_but_allows_b_tier() -> None:
    candidate = _s_tier_candidate()
    assert candidate.grade == Grade.S_TIER
    # ATR percent below the 2.0 floor: cannot be S tier or A Plus
    slow = replace(candidate.command, atr_percent=1.5)
    result = _regrade(candidate, command=slow)
    assert result.grade not in {Grade.S_TIER, Grade.A_PLUS}
    assert result.grade == Grade.B_TIER
    assert "atr_percent_below_floor" in result.rejection_reasons


def test_movement_filter_reason_codes_in_json_rejected_output() -> None:
    from scanner.models import RejectedRecord, ScanType
    from scanner.reports import result_to_json
    from scanner.run_scan import run_scan

    candidate = _s_tier_candidate()
    # Fail movement (low ATR) and B tier scores so the candidate fully rejects
    weak = replace(candidate.command, score=62, atr_percent=1.0)
    result = _regrade(candidate, command=weak)
    assert result.grade == Grade.REJECTED
    assert "atr_percent_below_floor" in result.rejection_reasons

    scan = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    record = RejectedRecord(result.symbol, "grading", result.rejection_reasons, {})
    scan = replace(scan, rejected=[record])
    data = result_to_json(scan)
    codes = data["rejected"][0]["reason_codes"]
    assert "atr_percent_below_floor" in codes


def test_tier_threshold_lists_unchanged() -> None:
    candidate = _s_tier_candidate()
    # S tier requires command score >= 85
    assert _regrade(candidate, command=replace(candidate.command, score=84)).grade != Grade.S_TIER
    assert _regrade(candidate, command=replace(candidate.command, score=85)).grade == Grade.S_TIER
    # A Plus requires command score >= 75 (84 fails S but passes A+)
    a_plus = _regrade(candidate, command=replace(candidate.command, score=84))
    assert a_plus.grade == Grade.A_PLUS
    below_a = _regrade(candidate, command=replace(candidate.command, score=74))
    assert below_a.grade not in {Grade.S_TIER, Grade.A_PLUS}
    # B tier requires command score >= 65
    assert below_a.grade == Grade.B_TIER
    rejected = _regrade(candidate, command=replace(candidate.command, score=64))
    assert rejected.grade == Grade.REJECTED
